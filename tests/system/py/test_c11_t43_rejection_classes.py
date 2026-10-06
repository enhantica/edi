"""rejection gates for resume, modes, paths, and report surfaces."""

from __future__ import annotations

import ast
import csv
import io
import math
import os
import re
import shutil
import subprocess
import sys
import uuid
from pathlib import Path

import edi
import pytest

ROOT = Path(__file__).resolve().parents[3]
CORPUS_ROOT = Path(
    os.environ.get('EDI_CRYSTA_CORPUS_ROOT', ROOT / 'build/crysta-src/tests/fitting')
)
CASE = CORPUS_ROOT / 'cosio-d20-scan-3f'
REFERENCE = CASE / 'diffraction-lib' / 'project' / 'analysis' / 'results.csv'
DECLARED_MODES = {'single', 'joint', 'sequential', 'independent'}
LOOKALIKES = ('Sequential', 'sequentially', 'independent ', 'parallel', '', ' ', '\t')
NATIVE_ENTRY_BY_MODE = {
    mode: 'fit' if mode == 'single' else f'fit_{mode}' for mode in DECLARED_MODES
}


def _post_copy_touched_documents() -> tuple[str, ...]:
    documents = tuple(
        sorted(
            path.relative_to(CASE / 'project').as_posix()
            for path in (CASE / 'project').rglob('*.edi')
        )
    )
    assert documents, (
        ' CLI symlink-boundary coverage must discover the saved project documents '
        'mechanically from the public corpus tree'
    )
    return documents


def _copy_bounded_project(tmp_path: Path, name: str, *, max_iterations: int = 1) -> Path:
    project_dir = tmp_path / name
    shutil.copytree(CASE / 'project', project_dir)
    analysis = project_dir / 'analysis' / 'analysis.edi'
    text = analysis.read_text(encoding='utf-8')
    assert '_minimizer.max_iterations 1000' in text, (
        ' rejection controls require the corpus iteration declaration'
    )
    analysis.write_text(
        text.replace(
            '_minimizer.max_iterations 1000',
            f'_minimizer.max_iterations {max_iterations}',
        ),
        encoding='utf-8',
    )
    return project_dir


def _rewrite(project_dir: Path, old: str, new: str) -> None:
    analysis = project_dir / 'analysis' / 'analysis.edi'
    text = analysis.read_text(encoding='utf-8')
    assert old in text, f' rejection fixture requires {old!r} in analysis.edi'
    analysis.write_text(text.replace(old, new), encoding='utf-8')


def _reference_header_and_ascending_rows() -> tuple[list[str], list[dict[str, str]]]:
    with REFERENCE.open(newline='', encoding='utf-8') as stream:
        reader = csv.DictReader(stream)
        assert reader.fieldnames is not None, (
            ' completed-resume control requires the frozen reference header'
        )
        return list(reader.fieldnames), list(reversed(list(reader)))


def _write_completed_results(
    project_dir: Path, completed_state: str = 'all-success'
) -> dict[str, str]:
    fieldnames, rows = _reference_header_and_ascending_rows()
    rows = [dict(row) for row in rows]
    if completed_state == 'failed-tail':
        rows[-1]['fit_result.success'] = 'False'
    elif completed_state == 'all-failed':
        for row in rows:
            row['fit_result.success'] = 'False'
    with (project_dir / 'analysis' / 'results.csv').open(
        'w', newline='', encoding='utf-8'
    ) as stream:
        writer = csv.DictWriter(stream, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    return rows[-1]


def _write_completed_partition(
    project_dir: Path, completed_state: str
) -> tuple[dict[str, str], dict[str, str] | None]:
    fieldnames, rows = _reference_header_and_ascending_rows()
    rows = [dict(row) for row in rows]
    if completed_state == 'failed-tail':
        rows[-1]['fit_result.success'] = 'False'
        # Deliberate control sentinels, not scientific expectations: they make substituting the
        # carry-forward row for the terminal outcome row observable on both edi surfaces.
        rows[-2]['fit_result.iterations'] = '271'
        rows[-1]['fit_result.iterations'] = '314'
        rows[-2]['fit_result.reduced_chi_square'] = '2.75'
        rows[-1]['fit_result.reduced_chi_square'] = '12.5'
        rows[-2]['cosio.cell.length_a'] = '10.25'
        rows[-1]['cosio.cell.length_a'] = '10.625'
    elif completed_state == 'all-failed':
        for row in rows:
            row['fit_result.success'] = 'False'
    with (project_dir / 'analysis' / 'results.csv').open(
        'w', newline='', encoding='utf-8'
    ) as stream:
        writer = csv.DictWriter(stream, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    successful = [row for row in rows if row['fit_result.success'] == 'True']
    return rows[-1], successful[-1] if successful else None


def _read_results(project_dir: Path) -> list[dict[str, str]]:
    with (project_dir / 'analysis' / 'results.csv').open(newline='', encoding='utf-8') as stream:
        return list(csv.DictReader(stream))


def _scan_payloads(rows: list[dict[str, str]]) -> dict[str, dict[str, str]]:
    return {
        Path(row['file_path']).name: {
            key: value
            for key, value in row.items()
            if key not in {'file_path', 'diffrn.ambient_temperature'}
        }
        for row in rows
    }


def _analysis_fit_docstring() -> str:
    """Read the shipped facade doc, not the test policy's runtime wrapper."""
    source = ast.parse((ROOT / 'lib' / 'edi' / '__init__.py').read_text(encoding='utf-8'))
    analysis = [
        node for node in source.body if isinstance(node, ast.ClassDef) and node.name == 'Analysis'
    ]
    assert len(analysis) == 1, (
        ' documentation gate requires exactly one shipped edi.Analysis definition'
    )
    fit = [
        node
        for node in analysis[0].body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == 'fit'
    ]
    assert len(fit) == 1, (
        ' documentation gate requires exactly one shipped edi.Analysis.fit definition'
    )
    return ast.get_docstring(fit[0], clean=False) or ''


def _template_restart_controls(tmp_path: Path) -> dict[str, dict[str, str]]:
    controls: dict[str, dict[str, str]] = {}
    source_names = sorted(
        path.name for path in (CASE / 'project/experiments/d20_scan').glob('*.dat')
    )
    for index, source_name in enumerate(source_names):
        project_dir = _copy_bounded_project(tmp_path, f'independent-control-{index}')
        scan_dir = project_dir / 'experiments' / 'd20_scan'
        for data_file in scan_dir.glob('*.dat'):
            if data_file.name != source_name:
                data_file.unlink()
        control = edi.Project.load(project_dir)
        control.analysis.fitting_mode = 'sequential'
        control.analysis.fit()
        controls.update(_scan_payloads(_read_results(project_dir)))
    return controls


def _run_cli(project_dir: Path, *options: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, '-m', 'edi', 'fit', str(project_dir), *options],
        cwd=ROOT,
        env={**os.environ, 'OMP_DYNAMIC': 'FALSE', 'OMP_NUM_THREADS': '1'},
        check=False,
        capture_output=True,
        text=True,
        timeout=120,
    )


_RESULT_SOURCE_BY_FIELD = {
    'banks': 'not applicable to a sequential terminal result',
    'converged': 'fit_result.success',
    'fitting_time': 'unavailable: no solve ran',
    'iterations': 'fit_result.iterations',
    'reduced_chi_square': 'fit_result.reduced_chi_square',
    'result_kind': 'sequential operation invariant',
    'rwp': 'unavailable: no results.csv column',
    'status': 'per-file provenance termination; unavailable only for legacy rows',
    'success': 'fit_result.success',
    'uncertainty': '<parameter>.uncertainty columns',
    'values': '<parameter> value columns',
}


def _live_cause_project(tmp_path: Path, name: str, live_cause: str) -> tuple[Path, object]:
    max_iterations = 1 if live_cause == 'max-iter' else 3
    project_dir = _copy_bounded_project(tmp_path, name, max_iterations=max_iterations)
    project = edi.Project.load(project_dir)
    if live_cause == 'no-step':
        # The visible crysta constrained-solver witness establishes this as a real
        # NO_ACCEPTED_STEP route: all proposed trials become non-finite and are rejected.
        project.experiments[0].linked_structure.scale.value = 1e152
    return project_dir, project


@pytest.mark.parametrize('completed_state', ['all-success', 'failed-tail', 'all-failed'])
def test_completed_resume_partitions_terminal_outcome_on_python(
    tmp_path: Path, completed_state: str
) -> None:
    project_dir = _copy_bounded_project(tmp_path, f'python-partition-{completed_state}')
    terminal, carry_forward = _write_completed_partition(project_dir, completed_state)

    project = edi.Project.load(project_dir)
    outcome = project.analysis.fit()
    expected_converged = terminal['fit_result.success'] == 'True'

    assert outcome.converged is expected_converged, (
        ' edi Python completed resume must recover convergence from the terminal row, '
        f'not the carry-forward selector; state={completed_state}'
    )
    assert outcome.success is outcome.converged, (
        ' edi Python resume success alias must agree with recovered convergence'
    )
    expected_status = edi.FitStatus.DONE if expected_converged else edi.FitStatus.UNAVAILABLE
    assert outcome.status == expected_status, (
        ' edi Python completed resume must map persisted success to DONE and an '
        f'unpersisted failure cause to UNAVAILABLE; state={completed_state}'
    )
    assert outcome.iterations == int(terminal['fit_result.iterations']), (
        ' edi Python completed resume must recover terminal iterations'
    )
    assert outcome.reduced_chi_square == pytest.approx(
        float(terminal['fit_result.reduced_chi_square']), rel=0.0, abs=0.0
    ), ' edi Python completed resume must recover terminal reduced chi-square'
    assert project.structure.cell.length_a.value == pytest.approx(
        float(terminal['cosio.cell.length_a']), rel=0.0, abs=0.0
    ), ' edi Python completed resume must write back the terminal model state'

    if completed_state == 'failed-tail':
        assert carry_forward is not None, (
            ' edi Python mixed-state control requires a successful predecessor'
        )
        assert carry_forward is not terminal, (
            ' edi Python mixed-state control requires predecessor and terminal to differ'
        )
        substituted = carry_forward
        assert outcome.iterations != int(substituted['fit_result.iterations']), (
            ' edi Python outcome-selector substitution exercise must reject '
            'carry-forward iterations'
        )
        assert not math.isclose(
            outcome.reduced_chi_square,
            float(substituted['fit_result.reduced_chi_square']),
            rel_tol=0.0,
            abs_tol=1e-12,
        ), (
            ' edi Python outcome-selector substitution exercise must reject the '
            'carry-forward reduced chi-square'
        )
        assert not math.isclose(
            project.structure.cell.length_a.value,
            float(substituted['cosio.cell.length_a']),
            rel_tol=0.0,
            abs_tol=1e-12,
        ), (
            ' edi Python outcome-selector substitution exercise must reject the '
            'carry-forward model state'
        )


@pytest.mark.parametrize('completed_state', ['all-success', 'failed-tail', 'all-failed'])
def test_completed_resume_partitions_terminal_outcome_on_cli(
    tmp_path: Path, completed_state: str
) -> None:
    project_dir = _copy_bounded_project(tmp_path, f'cli-partition-{completed_state}')
    terminal, carry_forward = _write_completed_partition(project_dir, completed_state)

    completed = _run_cli(project_dir, '--dry', '--report', 'machine', '--verbosity', 'compact')
    assert completed.returncode == 0, (
        f' completed CLI partition must run: {completed.stderr[-500:]!r}'
    )
    record = dict(line.split('=', 1) for line in completed.stdout.splitlines() if '=' in line)
    expected_converged = terminal['fit_result.success'] == 'True'
    assert record['converged'] == ('true' if expected_converged else 'false'), (
        ' edi machine record must recover convergence from the terminal row, not the '
        f'carry-forward selector; state={completed_state}'
    )
    assert record['status'] == ('done' if expected_converged else 'unavailable'), (
        ' edi machine record must map persisted success to done and an unpersisted '
        f'failure cause to unavailable; state={completed_state}'
    )
    assert int(record['iterations']) == int(terminal['fit_result.iterations']), (
        ' edi machine record must recover terminal iterations'
    )
    expected_chi_square = format(float(terminal['fit_result.reduced_chi_square']), '.10g')
    assert record['reduced_chi_square'] == expected_chi_square, (
        ' edi machine record must recover terminal reduced chi-square'
    )

    if completed_state == 'failed-tail':
        assert carry_forward is not None, (
            ' edi CLI mixed-state control requires a successful predecessor'
        )
        assert carry_forward is not terminal, (
            ' edi CLI mixed-state control requires predecessor and terminal to differ'
        )
        substituted = carry_forward
        assert int(record['iterations']) != int(substituted['fit_result.iterations']), (
            ' edi CLI outcome-selector substitution exercise must reject carry-forward iterations'
        )
        assert record['reduced_chi_square'] != format(
            float(substituted['fit_result.reduced_chi_square']), '.10g'
        ), (
            ' edi CLI outcome-selector substitution exercise must reject the '
            'carry-forward reduced chi-square'
        )


def _prepare_cause_ledger(project_dir, terminal, live_cause, ledger, max_iterations):
    provenance = project_dir / 'analysis/results-provenance.csv'
    recorded = list(csv.DictReader(io.StringIO(provenance.read_text())))
    expected_reason = 'max_iter_exhausted' if live_cause == 'max-iter' else 'no_accepted_step'
    terminal_name = Path(terminal['file_path']).name
    terminal_ledger = next(row for row in recorded if Path(row['file_path']).name == terminal_name)
    assert terminal_ledger['termination'] == expected_reason, (
        'Resume witness: the producing ledger records the independently admitted terminal cause'
    )
    if ledger == 'legacy':
        provenance.unlink()
    else:
        # Put the terminal entry first and poison the other entries: selecting the last ledger
        # row, or re-inferring from the current bound, must fail this identity-based witness.
        others = [dict(row) for row in recorded if row is not terminal_ledger]
        for row in others:
            row['termination'] = 'converged'
        _write_cause_rows(provenance, [terminal_ledger, *others])
        csv_path = project_dir / 'analysis/results.csv'
        csv_rows = list(csv.DictReader(io.StringIO(csv_path.read_text())))
        _write_cause_rows(csv_path, [csv_rows[-1], *csv_rows[:-1]])
    analysis = project_dir / 'analysis/analysis.edi'
    analysis.write_text(
        analysis.read_text().replace(
            f'_minimizer.max_iterations {max_iterations}', '_minimizer.max_iterations 17'
        )
    )


def _write_cause_rows(path, rows):
    with path.open('w', newline='', encoding='utf-8') as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


@pytest.mark.parametrize('ledger', ['recorded', 'legacy'])
@pytest.mark.parametrize('live_cause', ['max-iter', 'no-step'])
def test_completed_resume_recovers_recorded_cause_or_legacy_unknown_on_python(
    tmp_path: Path, live_cause: str, ledger: str
) -> None:
    project_dir, project = _live_cause_project(tmp_path, f'python-{live_cause}', live_cause)
    live = project.analysis.fit()
    expected_live = edi.FitStatus.MAX_ITER if live_cause == 'max-iter' else edi.FitStatus.NO_STEP
    assert live.status == expected_live, (
        f' edi Python {live_cause} witness must reach its distinct live terminal cause'
    )

    fieldnames, _reference_rows = _reference_header_and_ascending_rows()
    with (project_dir / 'analysis' / 'results.csv').open(newline='', encoding='utf-8') as stream:
        reader = csv.DictReader(stream)
        assert reader.fieldnames == fieldnames, (
            ' edi cause honesty must retain the frozen diffraction-lib column identities'
        )
        assert len(fieldnames) == 83, (
            ' edi cause honesty must retain the frozen diffraction-lib 83-column header'
        )
        terminal = list(reader)[-1]

    observed_fields = {name for name in dir(live) if not name.startswith('_')}
    assert observed_fields == set(_RESULT_SOURCE_BY_FIELD), (
        ' every edi public resumed result field must remain in the mechanical source '
        'inventory; a new field cannot silently inherit a default'
    )

    _prepare_cause_ledger(
        project_dir, terminal, live_cause, ledger, 1 if live_cause == 'max-iter' else 3
    )
    completed_project = edi.Project.load(project_dir)
    outcome = completed_project.analysis.fit()
    assert outcome.converged is False, (
        f' edi Python completed {live_cause} resume must retain non-convergence'
    )
    assert outcome.success is outcome.converged, (
        ' edi Python resume success alias must agree with recovered convergence'
    )
    unavailable = getattr(edi.FitStatus, 'UNAVAILABLE', None)
    assert unavailable is not None, (
        ' edi needs an explicit public status for an unavailable resumed terminal cause'
    )
    assert outcome.status == (expected_live if ledger == 'recorded' else unavailable), (
        'Completed resume recovers the terminal file cause from provenance despite row '
        'reordering and a changed bound; absent legacy provenance stays unknown'
    )
    assert outcome.iterations == int(terminal['fit_result.iterations']), (
        ' edi Python resume must recover iterations instead of publishing zero'
    )
    assert outcome.reduced_chi_square == pytest.approx(
        float(terminal['fit_result.reduced_chi_square']), rel=0.0, abs=0.0
    ), ' edi Python resume must recover terminal reduced chi-square'
    assert math.isnan(outcome.rwp), (
        ' edi Python resume must mark unavailable Rwp as NaN, never measured-looking zero'
    )
    assert outcome.fitting_time is None, (
        ' edi Python resume must report no fitting time because no solve ran'
    )
    assert outcome.result_kind == 'deterministic', (
        ' edi Python resume must retain the public least-squares result kind'
    )
    assert not outcome.banks, (
        ' scan resume must not fabricate per-bank metrics from the terminal scan row'
    )
    assert set(outcome.values), ' edi Python resume must recover the terminal parameter map'
    assert set(outcome.values) == set(outcome.uncertainty), (
        ' edi Python resume must recover an uncertainty for every returned parameter'
    )
    assert completed_project.structure.cell.length_a.value == pytest.approx(
        float(terminal['cosio.cell.length_a']), rel=0.0, abs=0.0
    ), (
        ' edi Python resume must write back the actual terminal row, not the earlier '
        f'carry-forward seed; live={live_cause}'
    )


@pytest.mark.parametrize('ledger', ['recorded', 'legacy'])
@pytest.mark.parametrize('live_cause', ['max-iter', 'no-step'])
def test_completed_resume_cli_recovers_recorded_cause_or_legacy_unknown(
    tmp_path: Path, live_cause: str, ledger: str
) -> None:
    _source_dir, project = _live_cause_project(tmp_path, f'cli-source-{live_cause}', live_cause)
    project_dir = tmp_path / f'cli-{live_cause}'
    project.save_as(project_dir)

    live = _run_cli(project_dir, '--report', 'machine', '--verbosity', 'compact')
    assert live.returncode == 0, f' live CLI cause witness must run: {live.stderr[-500:]!r}'
    live_record = dict(line.split('=', 1) for line in live.stdout.splitlines() if '=' in line)
    expected_live = 'max_iter' if live_cause == 'max-iter' else 'no_step'
    assert live_record['status'] == expected_live, (
        f' edi CLI {live_cause} witness must publish its distinct live terminal cause'
    )

    fieldnames, _reference_rows = _reference_header_and_ascending_rows()
    with (project_dir / 'analysis' / 'results.csv').open(newline='', encoding='utf-8') as stream:
        reader = csv.DictReader(stream)
        assert reader.fieldnames == fieldnames, (
            ' CLI cause honesty must retain frozen diffraction-lib column identities'
        )
        assert len(fieldnames) == 83, (
            ' CLI cause honesty must retain the frozen diffraction-lib 83-column header'
        )
        terminal = list(reader)[-1]

    _prepare_cause_ledger(
        project_dir, terminal, live_cause, ledger, 1 if live_cause == 'max-iter' else 3
    )
    completed = _run_cli(project_dir, '--report', 'machine', '--verbosity', 'compact')
    assert completed.returncode == 0, (
        f' completed CLI resume must succeed: {completed.stderr[-500:]!r}'
    )
    record = dict(line.split('=', 1) for line in completed.stdout.splitlines() if '=' in line)
    assert record['converged'] == 'false', (
        f' CLI completed {live_cause} resume must retain terminal non-convergence'
    )
    assert record['status'] == (expected_live if ledger == 'recorded' else 'unavailable'), (
        'Completed CLI resume recovers the terminal file cause from provenance despite row '
        'reordering and a changed bound; absent legacy provenance stays unknown'
    )
    assert int(record['iterations']) == int(terminal['fit_result.iterations']), (
        ' CLI resume must report recovered terminal iterations, never synthetic zero'
    )
    expected_chi_square = format(float(terminal['fit_result.reduced_chi_square']), '.10g')
    assert record['reduced_chi_square'] == expected_chi_square, (
        ' CLI resume must report the terminal CSV reduced chi-square through the '
        "machine contract's 10-significant-digit representation"
    )
    assert math.isnan(float(record['rwp'])), (
        ' CLI resume must render unavailable Rwp explicitly as NaN, never zero'
    )


def test_mode_contract_is_closed_across_edi_loader_setters_dispatch_native_and_save(  # noqa: PLR0912, PLR0914, PLR0915
    tmp_path: Path,
) -> None:
    violations: list[str] = []
    for index, mode in enumerate(sorted(DECLARED_MODES)):
        project_dir = _copy_bounded_project(tmp_path, f'declared-load-{index}')
        _rewrite(project_dir, 'sequential\n', f'{mode}\n')
        loaded = edi.Project.load(project_dir)
        if loaded.analysis.fitting_mode != mode:
            violations.append(
                f'loader changed declared mode {mode!r} to {loaded.analysis.fitting_mode!r}'
            )

        for surface in (loaded, loaded.analysis):
            surface.fitting_mode = mode
            if surface.fitting_mode != mode:
                violations.append(
                    f'{type(surface).__name__} setter changed {mode!r} to {surface.fitting_mode!r}'
                )

        saved_mode = tmp_path / f'declared-saved-{index}'
        loaded.save_as(saved_mode)
        round_trip = edi.Project.load(saved_mode).analysis.fitting_mode
        if round_trip != mode:
            violations.append(f'{mode!r} save/reload returned {round_trip!r}')

    invalid_tokens = (*LOOKALIKES, f'undeclared-{uuid.uuid4().hex}')
    for index, token in enumerate(invalid_tokens):
        quoted = f'"{token}"' if not token or token.isspace() or token.endswith(' ') else token
        project_dir = _copy_bounded_project(tmp_path, f'load-{index}')
        _rewrite(project_dir, 'sequential\n', f'{quoted}\n')
        try:
            edi.Project.load(project_dir)
        except ValueError:
            pass
        else:
            violations.append(f'loader accepted {token!r}')

        for surface in ('project', 'analysis'):
            project = edi.Project.load(CASE / 'project')
            target = project if surface == 'project' else project.analysis
            try:
                target.fitting_mode = token
            except ValueError:
                pass
            else:
                violations.append(f'{surface} setter accepted {token!r}')

    independent_dir = _copy_bounded_project(tmp_path, 'independent')
    project = edi.Project.load(independent_dir)
    project.analysis.fitting_mode = 'independent'
    saved = tmp_path / 'independent-saved'
    project.save_as(saved)
    reloaded = edi.Project.load(saved)
    if reloaded.analysis.fitting_mode != 'independent':
        violations.append(f'independent round-trip returned {reloaded.analysis.fitting_mode!r}')
    native_scan_entries = {
        name
        for name in dir(reloaded)
        if name.startswith('fit_') and name.endswith(tuple(DECLARED_MODES))
    }
    expected_native_entries = {'fit_independent', 'fit_sequential'}
    missing_native_entries = expected_native_entries - native_scan_entries
    if missing_native_entries:
        violations.append(f'native scan entry points absent: {sorted(missing_native_entries)!r}')
    try:
        reloaded.fit()
    except ValueError:
        pass
    else:
        violations.append('direct Project.fit silently accepted independent mode')
    try:
        reloaded.analysis.fit()
    except ValueError as error:
        violations.append(f'independent facade dispatch refused: {error}')
    else:
        if not (saved / 'analysis' / 'results.csv').is_file():
            violations.append(
                'independent facade dispatch ran one template fit without results.csv'
            )
        else:
            actual = _scan_payloads(_read_results(saved))
            expected = _template_restart_controls(tmp_path)
            if actual != expected:
                files = f'actual={sorted(actual)!r}, expected={sorted(expected)!r}'
                violations.append(
                    'independent facade did not restart every scan file from the unchanged '
                    f'template: {files}'
                )

            if 'fit_independent' in native_scan_entries:
                direct_dir = _copy_bounded_project(tmp_path, 'independent-direct')
                direct = edi.Project.load(direct_dir)
                direct.analysis.fitting_mode = 'independent'
                direct.fit_independent()
                direct_rows = _scan_payloads(_read_results(direct_dir))
                if direct_rows != expected:
                    files = f'actual={sorted(direct_rows)!r}, expected={sorted(expected)!r}'
                    violations.append(
                        'native fit_independent did not implement template-restart semantics: '
                        f'{files}'
                    )

    # The autoloaded fit-policy fixture wraps edi.Analysis.fit during every repo pytest session;
    # that sentinel deliberately has no docstring.  Judge the production facade definition that
    # ships to users, rather than the test harness object installed around it.
    fit_doc = _analysis_fit_docstring()
    missing_docs = sorted(mode for mode in DECLARED_MODES if mode not in fit_doc)
    if missing_docs:
        violations.append(f'Analysis.fit docs omit {missing_docs!r}')
    assert not violations, (
        ' declares exactly single/joint/sequential/independent across the edi loader, '
        'both setters, facade dispatch, direct native entries, save/reload and docs; violations='
        f'{violations!r}'
    )


def test_declared_mode_by_native_entry_matrix_is_exact(tmp_path: Path) -> None:
    """Every native refinement entry accepts exactly its declared mode, not a family."""
    probe = edi.Project.load(CASE / 'project')
    discovered_entries = {name for name in dir(probe) if name == 'fit' or name.startswith('fit_')}
    expected_entries = set(NATIVE_ENTRY_BY_MODE.values())
    assert discovered_entries == expected_entries, (
        ' native-entry matrix must classify every public refinement entry; '
        f'missing={sorted(expected_entries - discovered_entries)!r}, '
        f'unclassified={sorted(discovered_entries - expected_entries)!r}'
    )

    violations: list[str] = []
    for mode in sorted(DECLARED_MODES):
        for entry in sorted(discovered_entries):
            project_dir = _copy_bounded_project(tmp_path, f'matrix-{mode}-{entry}')
            project = edi.Project.load(project_dir)
            project.analysis.fitting_mode = mode
            try:
                getattr(project, entry)()
            except ValueError as error:
                if entry == NATIVE_ENTRY_BY_MODE[mode]:
                    violations.append(f'{mode}->{entry} refused its matching route: {error!s}')
                elif not re.search(r'fitting_mode|fitting mode|mode', str(error), re.IGNORECASE):
                    violations.append(
                        f'{mode}->{entry} reached a later error instead of refusing at the '
                        f'mode boundary: {error!s}'
                    )
            else:
                if entry != NATIVE_ENTRY_BY_MODE[mode]:
                    violations.append(f'{mode}->{entry} accepted a cross-mode call')

    assert not violations, (
        ' requires the full declared-mode x native-entry matrix to be exact; '
        f'violations={violations!r}'
    )


def test_cli_persistence_never_follows_a_retained_touched_document_symlink(
    tmp_path: Path,
) -> None:
    """The persist-by-default surface preserves the same symlink boundary as crysta save."""
    violations: list[str] = []
    for index, relative_document in enumerate(_post_copy_touched_documents()):
        project_dir = _copy_bounded_project(tmp_path, f'cli-symlink-{index}')
        _write_completed_results(project_dir)
        touched = project_dir / relative_document
        external = tmp_path / f'external-{relative_document.replace("/", "-")}'
        external.write_bytes(touched.read_bytes())
        expected_external = external.read_bytes()
        touched.unlink()
        touched.symlink_to(os.path.relpath(external, start=touched.parent))

        completed = _run_cli(project_dir, '--report', 'machine', '--verbosity', 'off')
        if completed.returncode == 0:
            if touched.is_symlink():
                violations.append(
                    'successful CLI persistence retained an outside-project alias at '
                    f'{relative_document}'
                )
        elif not re.search(r'symlink|symbolic|reserved|project', completed.stderr, re.IGNORECASE):
            violations.append(
                'CLI refusal omitted a symlink-boundary diagnostic at '
                f'{relative_document}: stderr={completed.stderr[-500:]!r}'
            )
        if external.read_bytes() != expected_external:
            violations.append(f'external target was rewritten through {relative_document}')

    assert not violations, (
        ' CLI persistence must never follow any retained relative symlink while '
        'reconciling or regenerating mechanically discovered touched documents; '
        f'violations={violations!r}'
    )


@pytest.mark.parametrize('escape', ['absolute', 'parent'])
def test_edi_data_dir_lexical_escape_refuses_at_load(tmp_path: Path, escape: str) -> None:
    project_dir = _copy_bounded_project(tmp_path, f'lexical-{escape}')
    outside = tmp_path / 'outside-scan'
    shutil.copytree(project_dir / 'experiments' / 'd20_scan', outside)
    spelling = str(outside) if escape == 'absolute' else '../outside-scan'
    _rewrite(
        project_dir,
        '_sequential_fit.data_dir experiments/d20_scan',
        f'_sequential_fit.data_dir {spelling}',
    )
    with pytest.raises(ValueError, match=r'data_dir|relative|project'):
        edi.Project.load(project_dir)


@pytest.mark.parametrize('operation', ['fit', 'save'])
def test_edi_data_dir_symlink_escape_refuses_before_conversion_or_save(
    tmp_path: Path, operation: str
) -> None:
    project_dir = _copy_bounded_project(tmp_path, f'symlink-{operation}')
    outside = tmp_path / f'outside-{operation}'
    scan_dir = project_dir / 'experiments' / 'd20_scan'
    shutil.copytree(scan_dir, outside)
    shutil.rmtree(scan_dir)
    scan_dir.symlink_to(outside, target_is_directory=True)
    project = edi.Project.load(project_dir)

    action = (
        project.analysis.fit if operation == 'fit' else lambda: project.save_as(tmp_path / 'saved')
    )
    with pytest.raises(ValueError, match=r'data_dir|symlink|outside|project'):
        action()


def _iteration_numbers(output: str) -> list[int]:
    return [
        int(match.group(1))
        for line in output.splitlines()
        if (match := re.match(r'^\s*(\d+)\s+\d+\.\d+', line))
    ]


def _human_reporting_violations(output: str, *, expected_files: int) -> list[str]:
    iterations = _iteration_numbers(output)
    progress = [
        (int(match.group(1)), int(match.group(2)))
        for line in output.splitlines()
        if (match := re.match(r'^\[[█░]+\] · (\d+)/(\d+) ·', line))
    ]
    violations = []
    expected_progress = [(completed, expected_files) for completed in range(1, expected_files + 1)]
    if progress != expected_progress:
        violations.append(
            f'scan preamble/completion counts={progress!r}, expected={expected_progress!r}'
        )
    if iterations and iterations != sorted(set(iterations)):
        violations.append(f'ambiguous restarted iterations={iterations!r}')
    return violations


@pytest.mark.parametrize('verbosity', ['off', 'compact', 'full'])
def test_sequential_human_reporting_preserves_each_verbosity_contract(
    tmp_path: Path, verbosity: str
) -> None:
    project_dir = _copy_bounded_project(tmp_path, f'human-{verbosity}')
    completed = _run_cli(project_dir, '--dry', '--report', 'human', '--verbosity', verbosity)
    assert completed.returncode == 0, (
        f' human sequential report {verbosity} must succeed: {completed.stderr[-500:]!r}'
    )
    if verbosity == 'off':
        assert not completed.stdout, (
            ' human verbosity=off must suppress every scan progress and summary row'
        )
        return
    expected_files = len(list((project_dir / 'experiments' / 'd20_scan').glob('*.dat')))
    assert expected_files > 1, ' sequential-report control requires multiple declared scan files'
    violations = _human_reporting_violations(
        completed.stdout,
        expected_files=expected_files,
    )
    if verbosity == 'compact':
        default_dir = _copy_bounded_project(tmp_path, 'human-default-options')
        default = _run_cli(default_dir, '--dry')
        if default.returncode != 0:
            violations.append(f'default invocation failed: {default.stderr[-500:]!r}')
        else:
            violations.extend(
                f'default invocation: {item}'
                for item in _human_reporting_violations(
                    default.stdout,
                    expected_files=expected_files,
                )
            )
    assert not violations, (
        ' human scan reporting must emit an honest preamble and one unambiguous '
        'scan-level iteration sequence, or suppress incompatible per-file streaming; '
        f'verbosity={verbosity}, violations={violations!r}'
    )


@pytest.mark.parametrize('verbosity', ['off', 'compact', 'full'])
def test_sequential_machine_stream_preserves_each_verbosity_contract(
    tmp_path: Path, verbosity: str
) -> None:
    project_dir = _copy_bounded_project(tmp_path, f'machine-{verbosity}')
    completed = _run_cli(
        project_dir, '--dry', '--report', 'machine', '--stream', '--verbosity', verbosity
    )
    assert completed.returncode == 0, (
        f' streamed machine report {verbosity} must succeed: {completed.stderr[-500:]!r}'
    )
    progress = [
        int(line.split('=', 1)[1])
        for line in completed.stdout.splitlines()
        if line.startswith('iter=')
    ]
    if verbosity == 'off':
        assert not progress and not completed.stdout, (
            ' machine verbosity=off must suppress progress and terminal records'
        )
    else:
        assert not progress or progress == sorted(set(progress)), (
            ' machine scan streaming must use an unambiguous scan-level iteration '
            f'sequence or suppress per-file progress; got {progress!r}'
        )


def test_sequential_direct_callbacks_never_emit_orphaned_per_file_progress(
    tmp_path: Path,
) -> None:
    project_dir = _copy_bounded_project(tmp_path, 'callbacks')
    starts: list[object] = []
    iterations: list[int] = []
    project = edi.Project.load(project_dir)
    project.analysis.fit(
        on_start=starts.append,
        on_iteration=lambda record: iterations.append(record.iteration),
    )
    violations = []
    if iterations and len(starts) != 1:
        violations.append(f'{len(starts)} preambles for {len(iterations)} progress rows')
    if iterations and iterations != sorted(set(iterations)):
        violations.append(f'ambiguous restarted iterations={iterations!r}')
    assert not violations, (
        ' direct scan callbacks must emit one honest preamble and an unambiguous '
        'scan-level iteration sequence, or suppress incompatible per-file callbacks; '
        f'violations={violations!r}'
    )
