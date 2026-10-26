"""Unshown page/tab scan views defer work and catch up once with current data."""

import json
import os

import pytest

from tests.fixtures.fast_chart_redraws.rendering import ROOT, capture

CASES = [f'{page}-{mode}' for page in ('experiment', 'analysis') for mode in ('stacked', 'map')]


@pytest.fixture(scope='module')
def hidden_redraws():
    receipts = {}
    for case in CASES:
        status, output = capture(
            [
                os.environ.get('EDI_APP_TEST_RUNNER', ROOT / 'build/app/app/edi_app_tests'),
                '-input',
                ROOT / 'tests/system/app/HiddenScanRedraws.qml',
                '-o',
                '-,txt',
                'HiddenScanRedraws::test_hidden_views:' + case,
            ],
            timeout=90,
        )
        receipts[case] = status, output
    return receipts


@pytest.mark.parametrize('case', CASES)
def test_hidden_scan_views_build_once_with_latest_data(hidden_redraws, case):
    status, output = hidden_redraws[case]
    assert status == 0 and f'::HiddenScanRedraws::test_hidden_views({case})' in output, (
        'The exact hidden scan-view work and current-pixel actor must complete: ' + output
    )
    rows = [
        json.loads(line.split('HIDDEN_REDRAW ', 1)[1])
        for line in output.splitlines()
        if 'HIDDEN_REDRAW ' in line
    ]
    assert {row['context'] for row in rows} == {'page', 'tab'} and len(rows) == 2, (
        'Each page/mode combination exercises both hidden-page and hidden-tab data changes'
    )
    assert '0 failed' in output and '0 skipped' in output, (
        'No hidden-work or current-trace assertion is failed, omitted or skipped'
    )
