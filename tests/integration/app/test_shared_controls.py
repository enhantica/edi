"""Shared UI acceptance through the production Qt host, without network access."""

import os
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
CASES = [
    ('tst_shared_tooltips.qml', 'SharedTooltips', 'defaults'),
    ('tst_shared_tooltips.qml', 'SharedTooltips', 'migration'),
    ('tst_shared_tooltips.qml', 'SharedTooltips', 'persistence'),
    ('tst_shared_tooltips.qml', 'SharedTooltips', 'levels'),
    ('tst_shared_tooltips.qml', 'SharedTooltips', 'delay_clock'),
    ('tst_shared_tooltips.qml', 'SharedTooltips', 'disabled_app_control'),
    ('tst_shared_tooltips.qml', 'SharedTooltips', 'app_bar'),
    ('tst_shared_tooltips.qml', 'SharedTooltips', 'button_clicks'),
    ('tst_model_column_widths.qml', 'ModelColumnWidths', 'distant_row_metrics_and_scroll'),
]


@pytest.mark.parametrize(('file', 'suite', 'case'), CASES, ids=[case for _, _, case in CASES])
def test_shared_control_contract(file, suite, case):
    runner = Path(os.environ.get('EDI_APP_TEST_RUNNER', ROOT / 'build/app/app/edi_app_tests'))
    assert runner.is_file(), 'Shared control acceptance requires the current production Qt host'
    result = subprocess.run(
        [
            str(runner),
            '-input',
            str(ROOT / 'tests/unit/app' / file),
            f'{suite}::test_{case}',
            '-o',
            '-,txt',
        ],
        capture_output=True,
        text=True,
        timeout=20,
        env={**os.environ, 'QT_QPA_PLATFORM': 'offscreen', 'QT_QUICK_BACKEND': 'software'},
        check=False,
    )
    output = result.stdout + result.stderr
    assert result.returncode == 0, (
        'The actual shared control must satisfy its UI contract: ' + output
    )
    assert f'::{suite}::test_{case}' in output and '0 failed' in output, (
        'The production host must execute the named case, rather than an empty selection'
    )
    assert 'SKIP ' not in output, 'Every shared UI acceptance case must execute without a skip'
