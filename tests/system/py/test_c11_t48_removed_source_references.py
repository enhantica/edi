# System tier: scans this product's committed binding sources.
""": binding runtime lookups must not use removed Python spellings."""

from __future__ import annotations

import copy
import hashlib
import json
import re
import shutil
import subprocess
from functools import cache
from pathlib import Path
from typing import Any

from tests.fixtures.cwl_family.historical import current_surface_path

PRODUCTS = ('crysta', 'edi')

ROOT = Path(__file__).resolve().parents[3]
PRODUCT = 'edi'
MANIFEST = 'data/python-surface.json'
BASELINE = 'tests/unit/py/c11_t48_surface_baseline.json'
BASELINE_SHA256 = {
    'crysta': '63813521c604233960a94b95bd65c18cfa79e0ce0e50cc5fded24888c807587a',
    'edi': '7afbb58d7c01d0a9e2193a17611b62f77ad8dcf28df1ec08fa5528f43851101e',
}
POST_BASE_REMOVED_PATHS = {
    'crysta': {
        'FitOutcome.descent',
        'FitOutcome.terminal_unevaluable_trials',
        'FitOutcome.unevaluable_trials',
        'IterationRecord.unevaluable_trials',
        'ResidualPattern.sigma',
    },
    'edi': {
        'AtomSite.free_parameters',
        'BackgroundPoint.free_parameters',
        'Cell.free_parameters',
        'Experiment.free_parameters',
        'ExperimentBase.absorption',
        'ExperimentBase.background',
        'ExperimentBase.data',
        'ExperimentBase.excluded_regions',
        'ExperimentBase.free_parameters',
        'ExperimentBase.instrument',
        'ExperimentBase.peak',
        'FitResult.descent',
        'FitResult.elapsed_ms',
        'FitResult.engine_esd',
        'FitResult.engine_values',
        'FitResult.iterations_history',
        'FitResult.n_points_fitted',
        'FitResult.n_points_loaded',
        'FitResult.pre_fit',
        'FitResult.start',
        'FitResult.terminal_unevaluable_trials',
        'FitResult.unevaluable_trials',
        'FitResultBase.descent',
        'FitResultBase.elapsed_ms',
        'FitResultBase.engine_esd',
        'FitResultBase.engine_values',
        'FitResultBase.iterations_history',
        'FitResultBase.n_points_fitted',
        'FitResultBase.n_points_loaded',
        'FitResultBase.pre_fit',
        'FitResultBase.start',
        'FitResultBase.terminal_unevaluable_trials',
        'FitResultBase.unevaluable_trials',
        'LineSegment.free_parameters',
        'Reflection',
        'Structure.free_parameters',
    },
}
BINDING_ROOTS = {'crysta': ('src/bindings/',), 'edi': ('lib/src/',)}
CPP_SUFFIXES = {'.c', '.cc', '.cpp', '.cxx', '.h', '.hh', '.hpp'}
SOURCE_SCAN_LIMIT = (
    'SOURCE_SCAN_LIMIT: this gate covers committed tracked C/C++ binding sources under the '
    'declared binding roots and literal nanobind .attr("name") runtime lookups. A receiver owner '
    'is resolved only from a local nb::class_ binding variable or the root module variable m. '
    'When receiver ownership is unresolved, every literal leaf present in the removed-member '
    'inventory fails closed, including a spelling that remains live on another owner. Python '
    'source, C/C++ outside the binding roots, native identifiers, declaration strings such as '
    '.def("name"), and non-literal or dynamically assembled .attr arguments are outside this '
    'narrowed gate; the general Python analyzer residual is tracked by development hub . Dynamic '
    'runtime names can therefore escape this static check.'
)
GIT = shutil.which('git')
assert GIT is not None, ' I6: source gate requires git to read committed objects'

_CPP_ASSIGNED_CLASS = re.compile(
    r'(?P<variable>[A-Za-z_]\w*)\s*=\s*nb::class_<[^>]+>\s*'
    r'\(\s*[A-Za-z_]\w*\s*,\s*"(?P<owner>[A-Za-z_]\w*)"'
)
_CPP_DECLARED_CLASS = re.compile(
    r'nb::class_<[^>]+>\s+(?P<variable>[A-Za-z_]\w*)\s*'
    r'\(\s*[A-Za-z_]\w*\s*,\s*"(?P<owner>[A-Za-z_]\w*)"'
)
_CPP_LITERAL_ATTR = re.compile(r'\.\s*attr\s*\(\s*"(?P<name>[A-Za-z_]\w*)"\s*\)')
_SIMPLE_RECEIVER = re.compile(r'(?P<receiver>[A-Za-z_]\w*)\s*$')


@cache
def _committed(repo: str, path: str) -> str:
    """Read immutable product content from local committed HEAD, never the working tree."""
    assert repo == PRODUCT, ' I6: a product gate may inspect only its owning checkout'
    completed = subprocess.run(
        [GIT, '-C', str(ROOT), 'show', f'HEAD:{path}'],
        capture_output=True,
        text=True,
        check=False,
    )
    assert completed.returncode == 0, (
        f' I6: cannot read committed {PRODUCT}:{path}: {completed.stderr}'
    )
    return completed.stdout


def _manifest(repo: str) -> dict[str, Any]:
    document = json.loads(_committed(repo, MANIFEST))
    assert isinstance(document, dict), f' I6: {repo} Python-surface manifest must be a JSON object'
    assert document.get('schema') == 4, (
        f' I6: {repo} removed-source scan requires manifest schema 4'
    )
    assert isinstance(document.get('removed'), dict), (
        f' I6: {repo} manifest removed section must be an object'
    )
    return document


def _baseline_paths(repo: str) -> set[str]:
    raw = _committed(repo, BASELINE)
    digest = hashlib.sha256(raw.encode()).hexdigest()
    assert digest == BASELINE_SHA256[repo], f' I1: frozen {repo} pre-task surface changed bytes'
    document = json.loads(raw)
    assert document.get('schema') == 1, ' I1: frozen surface must use schema 1'
    assert document.get('repo') == repo, f' I1: frozen surface must name {repo}'
    assert document.get('module') == repo, f' I1: frozen surface must import {repo}'
    assert document.get('protected_tier') == 'tests/unit/**', (
        ' I1: frozen surface must remain a protected test input'
    )
    names = document.get('names')
    members = document.get('members')
    assert isinstance(names, list), ' I1: frozen surface must carry names'
    assert isinstance(members, dict), ' I1: frozen surface must carry members'
    paths = set(names)
    paths.update(
        f'{owner}.{member}'
        for owner, owner_members in members.items()
        if isinstance(owner_members, list)
        for member in owner_members
    )
    return {current_surface_path(path) for path in paths}


def _classification_paths(manifest: dict[str, Any]) -> set[str]:
    classification = manifest.get('classification')
    if not isinstance(classification, dict):
        return set()
    modules = classification.get('module')
    members = classification.get('members')
    if not isinstance(modules, dict) or not isinstance(members, dict):
        return set()
    paths = set(modules)
    paths.update(
        f'{owner}.{member}'
        for owner, owner_members in members.items()
        if isinstance(owner_members, dict)
        for member in owner_members
    )
    return {current_surface_path(path) for path in paths}


def _removed_inventory_findings(repo: str, manifest: dict[str, Any]) -> list[str]:
    removed = manifest.get('removed')
    if not isinstance(removed, dict):
        return ['removed: schema 4 requires an object']
    baseline = _baseline_paths(repo)
    classified = _classification_paths(manifest)
    removed_paths = set(removed)
    baseline_removed = {
        path for path in baseline if path in removed_paths or path.partition('.')[0] in removed
    }
    findings = [
        f'{path}: expected removed path has no removal record'
        for path in sorted(path for path in baseline - classified if path not in baseline_removed)
    ]
    findings.extend(
        f'{path}: removal record is absent from the independently derived inventory'
        for path in sorted(removed_paths - baseline - POST_BASE_REMOVED_PATHS[repo])
    )
    findings.extend(
        f'{path}: path is both classified and removed'
        for path in sorted(classified & baseline_removed)
    )
    return findings


@cache
def _binding_source_paths(repo: str) -> tuple[str, ...]:
    assert repo == PRODUCT, ' I6: source inventory must stay in its owning checkout'
    completed = subprocess.run(
        [
            GIT,
            '-C',
            str(ROOT),
            'ls-tree',
            '-r',
            '--name-only',
            'HEAD',
            '--',
            *BINDING_ROOTS[repo],
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    assert completed.returncode == 0, (
        f' I6: cannot enumerate committed {repo} binding sources: {completed.stderr}'
    )
    paths = tuple(
        path for path in completed.stdout.splitlines() if Path(path).suffix in CPP_SUFFIXES
    )
    assert paths, f' I6: {repo} binding source inventory is empty'
    return {current_surface_path(path) for path in paths}


def _binding_source_snapshot(repo: str) -> dict[str, str]:
    return {path: _committed(repo, path) for path in _binding_source_paths(repo)}


def _surface_sets(
    manifest: dict[str, Any],
) -> tuple[set[str], dict[str, set[str]], dict[str, set[str]]]:
    removed = manifest['removed']
    removed_modules = {path for path in removed if '.' not in path}
    removed_members: dict[str, set[str]] = {}
    for path in removed:
        if '.' in path:
            removed_members.setdefault(path.rsplit('.', 1)[1], set()).add(path)

    classification = manifest.get('classification', {})
    member_rows = classification.get('members', {}) if isinstance(classification, dict) else {}
    live_members: dict[str, set[str]] = {}
    if isinstance(member_rows, dict):
        for owner, owner_members in member_rows.items():
            if isinstance(owner_members, dict):
                for member in owner_members:
                    live_members.setdefault(member, set()).add(f'{owner}.{member}')
    return removed_modules, removed_members, live_members


def _line_number(text: str, offset: int) -> int:
    return text.count('\n', 0, offset) + 1


def _record(
    findings: set[str], repo: str, path: str, line: int, removed_path: str, shape: str
) -> None:
    findings.add(f'{repo}:{path}:{line}: {removed_path} via {shape}')


def _binding_runtime_findings(
    repo: str,
    manifest: dict[str, Any],
    sources: dict[str, str],
) -> list[str]:
    removed_modules, removed_members, live_members = _surface_sets(manifest)
    findings: set[str] = set()
    for path, text in sources.items():
        if Path(path).suffix not in CPP_SUFFIXES:
            continue
        class_variables = {
            match.group('variable'): match.group('owner')
            for pattern in (_CPP_ASSIGNED_CLASS, _CPP_DECLARED_CLASS)
            for match in pattern.finditer(text)
        }
        for match in _CPP_LITERAL_ATTR.finditer(text):
            name = match.group('name')
            receiver_match = _SIMPLE_RECEIVER.search(text[: match.start()])
            receiver = receiver_match.group('receiver') if receiver_match else None
            line = _line_number(text, match.start())

            if receiver == 'm' and name in removed_modules:
                _record(
                    findings,
                    repo,
                    path,
                    line,
                    name,
                    'literal root-module nanobind attr name',
                )
                continue

            owner = class_variables.get(receiver) if receiver is not None else None
            if owner is not None:
                removed_path = f'{owner}.{name}'
                if removed_path in removed_members.get(name, set()):
                    _record(
                        findings,
                        repo,
                        path,
                        line,
                        removed_path,
                        'owner-resolved literal nanobind attr name',
                    )
                continue

            candidates = removed_members.get(name, set())
            if not candidates:
                continue
            live_paths = live_members.get(name, set())
            if live_paths:
                shape = (
                    'owner-ambiguous literal nanobind attr name '
                    f'(fails closed; spelling also live as {", ".join(sorted(live_paths))})'
                )
            else:
                shape = 'owner-unresolved literal nanobind attr name (fails closed)'
            for removed_path in candidates:
                _record(findings, repo, path, line, removed_path, shape)
    return sorted(findings)


def test_c11_t48_removed_paths_have_no_static_product_source_references() -> None:
    assert PRODUCT in PRODUCTS, ' I6: source gate must run in crysta or edi'
    findings = _binding_runtime_findings(
        PRODUCT,
        _manifest(PRODUCT),
        _binding_source_snapshot(PRODUCT),
    )
    assert findings == [], (
        ' I6: removed Python paths must not survive in binding runtime lookups\n'
        + '\n'.join(findings)
        + f'\n{SOURCE_SCAN_LIMIT}'
    )


def test_c11_t48_removed_inventory_covers_the_frozen_pre_task_complement() -> None:
    findings = _removed_inventory_findings(PRODUCT, _manifest(PRODUCT))
    assert findings == [], (
        ' I1/I6: the frozen pre-task surface must be classified or recorded removed\n'
        + '\n'.join(findings)
    )


def test_c11_t48_removed_source_reference_controls_can_fail() -> None:
    assert PRODUCT in PRODUCTS, ' I6: refusal control must run in crysta or edi'
    inventory = _binding_source_paths(PRODUCT)
    assert all(
        path.startswith(BINDING_ROOTS[PRODUCT]) and Path(path).suffix in CPP_SUFFIXES
        for path in inventory
    ), ' I14: the blocking scan must stay bounded to declared C/C++ binding roots'

    owner, member = ('Parameter', 'par_type') if PRODUCT == 'crysta' else ('Cell', 'cubic')
    exact_findings = _binding_runtime_findings(
        PRODUCT,
        _manifest(PRODUCT),
        {
            f'{BINDING_ROOTS[PRODUCT][0]}c11_t48_control.cpp': (
                f'void control(nb::handle value) {{ value.attr("{member}"); }}\n'
            )
        },
    )
    assert any(
        f'{owner}.{member} via owner-unresolved literal nanobind attr name' in finding
        for finding in exact_findings
    ), ' I6: scanner must reject the exact pre-fix runtime attribute shape'

    if PRODUCT == 'crysta':
        shared_leaf_findings = _binding_runtime_findings(
            PRODUCT,
            _manifest(PRODUCT),
            {
                'src/bindings/c11_t48_shared_leaf_control.cpp': (
                    'void control(nb::handle parameter) { parameter.attr("label"); }\n'
                )
            },
        )
        assert any(
            'Parameter.label via owner-ambiguous literal nanobind attr name' in finding
            and 'FreeParameter.label' in finding
            for finding in shared_leaf_findings
        ), (
            ' I6: a removed member shared with a live owner must fail closed when '
            'the runtime receiver owner is unresolved'
        )

        live_owner_findings = _binding_runtime_findings(
            PRODUCT,
            _manifest(PRODUCT),
            {
                'src/bindings/c11_t48_resolved_owner_control.cpp': (
                    'auto free_parameter = nb::class_<FreeParameter>(m, "FreeParameter");\n'
                    'free_parameter.attr("label");\n'
                )
            },
        )
        assert not any('Parameter.label' in finding for finding in live_owner_findings), (
            ' I14: a structurally resolved surviving owner must not inherit another '
            "owner's removed member"
        )

    dynamic_findings = _binding_runtime_findings(
        PRODUCT,
        _manifest(PRODUCT),
        {
            f'{BINDING_ROOTS[PRODUCT][0]}c11_t48_dynamic_control.cpp': (
                f'void control(nb::handle value) {{ value.attr("{member}" + suffix); }}\n'
            )
        },
    )
    assert dynamic_findings == [], (
        'control premise: a dynamically assembled attribute name is outside the static gate'
    )
    python_findings = _binding_runtime_findings(
        PRODUCT,
        _manifest(PRODUCT),
        {'tools/c11_t48_python_control.py': f'value.{member}\n'},
    )
    assert python_findings == [], (
        ' owner ruling: general Python analysis must not remain a blocking gate'
    )

    deleted_path = f'{owner}.{member}'
    manifest = _manifest(PRODUCT)
    existing_inventory_findings = _removed_inventory_findings(PRODUCT, manifest)
    deleted_manifest = copy.deepcopy(manifest)
    del deleted_manifest['removed'][deleted_path]
    missing = _removed_inventory_findings(PRODUCT, deleted_manifest)
    assert set(missing) == {
        *existing_inventory_findings,
        f'{deleted_path}: expected removed path has no removal record',
    }, ' I1/I6: deleting a non-sentinel removal record must fail closed'
    assert not any(
        deleted_path in finding
        for finding in _binding_runtime_findings(
            PRODUCT,
            deleted_manifest,
            {
                f'{BINDING_ROOTS[PRODUCT][0]}c11_t48_deleted_record_control.cpp': (
                    f'void control(nb::handle value) {{ value.attr("{member}"); }}\n'
                )
            },
        )
    ), 'control premise: deleting the removal record makes the source-only scan blind'

    assert 'unresolved' in SOURCE_SCAN_LIMIT, (
        ' I14: the narrowed gate must state its receiver uncertainty'
    )
    assert 'fails closed' in SOURCE_SCAN_LIMIT, (
        ' I14: the narrowed gate must state how receiver uncertainty resolves'
    )
    assert 'Python source' in SOURCE_SCAN_LIMIT, (
        ' owner ruling: the narrowed gate must name its excluded source universe'
    )
    assert 'outside this narrowed gate' in SOURCE_SCAN_LIMIT, (
        ' owner ruling: the narrowed gate must bound its excluded source universe'
    )
    assert 'non-literal or dynamically assembled' in SOURCE_SCAN_LIMIT, (
        ' I14: the narrowed gate must state its dynamic-name blind spot'
    )
