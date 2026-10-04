"""The edi-side fitting-corpus runner (crysta  D4) — thin by design.

The fitting corpus lives in crysta (`tests/fitting/` — one directory per case, one declared
manifest); edi consumes it **at its recorded crysta-main source**, so corpus data flows with
the dependency it already built (`build/crysta-src/CRYSTA_SOURCE_SHA`). This runner is structurally
derived from that manifest: every case with ``sides: both`` or ``sides: edi-only`` becomes
one parametrized test asserting the case's ``expected.json`` through edi's own entry point
(`edi.Project.load` + `fit`), within the case's declared tolerances.

Corpus-root resolution is one explicit seam:

- ``EDI_CRYSTA_CORPUS_ROOT`` (set by the cross-build harness — crysta's `edi-verification`
  PR job / `edi-simulation` task) points at the *current* crysta tree's corpus, arming the
  both-sides contract pre-merge with no committed foreign pin. The harness ALSO rebuilds
  edi's core against that same tree (``CRYSTA_CONSUMER_SRC``) before running this file —
  setting the override against a different core build compares working-tree expected values to
  a different engine and asserts nothing meaningful;
- otherwise the recorded checkout (`build/crysta-src/tests/fitting`).

Transition semantics ( §4.3): a resolved root with **no corpus at all** is one loud,
named skip carrying the recorded sha; a
resolved root **with** a manifest enforces full totality: a case this runner should exercise
but cannot realize FAILS (fail-closed, never a silent skip).

Quantity names are the corpus canon (the crysta CLI compact-record spellings); the accessor
table below is this runner's entry-point mapping. The historical schema-7 `reduced_chi2` and
settled schema-8 `reduced_chi_square` spellings both map deliberately to
``FitOutcome.reduced_chi_square`` during the pin transition; parameter `.esd` and
`.uncertainty` suffixes likewise resolve through ``FitOutcome.uncertainty``.
"""

from __future__ import annotations

import csv
import json
import os
import re
import shutil
from pathlib import Path

import edi
import pytest
import yaml

from conftest import crysta_reference_source

REPO_ROOT = Path(__file__).resolve().parents[3]
RECORDED_SHA_FILE = REPO_ROOT / 'build' / 'crysta-src' / 'CRYSTA_SOURCE_SHA'
RECORDED_CORPUS = REPO_ROOT / 'build' / 'crysta-src' / 'tests' / 'fitting'

# The entry-point mapping: corpus quantity name -> FitOutcome attribute.
OUTCOME_ATTRS = {
    'reduced_chi2': 'reduced_chi_square',
    'reduced_chi_square': 'reduced_chi_square',
    'rwp': 'rwp',
    'iterations': 'iterations',
}
_SEQUENTIAL_CHI2_RE = re.compile(
    r'^results\[([0-9]+(?:\.[0-9]+)?)\]\.fit_result\.reduced_chi_square$'
)


def _read_sequential_rows(project_dir: Path) -> dict[float, dict[str, str]]:
    results_csv = project_dir / 'analysis' / 'results.csv'
    if not results_csv.is_file():
        return {}
    with results_csv.open(newline='', encoding='utf-8') as stream:
        return {float(row['diffrn.ambient_temperature']): row for row in csv.DictReader(stream)}


def _sequential_quantity(
    case_id: str, name: str, rows: dict[float, dict[str, str]]
) -> float | None:
    match = _SEQUENTIAL_CHI2_RE.fullmatch(name)
    if match is None:
        return None
    temperature = float(match.group(1))
    assert temperature in rows, (
        f"{case_id}: quantity '{name}' names temperature {temperature}, absent "
        f'from results.csv temperatures {sorted(rows)!r}'
    )
    return float(rows[temperature]['fit_result.reduced_chi_square'])


def _assert_quantity(case_id: str, name: str, spec: dict, measured: float) -> None:
    delta = abs(measured - spec['value'])
    if spec['tol_abs'] is not None:
        assert delta <= spec['tol_abs'], (
            f'{case_id}.{name} ({spec["kind"]}): |{measured} - {spec["value"]}| = '
            f'{delta} > tol_abs {spec["tol_abs"]}'
        )
    if spec['tol_rel'] is not None:
        bound = spec['tol_rel'] * abs(spec['value'])
        assert delta <= bound, (
            f'{case_id}.{name} ({spec["kind"]}): |{measured} - {spec["value"]}| = '
            f'{delta} > tol_rel bound {bound}'
        )


def _recorded_sha() -> str:
    try:
        return RECORDED_SHA_FILE.read_text(encoding='utf-8').strip()
    except OSError:
        return 'unreadable-sha'


_OVERRIDE = os.environ.get('EDI_CRYSTA_CORPUS_ROOT')
ROOT = Path(_OVERRIDE) if _OVERRIDE else crysta_reference_source() / 'tests/fitting'
MANIFEST = ROOT / 'manifest.yml'

if MANIFEST.is_file():
    _manifest = yaml.safe_load(MANIFEST.read_text(encoding='utf-8'))
    # A manifest-bearing root enforces full totality from this side too ( §4.2/§4.3):
    # the manifest and the case directories must agree exactly, and every declared file must
    # exist — a deviation refuses at collection, never a skip.
    _ids = {c['id'] for c in _manifest['cases']}
    _dirs = {p.name for p in ROOT.iterdir() if p.is_dir() and p.name != '__pycache__'}
    if _dirs != _ids:
        _msg = (
            f'fitting corpus at {ROOT} violates manifest<->directory totality: '
            f'unlisted dirs {sorted(_dirs - _ids)!r}, missing dirs {sorted(_ids - _dirs)!r}'
        )
        raise RuntimeError(_msg)
    for _case in _manifest['cases']:
        for _f in _case['files']:
            if not (ROOT / _case['id'] / _f).is_file():
                _msg = f"corpus case '{_case['id']}' declares {_f} but the file does not exist"
                raise RuntimeError(_msg)
    _EDI_SIDES = {'both', 'edi-only'}
    UNITS = []
    for _c in _manifest['cases']:
        _variants = _c.get('variants')
        if not _variants:
            if _c['sides'] in _EDI_SIDES:
                UNITS.append((_c, None))
            continue
        UNITS.extend((_c, row) for row in _variants if row.get('sides', _c['sides']) in _EDI_SIDES)
    CORPUS_PRESENT = True
elif _OVERRIDE:
    # The override is the cross-build harness asserting where the corpus IS. A missing
    # manifest there is a wiring failure, and the override path never skips (I10): refuse
    # at collection so the harness run is red, not quietly hollow.
    _msg = (
        f'EDI_CRYSTA_CORPUS_ROOT={_OVERRIDE} names no fitting corpus '
        f'(no manifest.yml) — the working-tree override path never skips'
    )
    raise RuntimeError(_msg)
else:
    UNITS = []
    CORPUS_PRESENT = False

# The loud, named transition state ( §4.3) rides the guard test's OWN NODE ID, so it
# is visible in every pytest invocation including `--collect-only` (pytest's capture
# swallows import-time writes during collection; a node id it must print).
_GUARD_ID = (
    f'corpus not present at recorded crysta source {_recorded_sha()}'
    if not CORPUS_PRESENT
    else 'corpus-present'
)


@pytest.mark.parametrize('transition', [pytest.param(_GUARD_ID, id=_GUARD_ID)])
def test_corpus_absent_at_pin_is_a_named_transition_state(transition: str) -> None:
    """State the transition loudly: the pinned crysta predates the fitting corpus."""
    if CORPUS_PRESENT:
        pytest.skip('corpus present at the resolved root — the parametrized cases are the gate')
    pytest.skip(
        f'{transition} (resolved root {ROOT}); the EDI_CRYSTA_CORPUS_ROOT override arms the '
        'both-sides contract pre-merge'
    )


def _resolve_project_dir(case_dir: Path, case_id: str) -> Path:
    """The one realization target inside a corpus case.

    : a case may carry declared sidecars beside its project (goldens/, fullprof/,
    bounded-analysis/); the canonical `project` directory is the target when present, and a case
    with no unambiguous project stays a red, never a skip.
    """
    if (case_dir / 'project').is_dir():
        return case_dir / 'project'
    project_dirs = [p for p in case_dir.iterdir() if p.is_dir()]
    if len(project_dirs) != 1:
        pytest.fail(
            f'{case_id}: edi realizes project-directory cases; expected exactly one '
            f'project directory inside the case, found {sorted(p.name for p in project_dirs)!r} '
            f'— an unrealizable declared case is a red, never a skip'
        )
    return project_dirs[0]


def _assert_pin_declares_no_edi_side_case() -> None:
    """Prove an empty subject from the MANIFEST, never from an empty parametrisation.

    If the pin ever declares an edi side again, this fails loudly here instead of passing
    quietly as a placeholder — which is the whole point of naming the empty unit.
    """
    assert CORPUS_PRESENT, 'the absent-corpus state is the guard test, not this one'
    claimed = [
        row['id']
        for row in _manifest['cases']
        if row['sides'] in _EDI_SIDES
        or any(v.get('sides', row['sides']) in _EDI_SIDES for v in row.get('variants') or [])
    ]
    assert not claimed, (
        f'the pinned corpus declares edi-side cases {sorted(claimed)} but none were '
        f'parametrised — the runner and the manifest disagree'
    )


# An EMPTY edi-side subject is a legal state and must be a DECLARED one. Owner ruling 65
# replaced crysta's corpus wholesale, and every case the pin now carries declares
# `sides: crysta-only`, so `UNITS` is empty here. Handing pytest an empty parameter set turns
# the runner into ONE SKIPPED PLACEHOLDER named `[NOTSET]` — it reads like coverage in a report,
# asserts nothing, and ( §4.2/§4.3, and this file's own rule) the corpus paths never skip.
# So the empty case gets its own named unit that PROVES emptiness against the manifest instead.
_EMPTY_SUBJECT_ID = 'no-edi-side-case-at-pin'
_PARAMS = [
    pytest.param(case, row, id=case['id'] if row is None else f'{case["id"]}::{row["name"]}')
    for case, row in UNITS
] or [pytest.param(None, None, id=_EMPTY_SUBJECT_ID)]


@pytest.mark.parametrize(('case', 'variant'), _PARAMS)
def test_fitting_case_matches_expected_through_edi(
    case: dict | None, variant: dict | None, tmp_path: Path
) -> None:
    """Realize one corpus (case, variant) unit through edi's API and hold its quantities."""
    if case is None:
        _assert_pin_declares_no_edi_side_case()
        return
    case_dir = ROOT / case['id']
    # : realize on a DISPOSABLE COPY, never in place. A plain fit mutates only the
    # in-memory model, but a sequential case's fit writes its `analysis/results.csv` beside the
    # project BY CONTRACT — and this runner's corpus root can be a live checkout (crysta's
    # `edi-verification` step points `EDI_CRYSTA_CORPUS_ROOT` at the crysta tree in hand), where
    # an in-place write contaminates the corpus that repo's manifest-totality gate then walks
    # (measured 2026-09-09: one verify run left a stray results.csv in the crysta checkout).
    # The copy also keeps a re-run of a completed sequential case a FIT rather than a resume.
    project_dir = tmp_path / 'project'
    shutil.copytree(_resolve_project_dir(case_dir, case['id']), project_dir)
    #  (the sides flips): realize through the analysis facade, which dispatches by the
    # project's declared fitting mode — a joint case realized down the single path would
    # silently fit one bank (measured: chi2r 3.92 vs the joint 14.12 on ncaf-wish-3bank-s5).
    outcome = edi.Project.load(project_dir).analysis.fit()
    if not outcome.converged:
        pytest.fail(f'{case["id"]}: edi fit did not converge (status {outcome.status!r})')

    expected = json.loads((case_dir / 'expected.json').read_text(encoding='utf-8'))
    values = dict(outcome.values)
    quantities = dict(
        expected['variants'][variant['name']]['quantities']
        if variant is not None
        else expected['quantities']
    )
    #  (the sides flips): convergence-path-tight pins (iteration count, chi2/rwp at
    # absolute tolerance) are per-SIDE facts — the `edi` overlay re-pins exactly those keys
    # for this surface; every physics-anchored quantity stays shared.
    quantities.update(expected.get('edi', {}).get('quantities', {}))
    uncertainty = dict(outcome.uncertainty)
    bank_metrics = {bank.name: bank for bank in outcome.banks}
    sequential_rows = _read_sequential_rows(project_dir)

    def _resolve_parameter(label: str, table: dict) -> float:
        # The label seam: crysta's CLI record uses bare parameter labels; edi's
        # FitOutcome tables qualify them by owner and category (). Resolve
        # exact, then the category-qualified spellings — bank-qualified for a joint
        # case's `<bank>.<field>` labels, site-qualified for `<site>.<field>` — refusing
        # loudly on absence or ambiguity.
        candidates = [
            label,
            f'experiment.{label}',
            f'experiment.peak.{label}',
            f'experiment.instrument.{label}',
            f'experiment.linked_structure.{label}',
            f'experiment.absorption.{label}',
            f'structure.{label}',
            f'structure.cell.{label}',
        ]
        head, _, field = label.partition('.')
        if field:
            if head in bank_metrics:
                background = field.startswith('background[')
                candidates += [
                    f'experiments[{head}].{field}',
                    f'experiments[{head}].peak.{field}',
                    f'experiments[{head}].instrument.{field}',
                    f'experiments[{head}].absorption.{field}',
                ]
                candidates += (
                    [f'experiments[{head}].{field}.intensity']
                    if background
                    else [f'experiments[{head}].linked_structure.scale']
                    if field == 'scale'
                    else []
                )
            else:
                candidates.append(f'structure.atom_sites[{head}].{field}')
        hits = sorted({c for c in candidates if c in table})
        assert len(hits) == 1, (
            f"{case['id']}: refined parameter '{label}' resolves to {hits!r} — "
            f'need exactly one match'
        )
        return float(table[hits[0]])

    for name, spec in quantities.items():
        measured = _sequential_quantity(case['id'], name, sequential_rows)
        if measured is not None:
            pass
        elif name.startswith('param.') and name.endswith('.value'):
            measured = _resolve_parameter(name[len('param.') : -len('.value')], values)
        elif name.startswith('param.') and name.endswith(('.esd', '.uncertainty')):
            suffix = '.uncertainty' if name.endswith('.uncertainty') else '.esd'
            measured = _resolve_parameter(name[len('param.') : -len(suffix)], uncertainty)
        elif name.startswith('bank.') and name.endswith('.rwp'):
            bank_name = name[len('bank.') : -len('.rwp')]
            assert bank_name in bank_metrics, (
                f"{case['id']}: quantity '{name}' names bank {bank_name!r}, absent from the "
                f'joint outcome banks {sorted(bank_metrics)!r}'
            )
            measured = float(bank_metrics[bank_name].rwp)
        elif name == 'n_free':
            # The refined free-set size — the outcome's value table is exactly that set.
            measured = float(len(values))
        else:
            attr = OUTCOME_ATTRS.get(name)
            assert attr is not None, (
                f"{case['id']}: quantity '{name}' has no edi accessor mapping — extend "
                f'OUTCOME_ATTRS deliberately rather than skipping it'
            )
            measured = float(getattr(outcome, attr))
        _assert_quantity(case['id'], name, spec, measured)
