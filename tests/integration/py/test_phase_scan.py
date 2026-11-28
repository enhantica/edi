"""Scan equivalence, linear scale recovery and unchanged-data persistence."""

import csv
import warnings

import edi as engine
import pytest

from tests.fixtures import phase_scan
from tests.fixtures.multiphase import support


def csv_rows(path):
    with path.open(newline='') as stream:
        return list(csv.DictReader(stream))


def scales(project):
    return [support.links(project.experiments[0])[name].scale.value for name in ('alpha', 'beta')]


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
def test_fit_from_fitted_start_keeps_dependent_in_range(tmp_path, geometry, capfd):
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
    capfd.readouterr()
    with warnings.catch_warnings(record=True) as notices:
        warnings.simplefilter('always')
        outcome = project.analysis.fit()
    diagnostics = capfd.readouterr().err + '\n'.join(str(item.message) for item in notices)
    assert outcome.converged, (
        'A constrained fit from a fitted start must keep finite out-of-range dependents and finish'
    )
    assert 'crysta.domain.constraint_range' in diagnostics, (
        'A finite dependent outside its range must emit the stable range-warning code'
    )
    parent = project.experiments['bank'].background_terms[0].coef.value
    assert parent == pytest.approx(1, abs=2e-6), (
        'Constant observations of one have optimum a=1 even when its dependent leaves its range'
    )
    for name in ('phase',) if geometry == 'single' else ('phase', 'other'):
        dependent = project.structures[name].atom_sites[0].adp_iso.value
        expected = parent - 2 if name == 'phase' else 2 * parent - 4
        assert dependent == pytest.approx(expected, abs=2e-6) and dependent < 0, (
            'Every phase must keep the finite negative value prescribed by its relation'
        )
    if geometry == 'scan':
        assert all(
            row['fit_result.success'] == 'True' for row in csv_rows(saved / 'analysis/results.csv')
        ), 'Sequential fits must continue successfully from the constrained fitted start'


def test_joint_mode_over_declared_scan_writes_every_point(tmp_path):
    directory = phase_scan.materialize(tmp_path / 'scan', 'joint')
    engine.Project.load(directory).analysis.fit()
    inputs = sorted(path.name for path in (directory / 'experiments/scan').glob('*.xy'))
    rows = (directory / 'analysis/results.csv').read_text().splitlines()
    published = csv.DictReader(line for line in rows if not line.startswith('#'))
    assert [row['file_path'].rsplit('/', 1)[-1] for row in published] == inputs, (
        'Joint mode over a declared scan publishes one row per measured pattern'
    )
