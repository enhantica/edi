"""Changing auto estimates must not invalidate scan bookkeeping or template rows."""

import csv
import json
import os
import subprocess
import sys
from pathlib import Path

import edi as engine
import pytest

from tests.conftest import corpus_case_dir
from tests.fixtures.background_estimate.lifecycle import persisted_points, scan_input

ROOT = Path(__file__).resolve().parents[3]
SOURCE = corpus_case_dir('lbco-hrpt-s2') / 'project'


@pytest.mark.parametrize('mode', ['independent', 'sequential'])
@pytest.mark.parametrize('fail_first', [False, True], ids=['success', 'failed-predecessor'])
def test_auto_scan_preserves_rows_and_resumes_with_different_measured_files(
    tmp_path, mode, fail_first
):
    counts = scan_input(tmp_path / 'input', SOURCE, engine, mode)
    assert len(set(counts)) > 1, (
        'The scan witness must use genuinely different measurements '
        'requiring different anchor counts'
    )
    completed = subprocess.run(
        [
            sys.executable,
            '-m',
            'tests.fixtures.background_estimate.lifecycle',
            'edi',
            str(tmp_path / 'input'),
            'scan',
            'true' if fail_first else 'false',
        ],
        capture_output=True,
        text=True,
        timeout=4,
        check=False,
        env={**os.environ, 'OMP_NUM_THREADS': '1', 'OPENBLAS_NUM_THREADS': '1'},
    )
    assert completed.returncode == 0, (
        'Changing automatic points must not crash a scan or use replaced native rows: '
        + completed.stderr
    )
    result = json.loads(completed.stdout.splitlines()[-1])
    assert 'error' not in result, (
        'Auto scan bookkeeping must tolerate changed anchor counts and a failed predecessor: '
        + str(result)
    )
    assert len(result['files']) == 3, 'Every authored measured file must complete exactly once'
    assert result['points'] == result['original'], (
        'Every file must use the frozen template points specified by the scan ADR'
    )
    assert result['identity'], (
        'Scan fitting must preserve the identity and layout of template point rows'
    )
    assert result['mode'] == 'auto', (
        'Scan write-back must not turn estimated points into manual edits'
    )
    if fail_first:
        assert result['injected'], (
            'The failure/restart scan must actually execute its failed predecessor'
        )
        assert result['first_failed'], (
            'The authored failed predecessor must remain a failed persisted row'
        )
    assert result['resume_unchanged'], (
        'A completed auto scan must resume without changing result bytes'
    )
    assert result['completed_before_restart'] == 3, 'A completed resume must not repeat callbacks'
    assert result['completed_after_restart'] == 4, (
        'Restart must fit only the missing terminal file'
    )


@pytest.mark.parametrize('mode', ['independent', 'sequential'])
def test_cli_scan_uses_one_template_and_resumes_without_rewriting_finished_rows(tmp_path, mode):
    source = tmp_path / 'input'
    counts = scan_input(source, SOURCE, engine, mode)
    assert len(set(counts)) > 1, (
        'The CLI scan must exercise files with different separately estimated anchor counts'
    )
    original = persisted_points(source, experiment='hrpt')
    command = [sys.executable, '-m', 'edi', 'fit', str(source), '--verbosity', 'off']
    result = subprocess.run(command, capture_output=True, text=True, timeout=3, check=False)
    assert result.returncode == 0, (
        'Both public CLI scan modes must complete without using replaced automatic rows: '
        + result.stdout
        + result.stderr
    )
    csv_path = source / 'analysis/results.csv'
    initial = csv_path.read_bytes()
    with csv_path.open() as stream:
        rows = list(csv.DictReader(stream))
    assert len(rows) == 3, 'The CLI must retain one result per distinct measured file'
    assert persisted_points(source, experiment='hrpt') == original, (
        'A CLI scan must retain the one frozen template estimate instead of last-file points'
    )
    result = subprocess.run(command, capture_output=True, text=True, timeout=1, check=False)
    assert result.returncode == 0, 'A completed CLI auto scan must resume successfully'
    assert csv_path.read_bytes() == initial, (
        'Completed auto-scan resume must preserve every persisted result byte'
    )
