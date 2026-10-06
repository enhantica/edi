"""Observe scan work, event identity and facade/native CSV consistency."""

from __future__ import annotations

import copy
import csv
import importlib
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from tests.conftest import crysta_reference_prefix, crysta_reference_source

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


def input_columns(file):
    # Independent ASCII convention: scan_template/REFERENCE.md.
    points = []
    for line in file.read_text().splitlines():
        try:
            point = tuple(map(float, line.split()))
        except ValueError:
            continue
        if len(point) == 3:
            points.append((round(point[0], 4), point[1], 1.0 if point[2] < 0.0001 else point[2]))
    return [list(column) for column in zip(*points, strict=True)]


def assert_resume_work(work):
    expected = [input_columns(FIXTURE / 'experiments/d20_scan' / name) for name in EXPECTED[1:]]
    assert work == expected, (
        'Stop and continue: only unfinished datasets enter the optimizer, '
        'with their full measured columns'
    )


@pytest.fixture(scope='module')
def native_resume(tmp_path_factory):
    root = tmp_path_factory.mktemp('native-resume')
    prefix = crysta_reference_prefix()
    source = crysta_reference_source()
    native = (source / 'src/core/sequential.cpp').read_text()
    call = 'last_result = fit_project(working, on_iteration, should_cancel);'
    assert native.count(call) == 1, (
        'Stop and continue: the observer must intercept the real scan optimizer boundary once'
    )
    # A silent redundant fit inside continuation: no subscriber and no CSV append.
    injection = (
        'if (observing && escape_enabled && index == existing.size() && '
        '!existing.empty()) {\n            Project duplicate(working);\n    '
        '        duplicate.experiment().data = read_scan_data(scan_dir / '
        'file_names.front());\n            fit_project(duplicate, {}, '
        '{});\n        }\n        ' + call
    )
    (root / 'observed_sequential.cpp').write_text(native.replace(call, injection))
    artifact = Path(sys.modules['edi._edi'].__file__).resolve().parents[2]
    executable = root / 'resume'
    compiler = os.environ.get('CXX', 'c++')
    command = [
        compiler,
        '-std=c++20',
        '-O0',
        '-I' + str(ROOT / 'core/include'),
        '-I' + str(Path(sys.prefix) / 'include'),
        '-I' + str(Path(sys.prefix) / 'include/eigen3'),
        '-I' + str(prefix / 'include'),
        '-I' + str(source / 'src'),
        '-I' + str(root),
        str(ROOT / 'tests/fixtures/scan_template/work_probe.cpp'),
        str(artifact / 'core/libedi_core.a'),
        str(prefix / 'lib/libcrysta_core.a'),
        '-lsleef',
        '-lpthread',
        '-o',
        str(executable),
    ]
    if sys.platform != 'darwin':
        command.insert(-2, '-fopenmp')
    result = subprocess.run(command, capture_output=True, text=True, check=False, timeout=60)
    assert result.returncode == 0, (
        'Stop and continue: the real native scan observer must compile '
        'against the linked headers and source: ' + result.stderr
    )
    observations = []
    for mode in ('sequential', 'independent'):
        transcripts = []
        for variant in ('normal', 'duplicate'):
            directory = reduced_input(root / (mode + '-' + variant), mode)
            log = root / (mode + '-' + variant + '.jsonl')
            result = subprocess.run(
                [str(executable), str(directory), str(log), variant],
                capture_output=True,
                text=True,
                check=False,
                timeout=30,
            )
            assert result.returncode == 0, (
                'Stop and continue: the actual native continuation must run: ' + result.stderr
            )
            transcripts.append({
                'work': [json.loads(line) for line in log.read_text().splitlines()],
                'rows': rows(directory),
                'result': result.stdout.strip(),
            })
        observations.append(transcripts)
    return observations


def assert_events(events, observations):
    assert len(events) == len(observations), (
        'Scan progress: each event has one committed-row observation'
    )
    for event, committed in zip(events, observations, strict=True):
        assert event == row_cells(committed[-1]), (
            'Scan progress: each event identifies its newly committed file and fit values'
        )


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
    }


@pytest.fixture(scope='module')
def scan_transcript(tmp_path_factory):
    root = tmp_path_factory.mktemp('scan-resume')
    return [run_scan(mode, root) for mode in ('sequential', 'independent')]


def test_stop_retains_committed_rows_and_continue_visits_only_remaining_files(
    scan_transcript, native_resume
):
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
        assert transcript['first'].status == importlib.import_module('edi').FitStatus.CANCELLED, (
            'Stop and continue: the stopped scan returns a cancelled result'
        )
        assert transcript['second'].status == importlib.import_module('edi').FitStatus.MAX_ITER, (
            'Stop and continue: the one-iteration scan reports its final '
            'maximum-iterations outcome'
        )

    for normal, _escape in native_resume:
        assert_resume_work(normal['work'])


def test_callback_runs_after_each_result_is_committed(scan_transcript, native_resume):
    for normal, _escape in native_resume:
        assert normal['result'].split()[-1] == '2', (
            'Scan progress: native continuation publishes only unfinished dataset events'
        )
    for transcript in scan_transcript:
        assert [len(value) for value in transcript['observations']] == [1, 2, 3], (
            'Scan progress: each callback follows its committed row'
        )
        assert_events(transcript['events'], transcript['observations'])


def test_resume_gate_rejects_real_duplicate_work_with_unchanged_csv_and_events(native_resume):
    for normal, escape in native_resume:
        assert normal['result'] == escape['result'], (
            'Stop and continue: silent duplicate work preserves continuation '
            'status and event counts'
        )

        def normalized(rows):
            return [{**row, 'file_path': Path(row['file_path']).name} for row in rows]

        assert normalized(normal['rows']) == normalized(escape['rows']), (
            'Stop and continue: the redundant optimizer invocation retains every CSV cell'
        )
        assert len(escape['work']) == len(normal['work']) + 1, (
            'Stop and continue: the escape reaches the real completed dataset '
            'inside continuation without notifications'
        )
        with pytest.raises(AssertionError, match='unfinished datasets'):
            assert_resume_work(escape['work'])


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


def test_resumed_facade_csv_is_cell_identical_to_native_driver_consistency(
    scan_transcript, native_resume
):
    for transcript in scan_transcript:
        assert transcript['complete'] == transcript['direct'], (
            'Scan consistency: the facade and native driver resume to the same CSV cells'
        )

    for transcript, (normal, _escape) in zip(scan_transcript, native_resume, strict=True):

        def normalized(values):
            return [{**row, 'file_path': Path(row['file_path']).name} for row in values]

        assert normalized(transcript['complete']) == normalized(normal['rows']), (
            'Scan consistency: the facade and independently instrumented '
            'native continuation retain identical fitted rows'
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
