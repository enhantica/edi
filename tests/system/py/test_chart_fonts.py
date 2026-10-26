"""Actual tick/title font equality on desktop and the pinned Qt web kit."""

import os
import re

import pytest

from tests.fixtures.fast_chart_redraws.rendering import ROOT, capture

CASES = [
    'powder-main',
    'powder-residual',
    'powder-bragg',
    'single-squared',
    'single-f',
    'correlations',
    'evolution',
    'stacked',
    'map',
    'structure-labels',
    'structure-axis-letters',
]


@pytest.fixture(scope='module')
def native_fonts():
    return {
        case: capture(
            [
                os.environ.get('EDI_APP_TEST_RUNNER', ROOT / 'build/app/app/edi_app_tests'),
                '-input',
                ROOT / 'tests/system/app/ChartFonts.qml',
                '-o',
                '-,txt',
                'ChartFonts::test_fonts:' + case,
            ],
            timeout=60,
        )
        for case in CASES
    }


@pytest.mark.parametrize('case', CASES)
def test_ticks_and_axis_titles_share_the_app_font(native_fonts, case):
    status, output = native_fonts[case]
    require_case(status, output, case)


def require_case(status, output, case):
    summary = re.findall(r'Totals: (\d+) passed, (\d+) failed, (\d+) skipped', output)
    assert len(summary) == 1 and status == int(summary[0][1]), (
        'The real font witness must complete with a coherent Qt Test result, not a host error: '
        + output
    )
    assert f'PASS   : edi_app::ChartFonts::test_fonts({case})' in output, (
        'Every chart and pane must use its actual axis-title app font family and pixel size: '
        + output
    )
    assert '::ChartFonts::cleanupTestCase()' in output, (
        'The font witness must finish after default, changed shared font and restored checks'
    )
    for phase in ('default', 'changed-shared-font', 'restored'):
        assert any(
            'CHART_FONT ' in line and f'"chart":"{case}"' in line and f'"phase":"{phase}"' in line
            for line in output.splitlines()
        ), 'Every chart font gate exercises the shared font change and restoration on real labels'
