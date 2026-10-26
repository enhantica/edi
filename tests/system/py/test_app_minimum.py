"""Observe the app-specific minimum and its non-destructive full-window overlay."""

import os

import pytest

from tests.fixtures.fast_chart_redraws.rendering import ROOT, capture

CASES = ['test_desktop_minimum', 'test_placeholder_boundary_and_state']


@pytest.fixture(scope='module')
def minimum_receipts():
    return {
        case: capture([
            os.environ.get('EDI_APP_TEST_RUNNER', ROOT / 'build/app/app/edi_app_tests'),
            '-input',
            ROOT / 'tests/unit/app/tst_fast_chart_redraws.qml',
            '-o',
            '-,txt',
            'FastChartRedraws::' + case,
        ])
        for case in CASES
    }


@pytest.mark.parametrize('case', CASES)
def test_app_minimum_and_overlay(minimum_receipts, case):
    status, output = minimum_receipts[case]
    assert status == 0, 'The actual minimum-size and overlay contract must pass: ' + output
    assert 'PASS   : edi_app::FastChartRedraws::' + case + '()' in output, (
        'Each requested native window boundary case must execute without skipping'
    )
    assert '::FastChartRedraws::cleanupTestCase()' in output, (
        'The minimum-size actor must complete cleanup after real resize and pointer input'
    )
