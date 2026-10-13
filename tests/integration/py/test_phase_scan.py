"""Scan equivalence, linear scale recovery and unchanged-data persistence."""

import csv
from pathlib import Path

import edi as engine
import numpy as np
import pytest

from tests.fixtures import phase_scan
from tests.fixtures.multiphase import support


def csv_rows(path):
    with path.open(newline='') as stream:
        return list(csv.DictReader(stream))


def scales(project):
    return [support.links(project.experiments[0])[name].scale.value for name in ('alpha', 'beta')]


@pytest.mark.parametrize('mode', ['sequential', 'independent'])
def test_phase_scan_equals_single_fits_and_recovers_linear_coefficients(tmp_path, mode):
    directory = phase_scan.materialize(tmp_path / 'scan', mode)
    project = engine.Project.load(directory)
    events = []
    project.analysis.fit(on_file_complete=events.append)
    rows = csv_rows(directory / 'analysis/results.csv')
    assert len(rows) == len(events) == 3, (
        'A two-phase scan must emit one durable row and event per file'
    )
    parameter_columns = [key for key in rows[0] if key.endswith('.scale')]
    assert len(parameter_columns) == len(set(parameter_columns)) == 2, (
        'Both free phase scales require distinct results columns'
    )
    assert all(key + '.uncertainty' in rows[0] for key in parameter_columns), (
        'Every free phase scale requires its own uncertainty column'
    )
    previous = [1.125, 0.875]
    for index, row in enumerate(rows):
        points = np.loadtxt(directory / f'experiments/scan/{index + 1:02d}.xy')
        start = previous if mode == 'sequential' else [1.125, 0.875]
        control = engine.Project.load(
            phase_scan.single(tmp_path / f'control-{index}', start, points[:, 1])
        )
        outcome = control.analysis.fit()
        assert outcome.converged and row['fit_result.success'] == 'True', (
            'Each scan file and its single multiphase control must converge'
        )
        actual = [
            float(row[next(key for key in parameter_columns if name in key)])
            for name in ('alpha', 'beta')
        ]
        np.testing.assert_allclose(
            actual,
            scales(control),
            rtol=2e-10,
            atol=1e-10,
            err_msg='Each scan fit must equal the single multiphase fit from its prescribed start',
        )
        np.testing.assert_allclose(
            actual,
            phase_scan.COEFFICIENTS[index],
            rtol=2e-7,
            atol=1e-9,
            err_msg='Distinct phase scales must recover the known linear '
            'coefficients of frozen basis inputs',
        )
        assert int(row['fit_result.iterations']) == outcome.iterations, (
            'Scan and single controls must use identical starts and stopping conditions'
        )
        previous = scales(control)
    saved = tmp_path / 'reopened'
    project.save_as(saved)
    reopened = engine.Project.load(saved)
    assert scales(reopened) == scales(project), (
        'Reopening a fitted scan must retain both terminal phase scales'
    )
    assert csv_rows(saved / 'analysis/results.csv') == rows, (
        'Reopening must preserve every phase result column and row'
    )


@pytest.mark.parametrize('mode', ['sequential', 'independent'])
def test_negative_points_and_zero_files_preserve_successful_scan(tmp_path, mode):
    clean_dir = phase_scan.materialize(tmp_path / 'clean', mode)
    dirty_dir = phase_scan.materialize(tmp_path / 'dirty', mode, negative=True, zero=True)
    engine.Project.load(clean_dir).analysis.fit()
    events = []
    engine.Project.load(dirty_dir).analysis.fit(on_file_complete=events.append)
    clean = csv_rows(clean_dir / 'analysis/results.csv')
    dirty = csv_rows(dirty_dir / 'analysis/results.csv')
    assert dirty == clean and len(events) == 3, (
        'Skipping a negative point and an all-zero file must '
        'preserve valid per-file fits and continue the scan'
    )
    notes = csv_rows(dirty_dir / 'analysis/scan-notes.csv')
    assert {
        Path(row['file_path']).name: (row['negative_points'], row['skipped_dataset'])
        for row in notes
    } == {'02.xy': ('1', 'False'), '02a.xy': ('0', 'True')}, (
        'Scan notes must report the counted negative point and the skipped zero dataset'
    )


@pytest.mark.parametrize('operation', ['save', 'save_as'])
def test_scan_save_reuses_unchanged_data_inodes(tmp_path, operation):
    directory = phase_scan.materialize(tmp_path / 'input')
    sources = {
        path.name: (
            path.stat().st_dev,
            path.stat().st_ino,
            path.read_bytes(),
            path.stat().st_mtime_ns,
        )
        for path in (directory / 'experiments/scan').glob('*.xy')
    }
    project = engine.Project.load(directory)
    for index in range(2):
        destination = directory if operation == 'save' else tmp_path / f'saved-{index}'
        if operation == 'save':
            project.save()
        else:
            project.save_as(destination)
        for name, before in sources.items():
            path = destination / 'experiments/scan' / name
            assert (
                path.stat().st_dev,
                path.stat().st_ino,
                path.read_bytes(),
                path.stat().st_mtime_ns,
            ) == before, (
                'Atomic scan saves on one filesystem must reuse the '
                'unchanged data rather than copy or rewrite it'
            )
        project = engine.Project.load(destination)


@pytest.mark.parametrize('mode', ['sequential', 'independent'])
def test_failure_after_solver_step_is_recorded_and_scan_continues(tmp_path, mode):
    directory = phase_scan.materialize(tmp_path / 'scan', mode)
    project = engine.Project.load(directory)
    project.structures['alpha'].atom_sites[0].adp_iso.free = True
    completed, failures = [], []

    def fail_middle_iteration(_record):
        if len(completed) == 1 and not failures:
            failures.append('middle solver iteration')
            message = 'Authored failure after the middle solver started'
            raise ValueError(message)

    project.analysis.fit(
        on_iteration=fail_middle_iteration,
        on_scan_start=lambda _record: None,
        on_file_complete=completed.append,
    )
    assert failures == ['middle solver iteration'], (
        'The failure actor must execute during an actual middle-file solver iteration'
    )
    rows = csv_rows(directory / 'analysis/results.csv')
    assert [row['fit_result.success'] for row in rows] == ['True', 'False', 'True'], (
        'A failure after fitting starts must produce a failed row and continue the scan'
    )
    assert len(completed) == 3, (
        'Every completed or failed fitted file must deliver its row to scan consumers'
    )
    expected = engine.Project.load(phase_scan.materialize(tmp_path / 'clean', mode))
    expected.structures['alpha'].atom_sites[0].adp_iso.free = True
    (tmp_path / 'clean/experiments/scan/02.xy').unlink()
    expected.analysis.fit()
    clean = csv_rows(tmp_path / 'clean/analysis/results.csv')
    for key, value in rows[2].items():
        if key.endswith(('.scale', '.adp_iso')):
            assert float(value) == pytest.approx(float(clean[-1][key]), rel=2e-8, abs=2e-8), (
                'The next file must resume from the last successful state or independent template'
            )


@pytest.mark.parametrize('mode', ['sequential', 'independent'])
def test_refusal_before_solver_stops_scan(tmp_path, mode):
    directory = phase_scan.materialize(tmp_path / 'scan', mode)
    bad = directory / 'experiments/scan/02.xy'
    bad.write_text('No measured numeric rows\n')
    completed = []
    with pytest.raises((ValueError, RuntimeError)):
        engine.Project.load(directory).analysis.fit(on_file_complete=completed.append)
    assert len(completed) == 1, (
        'A pre-solver refusal must stop before the next file and emit no failed completion'
    )


@pytest.mark.parametrize('geometry', ['single', 'phase_sum', 'scan'])
def test_fit_from_fitted_start_keeps_dependent_in_range(tmp_path, geometry):
    project = phase_scan.bounded_start(tmp_path / 'start', geometry, engine)
    first = project.analysis.fit()
    assert first.converged, 'The bounded-trial control must begin from a successful fitted state'
    saved = tmp_path / 'fitted'
    project.save_as(saved)
    for path in (saved / 'experiments').glob('*.edi'):
        prefix = path.read_text().split('loop_\n_data.two_theta')[0]
        path.write_text(
            prefix
            + 'loop_\n_data.two_theta\n_data.intensity_meas\n_data.intensity_meas_su\n'
            + ''.join(f'{40 + i} 1 1\n' for i in range(8))
        )
    if geometry == 'scan':
        scan = saved / 'experiments/scan'
        scan.mkdir()
        for name, value in [('01.xy', 4), ('02.xy', 1)]:
            (scan / name).write_text(''.join(f'{40 + i} {value} 1\n' for i in range(8)))
        analysis = saved / 'analysis/analysis.edi'
        analysis.write_text(
            analysis.read_text().replace(
                '_fitting_mode.type single', '_fitting_mode.type sequential'
            )
            + '\n_sequential_fit.data_dir experiments/scan\n_sequential_fit.file_pattern *.xy\n'
        )
    project = engine.Project.load(saved)
    outcome = project.analysis.fit()
    assert outcome.converged, (
        'A constrained fit from a fitted start must shorten or '
        'reject inadmissible trials and finish'
    )
    parent = project.experiments['bank'].background_terms[0].coef.value
    assert parent == pytest.approx(2, abs=2e-6), (
        'The constrained least-squares optimum is the admissible '
        'boundary a=2, not the unconstrained optimum a=1'
    )
    for structure in project.structures:
        dependent = structure.atom_sites[0].adp_iso.value
        assert dependent >= 0, (
            'Every phase dependent must stay in its declared nonnegative displacement range'
        )
    if geometry == 'scan':
        assert all(
            row['fit_result.success'] == 'True' for row in csv_rows(saved / 'analysis/results.csv')
        ), 'Sequential fits must continue successfully from the constrained fitted start'


def test_joint_mode_over_declared_scan_refuses_before_outputs(tmp_path):
    directory = phase_scan.materialize(tmp_path / 'scan', 'joint')
    with pytest.raises((ValueError, RuntimeError), match=r'joint|scan|sequential'):
        engine.Project.load(directory).analysis.fit()
    assert not (directory / 'analysis/results.csv').exists(), (
        'Joint mode over a declared scan must refuse without writing scan results'
    )
