"""Owner 9b6a82bdc: four app message levels, default Warning, errors retained."""

import os
import subprocess
from pathlib import Path

import pytest

from tests.system.py.test_onboarding_logging import invoke, logger_binary  # noqa: F401

ROOT = Path(__file__).resolve().parents[3]


@pytest.mark.parametrize('level', [None, 'Error', 'Warning', 'Info', 'Debug'])
def test_actual_app_logger_filters_each_level_and_always_keeps_errors(
    level,
    logger_binary,  # noqa: F811 - real native prerequisite fixture
    tmp_path,
):
    result = invoke(
        logger_binary,
        tmp_path / 'logs',
        '2026-07-18T09:41:26.125+02:00',
        'thresholds',
        **({'level': level} if level else {}),
    )
    if level is None:
        assert result['default_level'].casefold() == 'warning', (
            'The actual app run logger starts at Warning without a saved override'
        )
    threshold = (level or 'Warning').casefold()
    ordered = ['error', 'warning', 'info', 'debug']
    for severity in ordered:
        expected = ordered.index(severity) <= ordered.index(threshold)
        marker = 'level-' + severity + '-sentinel'
        assert (marker in Path(result['path']).read_text(encoding='utf-8')) == expected, (
            'The app log file applies the chosen severity threshold and always keeps Error'
        )
        assert (marker in result['terminal']) == expected, (
            'The actual app terminal sink applies the same message level as its file'
        )


@pytest.mark.parametrize(
    'case', ['default_is_warning', 'selector_changes_the_actual_message_sink']
)
def test_app_preferences_expose_the_same_four_message_levels(case, tmp_path):
    runner = Path(os.environ.get('EDI_APP_TEST_RUNNER', ROOT / 'build/app/app/edi_app_tests'))
    assert runner.is_file(), 'Message-level prerequisite: build the actual Qt app test host'
    result = subprocess.run(
        [
            str(runner),
            '-input',
            str(ROOT / 'tests/unit/app/tst_user_message_level.qml'),
            '-o',
            '-,txt',
            'UserMessageLevel::test_' + case,
        ],
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
        env={
            **os.environ,
            'QT_QPA_PLATFORM': 'offscreen',
            'QT_QUICK_BACKEND': 'software',
            'EDI_APP_DATA_DIR': str(tmp_path / 'data'),
            'XDG_CONFIG_HOME': str(tmp_path / 'config'),
        },
    )
    output = result.stdout + result.stderr
    assert result.returncode == 0 and '::test_' + case + '()' in output, (
        'The actual app message-level control completes its selected interaction: ' + output
    )
    assert '0 failed' in output and not any(
        line.startswith('SKIP') for line in output.splitlines()
    ), 'The app message-level gate executes its actual control rather than skipping it'
