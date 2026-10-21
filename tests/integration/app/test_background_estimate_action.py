"""Compare the Main-tab Estimate action receipts with the same live Python call."""

import json
import os
import re
import subprocess
from pathlib import Path

import edi
import pytest

from tests.fixtures.stored_loop_ids.historical_bytes import loop_ids

ROOT = Path(__file__).resolve().parents[3]


@pytest.fixture(scope='module')
def app_estimates():
    runner = Path(os.environ.get('EDI_APP_TEST_RUNNER', ROOT / 'build/app/app/edi_app_tests'))
    assert runner.is_file(), (
        'The production app test host must be built before app acceptance runs'
    )
    run = subprocess.run(
        [
            str(runner),
            '-input',
            str(ROOT / 'tests/unit/app/tst_background_estimate.qml'),
            '-o',
            '-,txt',
        ],
        env={**os.environ, 'QT_QPA_PLATFORM': 'offscreen', 'QT_QUICK_BACKEND': 'software'},
        capture_output=True,
        text=True,
        timeout=25,
        check=False,
    )
    output = run.stdout + run.stderr
    receipts = [
        json.loads(line)
        for line in re.findall(r'BACKGROUND_ESTIMATE_RECEIPT (\{[^\n]+\})', output)
    ]
    return run.returncode, output, receipts


@pytest.mark.parametrize('case', ['hrpt', 'sim_si'])
def test_app_estimate_equals_python_after_undo_and_exact_reload(app_estimates, case, tmp_path):
    status, output, receipts = app_estimates
    assert status == 0, (
        'The Main-tab control labelled Estimate must support estimation, undo and exact '
        'reload in the real Qt host:\n' + output
    )
    assert f'test_estimate_undo_and_exact_reload({case})' in output, (
        'The real app must execute the named corpus case'
    )
    matches = [receipt for receipt in receipts if receipt['case'] == case]
    assert len(matches) == 1, 'Each app case must produce exactly one completed action receipt'
    project = edi.Project.load(ROOT / 'tests/fixtures/background_estimate/projects' / case)
    background = project.experiment.background
    assert callable(getattr(background, 'auto_estimate', None)), (
        'The app comparison must execute the live Python estimation API'
    )
    background.auto_estimate(tolerance=2.0, in_peaks='drop', use_model=False)
    destination = tmp_path / 'python-estimate'
    project.save_as(destination)
    identifiers = [
        identity.decode()
        for _, _, identity in loop_ids(
            (destination / 'experiments/bank.edi').read_bytes(), b'_background'
        )
    ]
    assert len(identifiers) == len(background), (
        'The Python estimate must serialize exactly one stored identity per background point'
    )
    expected = [
        {
            'id': identity,
            'position': getattr(p.position, 'value', p.position),
            'intensity': p.intensity.value,
            'free': p.intensity.free,
        }
        for identity, p in zip(identifiers, background, strict=True)
    ]
    assert matches[0]['points'] == expected, (
        'The Background action and saved/reloaded points must equal the Python call exactly'
    )
