"""Public progress and the visible bar share the independently defined processed population."""

import json
import os
import subprocess

import edi
import pytest

from tests.fixtures import phase_scan
from tests.integration.app.test_e04_t1_runtime_escapes import ROOT, runner


def observe(root, channel):
    (root / 'expected.json').write_text(json.dumps({'channel': channel}))
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
