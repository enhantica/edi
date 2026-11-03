"""Observe chart placement and window boundaries in the native production host."""

import os
import re
from pathlib import Path

import pytest

from tests.fixtures.fast_chart_redraws.rendering import capture

ROOT = Path(__file__).resolve().parents[3]
CASES = [
    'test_gpu_backend',
    'test_adaptive_is_retained',
    *[f'test_placement:{count}' for count in (1, 3, 324)],
    *[f'test_wheel_reaches_last_dataset:{page}' for page in ('experiment', 'analysis')],
    *[f'test_joint_exclusions_follow_placement:{mode}' for mode in ('gpu', 'software')],
    *[f'test_highlight:{mode}' for mode in ('stacked', 'map')],
    *[f'test_hover_tooltip:{mode}' for mode in ('stacked', 'map')],
    *[
        f'test_toolbar:{page}-{mode}-{width}'
        for page in ('experiment', 'analysis')
        for mode in ('pattern', 'stacked', 'map')
        for width in (1200, 740, 420)
    ],
    *[f'test_cache_and_pacing:{mode}' for mode in ('stacked', 'map')],
    *[
        f'test_pages_at_minimum:{page}'
        for page in ('home', 'project', 'structure', 'experiment', 'analysis', 'report')
    ],
]


@pytest.fixture(scope='module')
def chart_receipt(request):
    binary = Path(os.environ.get('EDI_APP_TEST_RUNNER', ROOT / 'build/app/app/edi_app_tests'))
    assert binary.is_file(), 'Chart acceptance requires the current native app test host'
    selected = {
        item.callspec.params['case']
        for item in request.session.items
        if item.module is request.module and hasattr(item, 'callspec')
    }
    receipts = {}
    for case in CASES:
        if case not in selected:
            continue
        status, output = capture(
            [
                str(binary),
                '-input',
                str(ROOT / 'tests/unit/app/tst_fast_chart_redraws.qml'),
                '-o',
                '-,txt',
                'FastChartRedraws::' + case,
            ],
            timeout=90 if case == 'test_adaptive_is_retained' else 45,
        )
        receipts[case] = status, output
        print('Chart actor ' + case + ': ' + str(status), flush=True)
    return receipts


@pytest.mark.parametrize('case', CASES)
def test_chart_contract(chart_receipt, case):
    status, output = chart_receipt[case]
    assert 0 <= status < 128 and status != 124 and 'Totals:' in output, (
        'The native OpenGL actor must finish without crashing: ' + output
    )
    assert '::FastChartRedraws::cleanupTestCase()' in output, (
        'The complete chart acceptance actor must reach cleanup: ' + output
    )
    name, _, tag = case.partition(':')
    witness = f'::FastChartRedraws::{name}({tag})'
    lines = [line for line in output.splitlines() if witness in line]
    assert any(line.startswith('PASS ') for line in lines) and not any(
        re.match(r'FAIL|SKIP', line) for line in lines
    ), 'Each requested chart contract must execute and pass without skipping: ' + '\n'.join(lines)


def test_selection_rectangle_is_retired():
    assert not (ROOT / 'app/qml/Components/SelectedPatternBox.qml').exists(), (
        'The superseded selected-pattern rectangle is removed from the product tree'
    )
