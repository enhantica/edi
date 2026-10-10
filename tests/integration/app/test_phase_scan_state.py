"""Actual app scan/Evolution lifecycle from authored linear inputs and completion invariants."""

import json
import os
import subprocess
from pathlib import Path

import edi
import pytest

from tests.fixtures import phase_scan
from tests.integration.app.test_e04_t1_runtime_escapes import runner

ROOT = Path(__file__).resolve().parents[3]


def observe(root, expected, *, timeout=10):
    (root / 'expected.json').write_text(json.dumps(expected))
    return subprocess.run(
        [str(runner()), '-input', str(ROOT / 'tests/fixtures/phase_scan_app'), '-o', '-,txt'],
        env={
            **os.environ,
            'EDI_ACCEPTANCE_REFERENCE': str(root),
            'QT_QPA_PLATFORM': 'offscreen',
            'QT_QUICK_BACKEND': 'software',
            'OMP_NUM_THREADS': '1',
        },
        capture_output=True,
        text=True,
        timeout=timeout,
        check=False,
    )


@pytest.mark.parametrize('mode', ['sequential', 'independent'])
@pytest.mark.parametrize(
    'skipped', [(), (0,), (1,), (2,), (0, 1, 2), 'resume-leading', 'resume-converted']
)
def test_app_counts_processed_files_and_reopens_all_phase_results(tmp_path, mode, skipped):
    directory = phase_scan.materialize(tmp_path / 'project', mode)
    converted = skipped == 'resume-converted'
    resume = skipped in {'resume-leading', 'resume-converted'}
    skipped = (0,) if resume else skipped
    for index in skipped:
        (directory / f'experiments/scan/{index + 1:02d}.xy').write_text(
            ''.join(f'{x:.17g} 0 1\n' for x in phase_scan.support.grid())
        )
    if resume:
        pending = directory / 'experiments/scan/03.xy'
        parked = tmp_path / 'pending.xy'
        pending.rename(parked)
        edi.Project.load(directory).analysis.fit()
        parked.rename(pending)
        if converted:
            original = phase_scan.materialize(tmp_path / 'signal', mode)
            (directory / 'experiments/scan/01.xy').write_bytes(
                (original / 'experiments/scan/01.xy').read_bytes()
            )
            skipped = ()
    places = [index for index in range(3) if index not in skipped]
    result = observe(
        tmp_path,
        {
            'kind': 'scan',
            'resume': resume,
            'converted': converted,
            'places': places,
            'values': [phase_scan.COEFFICIENTS[index] for index in places],
        },
    )
    assert result.returncode == 0, (
        'The real app must fit every phase, render all successful points, account rowless skips, '
        'disable completed Start/Continue, permit Reset and retain those states on reopen: '
        + result.stdout
        + result.stderr
    )


@pytest.mark.parametrize('count', phase_scan.NOTES_CASES)
def test_app_refuses_malformed_notes_with_one_diagnostic(tmp_path, count):
    directory = phase_scan.materialize(tmp_path / 'project')
    (directory / 'analysis/scan-notes.csv').write_text(phase_scan.malformed_notes(count))
    result = observe(tmp_path, {'kind': 'notes'})
    assert result.returncode == 0, (
        'Malformed persisted counts and torn/duplicate notes must produce one explicit '
        'core/app diagnostic and prevent misleading recovered completion: '
        + result.stdout
        + result.stderr
    )


@pytest.mark.parametrize('kind', ['directory', 'fifo'])
def test_app_refuses_nonregular_notes_before_opening_a_stream(tmp_path, kind):
    if kind == 'fifo' and not hasattr(os, 'mkfifo'):
        pytest.skip('The platform cannot construct the optional FIFO file-kind witness')
    directory = phase_scan.materialize(tmp_path / 'project')
    notes = phase_scan.nonregular_notes(directory, kind)
    before = notes.lstat().st_ino, notes.lstat().st_mode
    try:
        result = observe(tmp_path, {'kind': 'notes'}, timeout=0.8)
    except subprocess.TimeoutExpired:
        pytest.fail('The core/app must refuse unsupported notes before opening a blocking FIFO')
    assert result.returncode == 0, (
        'The actual app must report existing unsupported notes paths as one explicit refusal: '
        + result.stdout
        + result.stderr
    )
    assert (notes.lstat().st_ino, notes.lstat().st_mode) == before, (
        'The app refusal must preserve the retained non-regular source state'
    )
