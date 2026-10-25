"""Actual legend input, per-chart runtime state and both hidden-curve range choices."""

import os

import pytest

from tests.fixtures.fast_chart_redraws.rendering import ROOT, capture

CASES = [
    'test_preference',
    *[
        'test_curves:' + page + '-' + kind + '-' + mode
        for page in ('experiment', 'analysis')
        for kind in ('powder', 'single')
        for mode in ('keep', 'fit')
    ],
]


@pytest.fixture(scope='module')
def legend_receipts():
    receipts = {}
    for case in CASES:
        receipts[case] = capture(
            [
                os.environ.get('EDI_APP_TEST_RUNNER', ROOT / 'build/app/app/edi_app_tests'),
                '-input',
                ROOT / 'tests/system/app/LegendVisibility.qml',
                '-o',
                '-,txt',
                'LegendVisibility::' + case,
            ],
            timeout=150,
        )
    return receipts


@pytest.mark.parametrize('case', CASES)
def test_legend_curve_visibility_and_range(legend_receipts, case):
    status, output = legend_receipts[case]
    assert status == 0, 'The actual legend visibility and range contract must complete: ' + output
    name, _, tag = case.partition(':')
    assert 'PASS   : edi_app::LegendVisibility::' + name + '(' + tag + ')' in output, (
        'Every requested chart and preference scenario must execute without skipping'
    )
    assert '::LegendVisibility::cleanupTestCase()' in output, (
        'The actual legend actor must finish after project-reset and runtime-state checks'
    )
