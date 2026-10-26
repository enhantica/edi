"""Exercise the fit shortcuts and results preference in the production window."""

import os
import re
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
CASES = [
    'test_visibility_tracks_analysis_on_every_page',
    'test_unavailable_action_matches_analysis',
    'test_status_start',
    'test_continue_matches_analysis',
    'test_running_action:status',
    'test_running_action:analysis',
    'test_button_style:light',
    'test_button_style:dark',
    'test_preference_default_and_user_store',
    *(
        f'test_results_preference:{kind}-{choice}'
        for kind in ('single', 'scan')
        for choice in ('on', 'off')
    ),
    'test_existing_analysis_start',
    'test_existing_completion:single',
    'test_existing_completion:scan',
]


@pytest.fixture(scope='module')
def fit_control_actors():
    runner = Path(os.environ.get('EDI_APP_TEST_RUNNER', ROOT / 'build/app/app/edi_app_tests'))
    assert runner.is_file(), (
        'Fit shortcut acceptance requires the actual built Qt application host'
    )
    result = subprocess.run(
        [
            str(runner),
            '-input',
            str(ROOT / 'tests/unit/app/tst_status_fit_controls.qml'),
            '-o',
            '-,txt',
        ],
        cwd=ROOT,
        env={**os.environ, 'QT_QPA_PLATFORM': 'offscreen', 'QT_QUICK_BACKEND': 'software'},
        capture_output=True,
        text=True,
        timeout=120,
        check=False,
    )
    output = result.stdout + result.stderr
    assert 0 <= result.returncode <= len(CASES), (
        'The real fit-control host must complete without a crash: ' + output
    )
    outcomes = {}
    for status, function, tag in re.findall(
        r'^(PASS|FAIL!|SKIP)\s*:\s+edi_app::StatusFitControls::(\w+)\(([^)]*)\)',
        output,
        re.MULTILINE,
    ):
        case = function + (':' + tag if tag else '')
        if case in CASES:
            outcomes.setdefault(case, []).append(status)
    assert set(outcomes) == set(CASES), (
        'The shared Qt host executes exactly every requested fit-control actor: ' + output
    )
    assert result.returncode == sum(states != ['PASS'] for states in outcomes.values()), (
        'The Qt exit count agrees with the independently parsed actor failures: ' + output
    )
    return outcomes, output


@pytest.mark.parametrize('case', CASES)
def test_status_fit_contract(fit_control_actors, case):
    outcomes, output = fit_control_actors
    assert outcomes[case] == ['PASS'], (
        'The status Fit shortcut, outcome button and results preference meet their app contract: '
        + case
        + '\n'
        + output
    )
