"""The saved three-way policy replaces the former Boolean enablement contract."""

import json
import os
import re
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]


@pytest.mark.parametrize(
    ('authored', 'expected', 'chosen'),
    [
        ('auto', 'auto', 'subtract'),
        ('subtract', 'subtract', 'ignore'),
        ('ignore', 'ignore', 'auto'),
        ('true', 'subtract', 'ignore'),
        ('false', 'ignore', 'subtract'),
    ],
)
def test_model_policy_selector_saves_and_reloads_tokens_and_migrates_booleans(
    authored, expected, chosen
):
    runner = Path(os.environ.get('EDI_APP_TEST_RUNNER', ROOT / 'build/app/app/edi_app_tests'))
    assert runner.is_file(), 'Policy acceptance requires the built production Qt host'
    suffix = 'legacy_' + authored if authored in {'true', 'false'} else authored
    case = 'BackgroundEstimateSettings::test_model_policy_' + suffix
    result = subprocess.run(
        [
            str(runner),
            '-input',
            str(ROOT / 'tests/unit/app/tst_background_estimate_settings.qml'),
            case,
            '-o',
            '-,txt',
        ],
        env={**os.environ, 'QT_QPA_PLATFORM': 'offscreen', 'QT_QUICK_BACKEND': 'software'},
        capture_output=True,
        text=True,
        # Process scheduling headroom; the measured system tier stays five seconds.
        timeout=15.0,
        check=False,
    )
    output = result.stdout + result.stderr
    assert result.returncode == 0 and f'PASS   : edi_app::{case}()' in output, (
        'The app must expose selector objectName background_estimate.use_model with model tokens '
        'auto/subtract/ignore, retain the authored policy, and save/reload actual user selection: '
        + output
    )
    receipts = re.findall(r'BACKGROUND_MODEL_POLICY (\{[^\n]+\})', output)
    assert len(receipts) == 1, (
        'Every policy and legacy Boolean must complete one actual app round trip'
    )
    assert json.loads(receipts[0]) == {
        'authored': authored,
        'canonical': expected,
        'chosen': chosen,
        'reloaded': chosen,
    }, 'The app must map true/false to subtract/ignore and persist the selected canonical token'


def test_each_auto_estimate_reports_information_in_messages_instead_of_background():
    runner = Path(os.environ.get('EDI_APP_TEST_RUNNER', ROOT / 'build/app/app/edi_app_tests'))
    assert runner.is_file(), 'Auto information acceptance requires the production Qt host'
    case = 'BackgroundEstimateSettings::test_auto_reason_is_information_for_each_estimate'
    result = subprocess.run(
        [
            str(runner),
            '-input',
            str(ROOT / 'tests/unit/app/tst_background_estimate_settings.qml'),
            case,
            '-o',
            '-,txt',
        ],
        env={**os.environ, 'QT_QPA_PLATFORM': 'offscreen', 'QT_QUICK_BACKEND': 'software'},
        capture_output=True,
        text=True,
        # Process scheduling headroom; the measured system tier stays five seconds.
        timeout=15.0,
        check=False,
    )
    output = result.stdout + result.stderr
    assert result.returncode == 0 and f'PASS   : edi_app::{case}()' in output, (
        'Each real Auto Estimate must append an information entry with measured share and the '
        'one-percent rule to Session.loadWarnings, keeping reason text out of Background: '
        + output
    )
    assert 'BACKGROUND_AUTO_MESSAGES information=2 repeated=true sidebarReason=false' in output, (
        'The Auto Messages workflow must finish both estimates and the no-sidebar-reason check'
    )
