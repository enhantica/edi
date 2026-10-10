"""Public progress and the visible bar share the independently defined processed population."""

import json
import os
import subprocess

import edi
import pytest

from tests.fixtures import phase_scan
from tests.integration.app.test_e04_t1_runtime_escapes import ROOT, runner


def observe(root, channel, **expected):
    (root / 'expected.json').write_text(json.dumps({'channel': channel, **expected}))
    return subprocess.run(
        [str(runner()), '-input', str(ROOT / 'tests/fixtures/phase_scan_progress'), '-o', '-,txt'],
        env={
            **os.environ,
            'EDI_ACCEPTANCE_REFERENCE': str(root),
            'QT_QPA_PLATFORM': 'offscreen',
            'QT_QUICK_BACKEND': 'software',
            'OMP_NUM_THREADS': '1',
        },
        capture_output=True,
        text=True,
        timeout=10,
        check=False,
    )


@pytest.mark.parametrize('mode', ['sequential', 'independent'])
@pytest.mark.parametrize('skipped', [(), (0,), (1,), (2,), (0, 1, 2)])
@pytest.mark.parametrize('channel', ['public', 'status-bar'])
def test_app_processed_progress_finishes_with_rowless_skips(tmp_path, mode, skipped, channel):
    directory = phase_scan.materialize(tmp_path / 'project', mode)
    for index in skipped:
        (directory / f'experiments/scan/{index + 1:02d}.xy').write_text(
            ''.join(f'{x:.17g} 0 1\n' for x in phase_scan.support.grid())
        )
    result = observe(tmp_path, channel)
    assert result.returncode == 0, (
        'Public and visible app progress must each reach completion with fitted '
        'plus skipped files: ' + result.stdout + result.stderr
    )


@pytest.mark.parametrize('mode', ['sequential', 'independent'])
def test_app_converted_skip_live_population_matches_reopen(tmp_path, mode):
    directory = phase_scan.materialize(tmp_path / 'project', mode)
    skipped = directory / 'experiments/scan/01.xy'
    signal = skipped.read_bytes()
    skipped.write_text(''.join(f'{x:.17g} 0 1\n' for x in phase_scan.support.grid()))
    pending = directory / 'experiments/scan/03.xy'
    parked = tmp_path / 'pending.xy'
    pending.rename(parked)
    edi.Project.load(directory).analysis.fit()
    pending.write_bytes(parked.read_bytes())
    skipped.write_bytes(signal)
    result = observe(tmp_path, 'population')
    assert result.returncode == 0, (
        'Converting a rowless skip to a fitted dataset must update live fitted-plus-skipped '
        'populations once, without exceeding the total, and agree with reopened counts: '
        + result.stdout
        + result.stderr
    )


@pytest.mark.parametrize('mode', ['sequential', 'independent'])
@pytest.mark.parametrize('ending', ['cancel', 'failure'])
def test_app_partial_end_preserves_its_real_outcome(tmp_path, mode, ending):
    directory = phase_scan.materialize(tmp_path / 'project', mode)
    if ending == 'failure':
        (directory / 'experiments/scan/02.xy').write_text('No measured numeric rows\n')
    result = observe(tmp_path, 'ending', ending=ending)
    assert result.returncode == 0, (
        'Cancellation and pre-step failure must keep their actual outcome and partial population '
        'instead of publishing invented scan completion: ' + result.stdout + result.stderr
    )


@pytest.mark.parametrize('mode', ['sequential', 'independent'])
@pytest.mark.parametrize('case', ['fraction', 'foreign'])
@pytest.mark.parametrize('channel', ['index', 'publication'])
def test_app_incremental_notes_failure_invalidates_before_progress(tmp_path, mode, case, channel):
    directory = phase_scan.materialize(tmp_path / 'project', mode)
    held = []
    for name in ('02.xy', '03.xy'):
        path = directory / ('experiments/scan/' + name)
        data = path.read_bytes()
        path.unlink()
        held.append((path, data))
    edi.Project.load(directory).analysis.fit()
    for path, data in held:
        path.write_bytes(data)
    (directory / 'analysis/scan-notes.csv').write_text(
        'file_path,negative_points,skipped_dataset,refusal\nexperiments/scan/01.xy,0,False,\n'
    )
    result = observe(tmp_path, 'incremental', fault=case, check=channel)
    assert result.returncode == 0, (
        'A notes failure after accepted initial history and an earlier complete later line must '
        'invalidate the live app index, report it and publish no partial recovery: '
        + result.stdout
        + result.stderr
    )


@pytest.mark.parametrize('mode', ['sequential', 'independent'])
@pytest.mark.parametrize('converted', [False, True])
@pytest.mark.parametrize('following', [False, True])
def test_app_incremental_refusal_blocks_later_callbacks_and_settlement(
    tmp_path, mode, converted, following
):
    directory = phase_scan.materialize(tmp_path / 'project', mode)
    scan = directory / 'experiments/scan'
    for name, source in [('04.xy', '01.xy'), ('05.xy', '02.xy')]:
        (scan / name).write_bytes((scan / source).read_bytes())
    signal = (scan / '03.xy').read_bytes()
    if converted:
        (scan / '03.xy').write_text(''.join(f'{x:.17g} 0 1\n' for x in phase_scan.support.grid()))
    held = []
    for name in ('02.xy', '04.xy', '05.xy') + (() if converted else ('03.xy',)):
        path = scan / name
        held.append((path, path.read_bytes()))
        path.unlink()
    edi.Project.load(directory).analysis.fit()
    for path, data in held:
        path.write_bytes(data)
    (scan / '03.xy').write_bytes(signal)
    (directory / 'analysis/scan-notes.csv').write_text(
        'file_path,negative_points,skipped_dataset,refusal\nexperiments/scan/01.xy,0,False,\n'
        + ('experiments/scan/03.xy,0,True,\n' if converted else '')
    )
    result = observe(tmp_path, 'incremental', fault='fraction', sweep=True, following=following)
    assert result.returncode == 0, (
        'Refused history must block later and terminal progress, including Follow and skips: '
        + result.stdout
        + result.stderr
    )
