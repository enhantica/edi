"""A real short scan proves optimizer, completion and FileResult observation arrival."""

import csv
from pathlib import Path

import pytest

from tests.fixtures.scan_app.harness import SMALL, Harness, copy_project, files


@pytest.fixture(scope='module')
def boundary_observations(tmp_path_factory):
    root = tmp_path_factory.mktemp('scan-boundary')
    harness = Harness(root / 'host')
    result = {}
    for mode in ['sequential', 'independent']:
        project = copy_project(SMALL, root / mode, mode=mode, iterations=1)
        expected = [path.name for path in files(project)]
        observed = harness.invoke('run', project)
        with (project / 'analysis/results.csv').open() as stream:
            rows = list(csv.DictReader(stream))
        result[mode] = expected, observed, rows
    return result


@pytest.mark.parametrize('mode', ['sequential', 'independent'])
def test_actual_scan_dispatch_reaches_each_native_callback(boundary_observations, mode):
    expected, observed, rows = boundary_observations[mode]
    assert observed['entered'] and observed['ended'], (
        'A real short app scan must enter and finish the production worker'
    )
    assert [Path(row['file_path']).name for row in rows] == expected, (
        'The independent persisted rows prove that every short-scan dataset really completed'
    )
    assert observed['completed'] == len(rows), (
        'Every real completed dataset reaches the completion observer on the called overload'
    )
    assert observed['fileResults'] == len(rows), (
        'Every dataset result reaches FileResult observation on the called production overload'
    )
    assert len(observed['work']) == len(rows), (
        'Optimizer entry observations remain reached after repairing the completion boundary'
    )
