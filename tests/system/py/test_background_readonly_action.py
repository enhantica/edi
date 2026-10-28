"""Actual Main tables retain scrolling and parameter context while Auto refuses edits."""

import os
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]


@pytest.mark.parametrize(
    ('kind', 'suffix'),
    [
        ('line-segment', 'points'),
        ('polynomial', 'polynomial'),
        ('chebyshev', 'chebyshev'),
    ],
)
@pytest.mark.parametrize('scope', ['values', 'free', 'fixed'])
def test_auto_table_guards_values_and_allows_free_context_actions(kind, suffix, scope):
    runner = Path(os.environ.get('EDI_APP_TEST_RUNNER', ROOT / 'build/app/app/edi_app_tests'))
    assert runner.is_file(), 'Read-only acceptance requires the production Qt host'
    case = 'BackgroundReadonly::test_' + suffix + ('_' + scope if scope != 'values' else '')
    result = subprocess.run(
        [
            str(runner),
            '-input',
            str(ROOT / 'tests/unit/app/tst_background_readonly.qml'),
            case,
            '-o',
            '-,txt',
        ],
        env={**os.environ,
             'QT_QPA_PLATFORM': os.environ.get('QT_QPA_PLATFORM', 'offscreen'),
             'QT_QUICK_BACKEND': os.environ.get('QT_QUICK_BACKEND', 'software')},
        capture_output=True,
        text=True,
        # Process scheduling headroom; the measured system tier stays five seconds.
        timeout=15.0,
        check=False,
    )
    output = result.stdout + result.stderr
    assert result.returncode == 0 and f'PASS   : edi_app::{case}()' in output, (
        'Auto must refuse value edits, permit free toggles and keep Auto; scrolling, '
        'three actions and row deletes disabled, estimation mode selector restores Manual: '
        + output
    )
    assert 'BACKGROUND_READINESS mode=actual-click theme=settled' in output, (
        'Each read-only workflow must complete actual mode input and settled theme checks'
    )
    receipt = (
        'BACKGROUND_AUTO_FLAGS '
        + kind
        + ' row='
        + ('0' if scope == 'free' else '1')
        + ' context=toggle mode=auto'
        if scope != 'values'
        else 'BACKGROUND_READONLY '
        + kind
        + ' auto=refused scroll=true context=preserved manual=separate-control'
    )
    assert receipt in output, (
        'Every type must finish its bounded real context-toggle or Auto-to-Manual edit workflow'
    )


@pytest.mark.parametrize(
    'case',
    [
        'BackgroundEstimateSettings::test_point_keyboard_edit_sets_manual',
        'BackgroundEstimateLifecycle::test_first_edit_with_excluded_data_selects_manual',
    ],
)
def test_adapted_existing_edit_actors_choose_manual_explicitly(case):
    runner = Path(os.environ.get('EDI_APP_TEST_RUNNER', ROOT / 'build/app/app/edi_app_tests'))
    assert runner.is_file(), 'Existing mode-edit actors require the production Qt host'
    stem = 'settings' if case.startswith('BackgroundEstimateSettings::') else 'lifecycle'
    result = subprocess.run(
        [
            str(runner),
            '-input',
            str(ROOT / 'tests/unit/app' / ('tst_background_estimate_' + stem + '.qml')),
            case,
            '-o',
            '-,txt',
        ],
        env={**os.environ,
             'QT_QPA_PLATFORM': os.environ.get('QT_QPA_PLATFORM', 'offscreen'),
             'QT_QUICK_BACKEND': os.environ.get('QT_QUICK_BACKEND', 'software')},
        capture_output=True,
        text=True,
        # Process scheduling headroom; the measured system tier stays five seconds.
        timeout=15.0,
        check=False,
    )
    output = result.stdout + result.stderr
    assert result.returncode == 0 and f'PASS   : edi_app::{case}()' in output, (
        'The previously implicit-edit actor must now explicitly select Manual before committing '
        'its saved value, without relaxing its existing persistence assertions: ' + output
    )


@pytest.mark.parametrize(
    ('kind', 'suffix'),
    [
        ('line-segment', 'points'),
        ('polynomial', 'polynomial'),
        ('chebyshev', 'chebyshev'),
    ],
)
def test_scrolled_auto_table_returns_to_manual_and_accepts_the_real_value_edit(kind, suffix):
    runner = Path(os.environ.get('EDI_APP_TEST_RUNNER', ROOT / 'build/app/app/edi_app_tests'))
    assert runner.is_file(), 'Manual return requires the actual production Qt host'
    case = 'BackgroundReadonly::test_' + suffix + '_manual_return'
    result = subprocess.run(
        [
            str(runner),
            '-input',
            str(ROOT / 'tests/unit/app/tst_background_readonly.qml'),
            case,
            '-o',
            '-,txt',
        ],
        env={**os.environ,
             'QT_QPA_PLATFORM': os.environ.get('QT_QPA_PLATFORM', 'offscreen'),
             'QT_QUICK_BACKEND': os.environ.get('QT_QUICK_BACKEND', 'software')},
        capture_output=True,
        text=True,
        # Process scheduling headroom; the measured system tier stays five seconds.
        timeout=15.0,
        check=False,
    )
    output = result.stdout + result.stderr
    assert result.returncode == 0 and f'PASS   : edi_app::{case}()' in output, (
        'A real Manual selection after Auto scrolling must restore all actions and value editing: '
        + output
    )
    assert (
        'BACKGROUND_MANUAL_RETURN ' + kind + ' auto=loaded scroll=true manual=edited' in output
    ), 'The bounded return case must finish the retained scroll, Manual and typed-value properties'
