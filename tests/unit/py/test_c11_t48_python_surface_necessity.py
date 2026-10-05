"""red-first gates for edi's justified Python surface and absorbed API rows."""

from __future__ import annotations

import copy
import enum
import hashlib
import importlib.util
import inspect
import json
import os
import re
import shlex
import shutil
from pathlib import Path
from types import ModuleType
from typing import Any

import edi
import pytest

ROOT = Path(__file__).resolve().parents[3]
MANIFEST = ROOT / 'data/python-surface.json'
CHECKER = ROOT / 'tools/checks/python_surface.py'
MODEL_HEADER = ROOT / 'core/include/edi/model.hpp'
BASELINE = Path(__file__).with_name('c11_t48_surface_baseline.json')
REQUIRED_REFERENCE = Path(__file__).with_name('c11_t48_required_surface.json')
CRYSTA_SOURCE_SHA = ROOT / 'build/crysta-src/CRYSTA_SOURCE_SHA'
# ADR-0011 partitions this retained pre-sweep universe into kept and removed paths.
# Its JSON 'base' field is historical provenance; no Git object is resolved.
BASELINE_SHA256 = '7afbb58d7c01d0a9e2193a17611b62f77ad8dcf28df1ec08fa5528f43851101e'
REQUIRED_POST_BASE_REMOVED_PATHS = {
    'AtomSite.free_parameters',
    'BackgroundPoint.free_parameters',
    'Cell.free_parameters',
    'Experiment.free_parameters',
    'Structure.free_parameters',
}
POST_BASE_REMOVED_PATHS = REQUIRED_POST_BASE_REMOVED_PATHS | {
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
}
TASK_ID = re.compile(r'[A-Z][0-9]{2}-T[0-9]+')

CELL_FIELDS = (
    'length_a',
    'length_b',
    'length_c',
    'angle_alpha',
    'angle_beta',
    'angle_gamma',
)
SITE_FIELDS = ('fract_x', 'fract_y', 'fract_z', 'occupancy', 'adp_iso')
PEAK_FIELDS = (
    'rise_alpha_0',
    'rise_alpha_1',
    'decay_beta_0',
    'decay_beta_1',
    'broad_gauss_sigma_0',
    'broad_gauss_sigma_1',
    'broad_gauss_sigma_2',
    'broad_gauss_size',
    'broad_gauss_strain',
    'broad_lorentz_gamma_0',
    'broad_lorentz_gamma_1',
    'broad_lorentz_gamma_2',
    'broad_lorentz_size',
    'broad_lorentz_strain',
    'broad_gauss_u',
    'broad_gauss_v',
    'broad_gauss_w',
    'broad_lorentz_x',
    'broad_lorentz_y',
)
INSTRUMENT_FIELDS = (
    'calib_d_to_tof_offset',
    'calib_d_to_tof_linear',
    'calib_d_to_tof_quadratic',
    'calib_d_to_tof_reciprocal',
    'setup_twotheta_bank',
    'setup_wavelength',
    'calib_twotheta_offset',
)


def _project_path() -> Path:
    root_override = os.environ.get('EDI_CRYSTA_CORPUS_ROOT')
    root = Path(root_override) if root_override else ROOT / 'build/crysta-src/tests/fitting'
    source_sha = CRYSTA_SOURCE_SHA.read_text(encoding='utf-8').strip()
    assert (root / 'manifest.yml').is_file(), (
        f' requires the declared crysta fitting corpus at {root} '
        f'(recorded crysta source {source_sha}); missing reference input is a failure, '
        'never a skip'
    )
    case = root / 'ncaf-wish-3bank-s5'
    assert case.is_dir(), f"declared crysta corpus at {root} has no case 'ncaf-wish-3bank-s5'"
    return case / 'project'


def _present_parameters(owner: object, names: tuple[str, ...]) -> list[object]:
    return [
        value
        for name in names
        if hasattr(owner, name) and (value := getattr(owner, name)) is not None
    ]


def _expected_parameters(project: object) -> list[tuple[object, list[object]]]:
    rows: list[tuple[object, list[object]]] = []
    all_structure_parameters: list[object] = []
    for structure in project.structures:
        structure_parameters: list[object] = []
        cell = _present_parameters(structure.cell, CELL_FIELDS)
        rows.append((structure.cell, cell))
        structure_parameters.extend(cell)
        for site in structure.atom_sites:
            site_parameters = _present_parameters(site, SITE_FIELDS)
            rows.append((site, site_parameters))
            structure_parameters.extend(site_parameters)
        rows.append((structure, list(structure_parameters)))
        all_structure_parameters.extend(structure_parameters)

    experiment_parameters: list[object] = []
    for experiment in project.experiments:
        peak = _present_parameters(experiment.peak, PEAK_FIELDS)
        instrument = _present_parameters(experiment.instrument, INSTRUMENT_FIELDS)
        linked = [experiment.linked_structure.scale]
        absorption = _present_parameters(experiment.absorption, ('abscor1', 'abscor2'))
        background: list[object] = []
        for point in experiment.background:
            point_parameters = [point.intensity]
            rows.append((point, point_parameters))
            background.extend(point_parameters)
        own = [*peak, *instrument, *linked, *absorption, *background]
        rows.append((experiment, own))
        experiment_parameters.extend(own)
    rows.append((project, [*all_structure_parameters, *experiment_parameters]))
    return rows


def _is_free_token(token: str) -> bool:
    return '(' in token and token.endswith(')')


def _tag_free_flags(path: Path) -> dict[str, list[bool]]:
    """Parse exact tag occurrences from the independent corpus text, including loops."""
    lines = path.read_text(encoding='utf-8').splitlines()
    flags: dict[str, list[bool]] = {}
    index = 0
    while index < len(lines):
        line = lines[index].strip()
        if line == 'loop_':
            index += 1
            headers: list[str] = []
            while index < len(lines) and lines[index].startswith('_'):
                headers.append(lines[index].strip())
                index += 1
            while index < len(lines) and lines[index].strip():
                values = shlex.split(lines[index])
                assert len(values) == len(headers), (
                    f' I3: independent EDI loops must remain rectangular in {path}'
                )
                for header, value in zip(headers, values, strict=True):
                    flags.setdefault(header, []).append(_is_free_token(value))
                index += 1
            continue
        fields = shlex.split(line)
        if len(fields) >= 2 and fields[0].startswith('_'):
            flags.setdefault(fields[0], []).append(_is_free_token(fields[1]))
        index += 1
    return flags


def _flag(flags: dict[str, list[bool]], tag: str, occurrence: int = 0) -> bool:
    if tag not in flags:
        return False
    assert occurrence < len(flags[tag]), f'independent corpus has no {tag}[{occurrence}]'
    return flags[tag][occurrence]


def _expected_project_free_flags(project: object, project_path: Path) -> list[bool]:
    structure_path = next((project_path / 'structures').glob('*.edi'))
    structure_flags = _tag_free_flags(structure_path)

    flags = [
        _flag(structure_flags, f'_cell.{name}')
        for name in CELL_FIELDS
        if getattr(project.structure.cell, name) is not None
    ]
    for site_index, site in enumerate(project.structure.atom_sites):
        flags.extend(
            _flag(structure_flags, f'_atom_site.{name}', site_index)
            for name in SITE_FIELDS
            if getattr(site, name) is not None
        )

    for experiment in project.experiments:
        experiment_path = project_path / 'experiments' / f'{experiment.name}.edi'
        assert experiment_path.is_file(), (
            f' I3: independent corpus has no source for experiment {experiment.name!r}'
        )
        experiment_flags = _tag_free_flags(experiment_path)
        flags.extend(
            _flag(experiment_flags, f'_peak.{name}')
            for name in PEAK_FIELDS
            if hasattr(experiment.peak, name) and getattr(experiment.peak, name) is not None
        )
        flags.extend(
            _flag(experiment_flags, f'_instrument.{name}')
            for name in INSTRUMENT_FIELDS
            if hasattr(experiment.instrument, name)
            and getattr(experiment.instrument, name) is not None
        )
        flags.append(_flag(experiment_flags, '_linked_structure.scale'))
        flags.extend(
            _flag(experiment_flags, f'_absorption.{name}')
            for name in ('abscor1', 'abscor2')
            if hasattr(experiment.absorption, name)
            and getattr(experiment.absorption, name) is not None
        )
        flags.extend(
            _flag(experiment_flags, '_background.intensity', point_index)
            for point_index, _point in enumerate(experiment.background)
        )
    return flags


def test_c11_t48_missing_declared_corpus_fails_instead_of_skipping(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setenv('EDI_CRYSTA_CORPUS_ROOT', str(tmp_path / 'missing-corpus'))
    with pytest.raises(AssertionError, match='missing reference input is a failure, never a skip'):
        _project_path()


def _atom_adp_types(path: Path) -> list[str]:
    lines = path.read_text(encoding='utf-8').splitlines()
    start = next(index for index, line in enumerate(lines) if line == '_atom_site.id')
    headers: list[str] = []
    index = start
    while index < len(lines) and lines[index].startswith('_atom_site.'):
        headers.append(lines[index])
        index += 1
    adp_index = headers.index('_atom_site.adp_type')
    values: list[str] = []
    while index < len(lines) and lines[index].strip():
        row = shlex.split(lines[index])
        assert len(row) == len(headers), ' I3: independent atom-site loops must remain rectangular'
        values.append(row[adp_index])
        index += 1
    return values


def _insert_it_number(path: Path) -> None:
    text = path.read_text(encoding='utf-8')
    anchor = '_space_group.name_h_m "I 21 3"\n'
    assert text.count(anchor) == 1, ' I3: the round-trip control requires one space-group anchor'
    path.write_text(
        text.replace(anchor, anchor + '_space_group.it_number 199\n'),
        encoding='utf-8',
    )


def test_c11_t48_adp_type_and_it_number_round_trip_from_the_edi_text(tmp_path: Path) -> None:
    source = tmp_path / 'source'
    shutil.copytree(_project_path(), source)
    structure_path = source / 'structures/ncaf.edi'
    expected_adp_types = _atom_adp_types(structure_path)
    _insert_it_number(structure_path)

    project = edi.Project.load(source)
    assert [site.adp_type for site in project.structure.atom_sites] == expected_adp_types, (
        ' I3: atom ADP types must load from independent EDI text'
    )
    assert project.structure.space_group.it_number == 199, (
        ' I3: the IT number must load from independent EDI text'
    )

    destination = tmp_path / 'saved'
    project.save_as(destination)
    written = (destination / 'structures/ncaf.edi').read_text(encoding='utf-8')
    assert '_space_group.it_number 199\n' in written, (
        ' I3: the IT number must persist to saved EDI text'
    )
    assert written.count(' Biso') == len(expected_adp_types), (
        ' I3: every atom ADP type must persist to saved EDI text'
    )
    restored = edi.Project.load(destination)
    assert [site.adp_type for site in restored.structure.atom_sites] == expected_adp_types, (
        ' I3: atom ADP types must survive an EDI round trip'
    )
    assert restored.structure.space_group.it_number == 199, (
        ' I3: the IT number must survive an EDI round trip'
    )


def _mutated_project(tmp_path: Path, tier: str) -> Path:
    destination = tmp_path / tier
    shutil.copytree(_project_path(), destination)
    if tier == 'syntax':
        experiment = destination / 'experiments/wish_2_9.edi'
        experiment.write_text(
            'unexpected-token\n' + experiment.read_text(encoding='utf-8'),
            encoding='utf-8',
        )
    elif tier == 'schema':
        structure = destination / 'structures/ncaf.edi'
        text = structure.read_text(encoding='utf-8')
        line = next(line for line in text.splitlines() if line.startswith('_cell.length_a '))
        structure.write_text(text.replace(line + '\n', ''), encoding='utf-8')
    elif tier == 'domain':
        experiment = destination / 'experiments/wish_2_9.edi'
        text = experiment.read_text(encoding='utf-8')
        old = '_experiment_type.beam_mode time-of-flight'
        assert text.count(old) == 1, ' I3: the domain control requires one beam-mode anchor'
        experiment.write_text(
            text.replace(old, '_experiment_type.beam_mode "constant wavelength"'),
            encoding='utf-8',
        )
    else:  # pragma: no cover - parametrization is closed below
        raise AssertionError(tier)
    return destination


@pytest.mark.parametrize('tier', ['syntax', 'schema', 'domain'])
def test_c11_t48_validation_error_tiers_are_value_errors_with_diagnostics(
    tier: str,
    tmp_path: Path,
) -> None:
    class_name = f'{tier.title()}ValidationError'
    assert hasattr(edi, 'ValidationError'), ' I3: edi must expose the validation error base class'
    assert hasattr(edi, class_name), ' I3: edi must expose every validation error tier'
    error_type = getattr(edi, class_name)
    assert issubclass(error_type, edi.ValidationError), (
        ' I3: each validation tier must derive from ValidationError'
    )
    assert issubclass(error_type, ValueError), (
        ' I3: every validation tier must preserve ValueError compatibility'
    )
    with pytest.raises(error_type) as captured:
        edi.Project.load(_mutated_project(tmp_path, tier))
    diagnostics = captured.value.diagnostics
    assert diagnostics, f'{class_name} must carry at least one diagnostic'
    for diagnostic in diagnostics:
        assert diagnostic.code and diagnostic.path and diagnostic.message, (
            ' I3: every validation diagnostic must carry code path and message'
        )


def _need_finding(path: str, row: object) -> str | None:  # noqa: PLR0911
    if not isinstance(row, dict):
        return f'{path}: classification row is not an object'
    need = row.get('need')
    if not isinstance(need, dict):
        return f'{path}: missing need'
    verdict = need.get('verdict')
    if verdict == 'undecided':
        return f'{path}: undecided'
    if verdict == 'remove':
        return f'{path}: remove is still live'
    if verdict != 'keep':
        return f'{path}: unknown need verdict {verdict!r}'
    by = need.get('by')
    if by not in {'counterpart', 'deviation', 'owner'}:
        return f'{path}: malformed keep provenance {by!r}'
    if by in {'counterpart', 'deviation'} and not str(need.get('ref', '')).strip():
        return f'{path}: keep by {by} has no ref'
    return None


def _surface_paths(module: ModuleType) -> set[str]:
    names = {name for name in dir(module) if not name.startswith('_')}
    paths = set(names)
    for name in names:
        value = getattr(module, name)
        if inspect.isclass(value):
            paths.update(f'{name}.{member}' for member in dir(value) if not member.startswith('_'))
    return paths


def _required_end_state() -> set[str]:
    document = json.loads(REQUIRED_REFERENCE.read_text(encoding='utf-8'))
    assert document.get('schema') == 1, (
        ' I3: the independent end-state fixture must use schema one'
    )
    assert document.get('repo') == 'edi', (
        ' I3: the independent end-state fixture must identify edi'
    )
    paths = document.get('required_paths')
    assert isinstance(paths, list), ' I3: required end-state paths must be represented as a list'
    assert paths == sorted(set(paths)), ' I3: required end-state paths must be unique and sorted'
    assert not {'Severity.Error', 'Severity.Info', 'Severity.Warning'} & set(paths), (
        'the named sources carry Severity but no enum-member rows'
    )
    sources = document.get('sources')
    assert isinstance(sources, list), (
        ' I3: independent end-state sources must be represented as a list'
    )
    assert len(sources) == 3, ' I3: the end-state fixture must retain all three named sources'
    assert set(paths) >= REQUIRED_POST_BASE_REMOVED_PATHS, (
        'the frozen end-state fixture must retain the paths superseded by the owner ruling'
    )
    return set(paths) - REQUIRED_POST_BASE_REMOVED_PATHS


def _baseline_paths() -> set[str]:
    content = BASELINE.read_bytes()
    document = json.loads(content)
    assert document['schema'] == 1, ' I1: the frozen surface baseline must use schema one'
    assert document['protected_tier'] == 'tests/unit/**', (
        ' I1: the frozen surface baseline must identify its protected tier'
    )
    assert document['repo'] == 'edi', ' I1: the frozen surface baseline must identify edi'
    assert document['module'] == 'edi', (
        ' I1: the frozen surface baseline must identify the edi module'
    )
    assert hashlib.sha256(content).hexdigest() == BASELINE_SHA256, (
        'C11-T48 I1: retained surface baseline content must stay byte-identical'
    )
    paths = set(document['names'])
    paths.update(
        f'{class_name}.{member}'
        for class_name, members in document['members'].items()
        for member in members
    )
    return paths


@pytest.mark.parametrize('damage', ['drop-name', 'drop-member', 'invent-member'])
def test_c11_t48_retained_baseline_cannot_shrink_or_gain_paths(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, damage: str
) -> None:
    document = json.loads(BASELINE.read_text(encoding='utf-8'))
    if damage == 'drop-name':
        document['names'].remove('Cell')
    elif damage == 'drop-member':
        document['members']['Cell'].remove('length_a')
    else:
        document['members']['Cell'].append('invented_member')
    damaged = tmp_path / 'damaged-baseline.json'
    damaged.write_text(json.dumps(document, indent=2) + '\n', encoding='utf-8')
    monkeypatch.setitem(globals(), 'BASELINE', damaged)
    with pytest.raises(AssertionError, match='C11-T48 I1: retained surface baseline content'):
        _baseline_paths()


def _classification_paths(manifest: dict[str, Any]) -> set[str]:
    classification = manifest.get('classification')
    if not isinstance(classification, dict):
        return set()
    module_rows = classification.get('module')
    member_rows = classification.get('members')
    if not isinstance(module_rows, dict) or not isinstance(member_rows, dict):
        return set()
    paths = set(module_rows)
    paths.update(
        f'{class_name}.{member}'
        for class_name, members in member_rows.items()
        if isinstance(members, dict)
        for member in members
    )
    return paths


def _partition_findings(
    manifest: dict[str, Any],
    live_paths: set[str],
    required_paths: set[str],
) -> list[str]:
    """Bind the frozen input universe to live classified rows or justified removals."""
    baseline_paths = _baseline_paths()
    classified_paths = _classification_paths(manifest)
    removed = manifest.get('removed')
    if not isinstance(removed, dict):
        return ['removed: schema 4 requires an object']
    removed_paths = set(removed)
    baseline_removed = {
        path
        for path in baseline_paths
        if path in removed_paths or path.partition('.')[0] in removed
    }
    findings = [
        f'{path}: pre-task path has no live classification or justified removal'
        for path in sorted(baseline_paths - classified_paths - baseline_removed)
    ]
    findings.extend(
        f'{path}: pre-task path is both classified and removed'
        for path in sorted(classified_paths & baseline_removed)
    )
    findings.extend(
        f'{path}: post-base path required removed by the owner ruling has no removal record'
        for path in sorted(POST_BASE_REMOVED_PATHS - removed_paths)
    )
    findings.extend(
        f'{path}: post-base removed path is still classified'
        for path in sorted(POST_BASE_REMOVED_PATHS & classified_paths)
    )
    findings.extend(
        f'{path}: removed path is absent from the protected removal universe'
        for path in sorted(removed_paths - baseline_paths - POST_BASE_REMOVED_PATHS)
    )
    for path, row in removed.items():
        if not isinstance(row, dict):
            findings.append(f'{path}: removal metadata is not an object')
        elif (
            not isinstance(row.get('removed_in'), str)
            or row['removed_in'] not in {'necessity review (ADR-0011)', 'refine-to-fit rename'}
            or not str(row.get('reason', '')).strip()
        ):
            findings.append(
                f'{path}: removal metadata must name a documented removal boundary '
                'and a non-empty reason'
            )
    findings.extend(
        f'{path}: required end-state path is absent'
        for path in sorted(required_paths - live_paths)
    )
    findings.extend(
        f'{path}: required end-state path is unclassified'
        for path in sorted(required_paths - classified_paths)
    )
    return findings


def _drop_classification(manifest: dict[str, Any], path: str) -> None:
    owner, dot, member = path.partition('.')
    if dot:
        del manifest['classification']['members'][owner][member]
    else:
        del manifest['classification']['module'][owner]


def _surface_findings(  # noqa: PLR0912, PLR0915
    manifest: dict[str, Any], module: ModuleType
) -> list[str]:
    findings: list[str] = []
    if manifest.get('schema') != 4:
        findings.append('schema: necessity rows require schema 4')
    classification = manifest.get('classification')
    if not isinstance(classification, dict):
        return [*findings, 'classification: missing']
    module_rows = classification.get('module')
    member_rows = classification.get('members')
    if not isinstance(module_rows, dict) or not isinstance(member_rows, dict):
        return [*findings, 'classification: module/members must be objects']

    findings.extend(_partition_findings(manifest, _surface_paths(module), _required_end_state()))

    live_names = {name for name in dir(module) if not name.startswith('_')}
    for name in sorted(live_names):
        if name not in module_rows:
            findings.append(f'{name}: live name is unclassified')
        else:
            problem = _need_finding(name, module_rows[name])
            if problem:
                findings.append(problem)
    findings.extend(
        f'{name}: stale module row' for name in sorted(module_rows) if not hasattr(module, name)
    )

    live_classes = {name for name in live_names if inspect.isclass(getattr(module, name))}
    for class_name in sorted(live_classes):
        rows = member_rows.get(class_name)
        if not isinstance(rows, dict):
            findings.append(f'{class_name}: member rows missing')
            continue
        cls = getattr(module, class_name)
        for member in sorted(name for name in dir(cls) if not name.startswith('_')):
            path = f'{class_name}.{member}'
            if member not in rows:
                findings.append(f'{path}: live member is unclassified')
            else:
                problem = _need_finding(path, rows[member])
                if problem:
                    findings.append(problem)
                elif rows[member]['need']['by'] == 'owner':
                    owner_need = module_rows[class_name].get('need', {})
                    if owner_need.get('verdict') != 'keep':
                        findings.append(f'{path}: owner {class_name} is not keep')
                    is_enum_value = issubclass(cls, enum.Enum) and member in cls.__members__
                    is_inherited = member not in cls.__dict__
                    if not (is_enum_value or is_inherited):
                        findings.append(f'{path}: by=owner is not derived')
    for class_name, rows in member_rows.items():
        if not hasattr(module, class_name) or not inspect.isclass(getattr(module, class_name)):
            findings.append(f'{class_name}: stale member group')
            continue
        if isinstance(rows, dict):
            cls = getattr(module, class_name)
            findings.extend(
                f'{class_name}.{member}: stale member row'
                for member in rows
                if not hasattr(cls, member)
            )

    removed = manifest.get('removed')
    if not isinstance(removed, dict):
        findings.append('removed: schema 4 requires an object')
    else:
        for path in removed:
            owner, dot, member = path.partition('.')
            if hasattr(module, owner) and (not dot or hasattr(getattr(module, owner), member)):
                findings.append(f'{path}: removed name remains reachable')
    return findings


def _manifest() -> dict[str, Any]:
    assert MANIFEST.is_file(), 'the declared Python surface manifest must exist in the checkout'
    value = json.loads(MANIFEST.read_text(encoding='utf-8'))
    assert isinstance(value, dict), ' I12: the necessity manifest root must be a JSON object'
    return value


def test_c11_t48_necessity_manifest_is_total_and_refusal_controls_can_fail(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    manifest = _manifest()
    assert _surface_findings(manifest, edi) == [], (
        ' I12: the committed edi necessity manifest must be total and resolved'
    )

    monkeypatch.setattr(edi, 'c11_t48_unclassified', object(), raising=False)
    assert any(
        'c11_t48_unclassified: live name is unclassified' in finding
        for finding in _surface_findings(manifest, edi)
    ), ' I12: an unclassified live module name must fail closed'
    monkeypatch.delattr(edi, 'c11_t48_unclassified')

    mutated = copy.deepcopy(manifest)
    module_rows = mutated['classification']['module']
    name = next(name for name in sorted(module_rows) if not name.startswith('_'))
    module_rows[name].pop('need')
    assert any(
        finding == f'{name}: missing need' for finding in _surface_findings(mutated, edi)
    ), ' I12: a classification without necessity evidence must fail closed'

    mutated = copy.deepcopy(manifest)
    module_rows = mutated['classification']['module']
    module_rows[name]['need'] = {'verdict': 'keep', 'by': 'counterpart', 'ref': ''}
    assert any(
        finding == f'{name}: keep by counterpart has no ref'
        for finding in _surface_findings(mutated, edi)
    ), ' I12: counterpart necessity without a reference must fail closed'

    mutated = copy.deepcopy(manifest)
    module_rows = mutated['classification']['module']
    module_rows[name]['need'] = {'verdict': 'undecided', 'question': 'owner decision required'}
    assert any(finding == f'{name}: undecided' for finding in _surface_findings(mutated, edi)), (
        ' I12: an undecided necessity verdict must fail closed'
    )
    module_rows[name]['need'] = {'verdict': 'remove'}
    assert any(
        finding == f'{name}: remove is still live' for finding in _surface_findings(mutated, edi)
    ), ' I6: a remove verdict must fail while its subject remains live'

    mutated = copy.deepcopy(manifest)
    mutated['removed'][name] = {'removed_in': 'control', 'reason': 'must be detected'}
    assert any(
        finding == f'{name}: removed name remains reachable'
        for finding in _surface_findings(mutated, edi)
    ), ' I6: a removed manifest path must be unreachable'

    owner_rows = [
        (class_name, member)
        for class_name, rows in manifest['classification']['members'].items()
        for member, row in rows.items()
        if row.get('need', {}).get('by') == 'owner'
    ]
    assert owner_rows, 'the derived enum/inherited population must be represented'
    class_name, member = owner_rows[0]
    mutated = copy.deepcopy(manifest)
    mutated['classification']['module'][class_name]['need'] = {'verdict': 'remove'}
    assert any(
        finding == f'{class_name}.{member}: owner {class_name} is not keep'
        for finding in _surface_findings(mutated, edi)
    ), ' I12: derived member necessity requires a kept owner class'

    live_paths = _surface_paths(edi)
    baseline_path = 'Cell.length_a'
    assert baseline_path in _baseline_paths() & live_paths, (
        ' I1: the deletion control requires a frozen live baseline path'
    )
    mutated = copy.deepcopy(manifest)
    _drop_classification(mutated, baseline_path)
    simulated_deleted = live_paths - {baseline_path}
    assert any(
        finding
        == f'{baseline_path}: pre-task path has no live classification or justified removal'
        for finding in _partition_findings(mutated, simulated_deleted, _required_end_state())
    ), ' I12: a deleted baseline path without a removal verdict must fail closed'
    mutated['removed'][baseline_path] = {
        'removed_in': 'refine-to-fit rename',
        'reason': 'synthetic deletion-path control',
    }
    assert not any(
        finding.startswith(f'{baseline_path}: pre-task path has no')
        for finding in _partition_findings(mutated, simulated_deleted, _required_end_state())
    ), ' I6: a justified removal must close the frozen baseline partition'
    mutated['removed'][baseline_path]['reason'] = ''
    assert any(
        finding
        == (
            f'{baseline_path}: removal metadata must name a documented removal boundary '
            'and a non-empty reason'
        )
        for finding in _partition_findings(mutated, simulated_deleted, _required_end_state())
    ), ' I6: incomplete removal metadata must fail closed'
    mutated['removed'][baseline_path]['reason'] = 'synthetic deletion-path control'
    mutated['removed'][baseline_path]['removed_in'] = 'control'
    assert any(
        finding
        == (
            f'{baseline_path}: removal metadata must name a documented removal boundary '
            'and a non-empty reason'
        )
        for finding in _partition_findings(mutated, simulated_deleted, _required_end_state())
    ), ' I6: removal provenance must remain a documented boundary'

    required_path = 'Diagnostic.code'
    assert required_path in _required_end_state(), (
        ' I3: the missing-path control requires a named end-state path'
    )
    mutated = copy.deepcopy(manifest)
    _drop_classification(mutated, required_path)
    simulated_missing = live_paths - {required_path}
    assert any(
        finding == f'{required_path}: required end-state path is absent'
        for finding in _partition_findings(mutated, simulated_missing, _required_end_state())
    ), ' I3: a missing required end-state path must fail closed'


def test_c11_t48_post_base_removal_records_are_protected_against_deletion() -> None:
    manifest = _manifest()
    post_base_path = 'Cell.free_parameters'
    assert post_base_path in POST_BASE_REMOVED_PATHS & set(manifest['removed']), (
        ': the post-base deletion control requires its settled removal record'
    )
    mutated = copy.deepcopy(manifest)
    del mutated['removed'][post_base_path]
    expected = (
        f'{post_base_path}: post-base path required removed by the owner ruling '
        'has no removal record'
    )
    assert expected in _partition_findings(mutated, _surface_paths(edi), _required_end_state()), (
        ' I6: a post-base removed path must remain protected against record deletion'
    )


def test_c11_t48_removed_manifest_paths_and_cell_cubic_are_unreachable() -> None:
    manifest = _manifest()
    removed = manifest.get('removed')
    assert isinstance(removed, dict) and removed, ' I6: schema four must record executed removals'
    assert 'Cell.cubic' in removed, ' I6: Cell cubic must carry a removal verdict'
    assert not hasattr(edi.Cell, 'cubic'), ' I6: Cell cubic must be unreachable in Python'
    assert 'cubic(' not in MODEL_HEADER.read_text(encoding='utf-8'), (
        ' I6: Cell cubic must be absent from the owning model declaration'
    )
    assert not [
        finding
        for finding in _surface_findings(manifest, edi)
        if 'removed name remains reachable' in finding
    ], ' I6: every manifest removal must be unreachable'


def _load_module(name: str, path: Path) -> ModuleType:
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None, ' I7: the committed checker must have an import specification'
    assert spec.loader is not None, ' I7: the committed checker must have a module loader'
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module
