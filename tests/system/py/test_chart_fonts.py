"""Actual tick/title font equality on desktop and the pinned Qt web kit."""

import json
import os
import re

import pytest

from tests.fixtures.fast_chart_redraws.rendering import ROOT, capture

INVENTORY = json.loads((ROOT / 'tests/fixtures/chart_fonts/cases.json').read_text())
if not isinstance(INVENTORY, list) or not all(
    isinstance(row, dict) and isinstance(row.get('tag'), str) for row in INVENTORY
):
    raise ValueError('The font inventory must be a list of named chart-input records')
CASES = [row['tag'] for row in INVENTORY]


def test_font_inventory_covers_every_chart_and_pane():
    assert set(CASES) == {
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
    } and len(CASES) == len(set(CASES)), (
        'The declared font inventory covers every owner-required chart and pane exactly once'
    )
    for row in INVENTORY:
        tag = row['tag']
        if tag.startswith('powder-'):
            wanted = {'tag': tag, 'kind': 'powder', 'pane': tag.removeprefix('powder-')}
        elif tag.startswith('single-'):
            wanted = {
                'tag': tag,
                'kind': 'single',
                'quantity': 'f_squared' if tag == 'single-squared' else 'f',
            }
        elif tag.startswith('structure-'):
            wanted = {
                'tag': tag,
                'kind': 'powder',
                'mode': 'structure',
                'field': 'font' if tag == 'structure-labels' else 'letterFont',
            }
        elif tag == 'correlations':
            wanted = {'tag': tag, 'kind': tag}
        else:
            wanted = {'tag': tag, 'kind': 'scan', 'mode': tag}
        assert row == wanted, (
            'Every declared font case selects its actual required chart, pane or plotted quantity'
        )


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
