"""Actual app open and setting edits use the relation-applied nonzero model."""

import os
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
CASES = [
    'open_applies_scale_relation_before_guided_estimate',
    'open_completes_symmetry_before_guided_estimate',
    'auto_setting_edit_applies_changed_relation_before_guided_estimate',
]


@pytest.mark.parametrize('case', CASES)
def test_app_refresh_uses_the_relation_applied_model(case):
    runner = Path(os.environ.get('EDI_APP_TEST_RUNNER', ROOT / 'build/app/app/edi_app_tests'))
    assert runner.is_file(), 'The lifecycle gate requires the built production Qt test host'
    try:
        completed = subprocess.run(
            [
                str(runner),
                '-input',
                str(ROOT / 'tests/unit/app/tst_background_estimate_relations.qml'),
                'BackgroundEstimateRelations::test_' + case,
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
        status, output = completed.returncode, completed.stdout + completed.stderr
    except subprocess.TimeoutExpired as error:
        captured = error.stdout or ''
        if isinstance(captured, bytes):
            captured = captured.decode(errors='replace')
        status, output = -1, captured + 'The native lifecycle operation exceeded 15 seconds'
    assert status == 0, (
        'The real app must apply declared and symmetry relations before guided estimation: '
        + case
        + '\n'
        + output
    )
    assert 'FAIL!' not in output, (
        'Every executed relation-order QML assertion must complete successfully'
    )
