"""Real scan, single-fit parity and reopen workflow; retains the PR core cadence."""

from pathlib import Path

import edi as engine
import numpy as np
import pytest

from tests.fixtures import phase_scan
from tests.integration.py.test_phase_scan import csv_rows, scales


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
        point_descent = 'fast_descent' if mode == 'sequential' else 'auto'
        control.analysis.descent = point_descent
        outcome = control.analysis.fit()
        assert row['fit_result.descent'] == point_descent, (
            'Auto sequential points execute fast descent while independent points retain Auto'
        )
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
            'Identical effective descent, starts and stop rules preserve exact iteration parity'
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
