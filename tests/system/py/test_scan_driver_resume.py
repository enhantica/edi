"""Driver reuse invariants; front-end consistency is not a physics claim."""

from __future__ import annotations

import csv
import importlib
import shutil
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
FIXTURE = ROOT / 'tests/fixtures/scan_template/project'
EXPECTED = ['all594687.dat', 'all594791.dat', 'all594842.dat']


def rows(project_dir):
    with (project_dir / 'analysis/results.csv').open(newline='') as stream:
        return list(csv.DictReader(stream))


def reduced_input(destination, mode):
    shutil.copytree(FIXTURE, destination)
    analysis = destination / 'analysis/analysis.edi'
    text = (
        analysis
        .read_text()
        .replace('_minimizer.max_iterations 1000', '_minimizer.max_iterations 1')
        .replace('_fitting_mode.type sequential', '_fitting_mode.type ' + mode)
    )
    analysis.write_text(text)
    return destination


def run_scan(mode, root):
    edi = importlib.import_module('edi')
    project_dir = reduced_input(root / mode, mode)
    project = edi.Project.load(project_dir)
    completed = []
    observed = []

    def on_file_complete(row):
        completed.append(row)
        observed.append(rows(project_dir))

    first = project.analysis.fit(
        on_file_complete=on_file_complete, should_cancel=lambda: len(completed) >= 1
    )
    partial = rows(project_dir)
    partial_bytes = (project_dir / 'analysis/results.csv').read_bytes()
    resumed = edi.Project.load(project_dir)
    second = resumed.analysis.fit(on_file_complete=on_file_complete)
    complete = rows(project_dir)
    (project_dir / 'analysis/results.csv').write_bytes(partial_bytes)
    direct = edi.Project.load(project_dir)
    getattr(direct, 'fit_' + mode)()
    return first, second, completed, observed, partial, complete, rows(project_dir)


@pytest.fixture(scope='module')
def scan_transcript(tmp_path_factory):
    root = tmp_path_factory.mktemp('scan-resume')
    return [run_scan(mode, root) for mode in ('sequential', 'independent')]


def test_stop_retains_committed_rows_and_continue_visits_only_remaining_files(scan_transcript):
    for _, _, notifications, _, partial, complete, _ in scan_transcript:
        assert len(partial) == 1, (
            'Stop and continue: stop after one file retains exactly one CSV row'
        )
        assert [Path(row['file_path']).name for row in complete] == EXPECTED, (
            'Stop and continue: completion follows scan order without a duplicate row'
        )
        assert len(notifications) == len(EXPECTED), (
            'Stop and continue: resumed work publishes only the remaining files'
        )
        assert complete[0] == partial[0], (
            'Stop and continue: the first committed row is not refitted'
        )


def test_callback_runs_after_each_result_is_committed(scan_transcript):
    for _, _, _, observations, _, _, _ in scan_transcript:
        assert [len(observed) for observed in observations] == [1, 2, 3], (
            'Scan progress: each callback arrives after its new row is visible in results.csv'
        )


def test_resumed_facade_csv_is_cell_identical_to_native_driver_consistency(scan_transcript):
    for _, _, _, _, _, actual, expected in scan_transcript:
        assert actual == expected, (
            'Scan consistency: the facade and native driver resume to the same CSV cells'
        )
