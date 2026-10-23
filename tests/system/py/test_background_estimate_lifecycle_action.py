"""Actual app preview, persistence, first edits and numeric-domain lifecycle boundaries."""

import os
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
CASES = [
    'independent_scan_preserves_the_template',
    'sequential_scan_preserves_the_template',
    'guided_preview_uses_the_visible_points',
    'delegated_save_keeps_the_visible_guided_points',
    'open_unchanged_auto_preserves_saved_model_guided_points',
    'first_edit_with_excluded_data_selects_manual',
    'infinite_width_is_refused_before_defaults',
    'overflowing_width_is_refused_before_defaults',
    'infinite_smoothness_is_refused_before_defaults',
]


@pytest.mark.parametrize('case', CASES)
def test_actual_app_estimation_lifecycle_contract(case):
    runner = Path(os.environ.get('EDI_APP_TEST_RUNNER', ROOT / 'build/app/app/edi_app_tests'))
    assert runner.is_file(), 'The lifecycle gate requires the built production Qt test host'
    try:
        completed = subprocess.run(
            [
                str(runner),
                '-input',
                str(ROOT / 'tests/unit/app/tst_background_estimate_lifecycle.qml'),
                'BackgroundEstimateLifecycle::test_' + case,
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
        'The real app must preserve estimation provenance, first edits and numeric refusals: '
        + case
        + '\n'
        + output
    )
    assert 'FAIL!' not in output, (
        'Every executed lifecycle QML assertion must complete successfully'
    )
