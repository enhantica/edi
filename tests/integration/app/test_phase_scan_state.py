"""Actual app scan/Evolution lifecycle from authored linear inputs and completion invariants."""

import json
import os
import shutil
import subprocess
from pathlib import Path

import edi
import pytest

from tests.fixtures import phase_scan
from tests.integration.app.test_e04_t1_runtime_escapes import runner
from tests.integration.py.test_scan_notes_resume import complete_results_history as history_fixture

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


@pytest.fixture(scope='module')
def complete_results_history(tmp_path_factory):
    return history_fixture.__wrapped__(tmp_path_factory)


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


@pytest.mark.parametrize('mode', ['sequential', 'independent'])
@pytest.mark.parametrize('latest', ['scan', 'single'])
def test_app_rowless_history_selects_the_latest_run_after_reopen(tmp_path, mode, latest):
    directory = phase_scan.materialize(tmp_path / 'project', mode)
    signal = (directory / 'experiments/scan/01.xy').read_bytes()
    for path in (directory / 'experiments/scan').glob('*.xy'):
        path.write_text(''.join(f'{x:.17g} 0 1\n' for x in phase_scan.support.grid()))
    edi.Project.load(directory).analysis.fit()
    assert edi.Project.load(directory)._scan_notes()['skipped'] == 3, (
        'The witness must retain all-skipped history without fitted rows'
    )
    if latest == 'single':
        (directory / 'experiments/scan/01.xy').write_bytes(signal)
    result = observe(
        tmp_path, {'kind': 'single-after-skips' if latest == 'single' else 'retained-scan'}
    )
    assert result.returncode == 0, (
        'Rowless history must round-trip and retain a later single fit as latest: '
        + result.stdout
        + result.stderr
    )


@pytest.mark.parametrize('filename', ['results.csv', 'results-provenance.csv'])
@pytest.mark.parametrize('kind', ['directory', 'fifo', 'absent', 'symlink'])
def test_app_results_state_open_distinguishes_supported_paths(
    tmp_path, complete_results_history, filename, kind
):
    if kind == 'fifo' and not hasattr(os, 'mkfifo'):
        pytest.skip('The platform cannot construct the optional FIFO file-kind witness')
    directory = tmp_path / 'project'
    if kind == 'absent' and filename == 'results.csv':
        phase_scan.materialize(directory)
    else:
        shutil.copytree(complete_results_history['sequential'], directory)
    phase_scan.scan_state_path(directory, filename, kind)
    before = phase_scan.scan_state_fingerprint(directory)
    try:
        result = observe(
            tmp_path,
            {'kind': 'state-open', 'filename': filename, 'valid': kind in {'absent', 'symlink'}},
            timeout=2,
        )
    except subprocess.TimeoutExpired:
        pytest.fail('App open must reject unsupported results/provenance before FIFO blocking')
    assert result.returncode == 0, (
        'App open must distinguish supported and unsupported results state: '
        + result.stdout
        + result.stderr
    )
    assert phase_scan.scan_state_fingerprint(directory) == before, (
        'App state-kind admission must retain every original analysis entry'
    )


@pytest.mark.parametrize('reader', ['offset', 'row', 'evolution'])
@pytest.mark.parametrize('kind', ['directory', 'fifo', 'symlink'])
def test_app_post_index_results_reread_checks_the_new_path_kind(
    tmp_path, complete_results_history, reader, kind
):
    if kind == 'fifo' and not hasattr(os, 'mkfifo'):
        pytest.skip('The platform cannot construct the optional FIFO file-kind witness')
    directory = tmp_path / 'project'
    shutil.copytree(complete_results_history['sequential'], directory)
    replacement = tmp_path / 'replacement'
    if kind == 'directory':
        replacement.mkdir()
        (replacement / 'keep').write_text('retained replacement\n')
    elif kind == 'fifo':
        os.mkfifo(replacement)
    else:
        replacement.symlink_to(directory / 'analysis/results.csv.retained')
    inode = replacement.lstat().st_ino
    try:
        result = observe(
            tmp_path, {'kind': 'reread', 'reader': reader, 'valid': kind == 'symlink'}, timeout=2
        )
    except subprocess.TimeoutExpired:
        pytest.fail('Post-index readers must reject a replaced FIFO before a blocking open')
    assert result.returncode == 0, (
        'Offset, dataset and Evolution rereads must prove the new path kind: '
        + result.stdout
        + result.stderr
    )
    assert (directory / 'analysis/results.csv').lstat().st_ino == inode, (
        'A post-index refusal must preserve the authored replacement path'
    )
