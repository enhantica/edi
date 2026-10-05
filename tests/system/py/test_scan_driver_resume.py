"""Observe scan work, event identity and facade/native CSV consistency."""

from __future__ import annotations

import copy
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
    analysis.write_text(
        analysis
        .read_text()
        .replace('_minimizer.max_iterations 1000', '_minimizer.max_iterations 1')
        .replace('_fitting_mode.type sequential', '_fitting_mode.type ' + mode)
    )
    return destination


def event_cells(record):
    return (record.file_name, record.converged, record.reduced_chi_square, record.iterations)


def row_cells(row):
    return (
        Path(row['file_path']).name,
        row['fit_result.success'] == 'True',
        float(row['fit_result.reduced_chi_square']),
        int(row['fit_result.iterations']),
    )


def assert_resume_work(work, complete):
    expected = sum(int(row['fit_result.iterations']) for row in complete[1:])
    assert expected > 0, 'Stop and continue: the fixture must exercise optimizer work'
    assert len(work) == expected, (
        'Stop and continue: only unfinished datasets may spend optimizer iterations'
    )


def assert_events(events, observations):
    assert len(events) == len(observations), (
        'Scan progress: each event has one committed-row observation'
    )
    for event, committed in zip(events, observations, strict=True):
        assert event == row_cells(committed[-1]), (
            'Scan progress: each event identifies its newly committed file and fit values'
        )


def duplicate_work(edi, directory):
    extra = []
    duplicate = edi.Project.load(directory)
    source_rows = []
    for line in (directory / 'experiments/d20_scan' / EXPECTED[0]).read_text().splitlines():
        try:
            values = tuple(map(float, line.split()))
        except ValueError:
            continue
        if len(values) == 3:
            source_rows.append(values)
    duplicate.experiments[0].data = edi.PdCwlData(
        two_theta=[r[0] for r in source_rows],
        intensity_meas=[r[1] for r in source_rows],
        intensity_meas_su=[r[2] for r in source_rows],
    )
    assert list(duplicate.experiments[0].data.two_theta) == [r[0] for r in source_rows], (
        'Stop and continue: redundant work must reach the already completed first dataset'
    )
    duplicate.fitting_mode = 'single'
    duplicate.analysis.fit(on_iteration=extra.append)
    return extra


def run_scan(mode, root):
    edi = importlib.import_module('edi')
    directory = reduced_input(root / mode, mode)
    project = edi.Project.load(directory)
    events, observations = [], []

    def complete(record):
        events.append(event_cells(record))
        observations.append(rows(directory))

    first = project.analysis.fit(on_file_complete=complete, should_cancel=lambda: len(events) >= 1)
    partial = rows(directory)
    partial_bytes = (directory / 'analysis/results.csv').read_bytes()
    resumed = edi.Project.load(directory)
    work = []
    second = resumed.analysis.fit(
        on_scan_start=lambda _preamble: None, on_iteration=work.append, on_file_complete=complete
    )
    finished = rows(directory)
    extra = duplicate_work(edi, directory)
    (directory / 'analysis/results.csv').write_bytes(partial_bytes)
    direct = edi.Project.load(directory)
    getattr(direct, 'fit_' + mode)()
    return {
        'directory': directory,
        'first': first,
        'second': second,
        'events': events,
        'observations': observations,
        'partial': partial,
        'complete': finished,
        'direct': rows(directory),
        'work': work,
        'extra': extra,
    }


@pytest.fixture(scope='module')
def scan_transcript(tmp_path_factory):
    root = tmp_path_factory.mktemp('scan-resume')
    return [run_scan(mode, root) for mode in ('sequential', 'independent')]


def test_stop_retains_committed_rows_and_continue_visits_only_remaining_files(scan_transcript):
    for transcript in scan_transcript:
        assert len(transcript['partial']) == 1, (
            'Stop and continue: stopping retains exactly the first row'
        )
        assert [Path(row['file_path']).name for row in transcript['complete']] == EXPECTED, (
            'Stop and continue: completion follows scan order without duplicate rows'
        )
        assert transcript['complete'][0] == transcript['partial'][0], (
            'Stop and continue: the previously committed row remains unchanged'
        )
        assert len(transcript['events']) == 3, (
            'Stop and continue: each dataset emits one completion event'
        )
        assert_resume_work(transcript['work'], transcript['complete'])
        assert transcript['first'].status == importlib.import_module('edi').FitStatus.CANCELLED, (
            'Stop and continue: the stopped scan returns a cancelled result'
        )
        assert transcript['second'].status != importlib.import_module('edi').FitStatus.CANCELLED, (
            'Stop and continue: a completed scan is not stopped'
        )


def test_callback_runs_after_each_result_is_committed(scan_transcript):
    for transcript in scan_transcript:
        assert [len(value) for value in transcript['observations']] == [1, 2, 3], (
            'Scan progress: each callback follows its committed row'
        )
        assert_events(transcript['events'], transcript['observations'])


def test_resume_gate_rejects_real_duplicate_work_with_unchanged_csv_and_events(scan_transcript):
    for transcript in scan_transcript:
        assert transcript['extra'], (
            'Stop and continue: the duplicate-fit escape must perform optimizer work'
        )
        with pytest.raises(AssertionError, match='unfinished datasets'):
            assert_resume_work(transcript['work'] + transcript['extra'], transcript['complete'])


def test_event_gate_rejects_wrong_file_and_wrong_value_with_correct_callback_count(
    scan_transcript,
):
    for transcript in scan_transcript:
        for field, replacement in [(0, 'wrong.dat'), (2, -17.5)]:
            events = copy.deepcopy(transcript['events'])
            changed = list(events[-1])
            changed[field] = replacement
            events[-1] = tuple(changed)
            with pytest.raises(AssertionError, match='newly committed'):
                assert_events(events, transcript['observations'])


def test_resumed_facade_csv_is_cell_identical_to_native_driver_consistency(scan_transcript):
    for transcript in scan_transcript:
        assert transcript['complete'] == transcript['direct'], (
            'Scan consistency: the facade and native driver resume to the same CSV cells'
        )


def test_save_as_retains_scan_results_and_preserves_the_source_copy(scan_transcript, tmp_path):
    edi = importlib.import_module('edi')
    for index, transcript in enumerate(scan_transcript):
        source = transcript['directory']
        before = (source / 'analysis/results.csv').read_bytes()
        project = edi.Project.load(source)
        destination = tmp_path / str(index)
        project.save_as(destination)
        assert (destination / 'analysis/results.csv').read_bytes() == before, (
            'Save As: the working copy retains every scan result byte in the saved project'
        )
        assert (source / 'analysis/results.csv').read_bytes() == before, (
            'Save As: retaining the working results cannot mutate the source project'
        )
        assert rows(destination) == transcript['complete'], (
            'Save As: saved scan rows still identify the same files and fitted values'
        )
