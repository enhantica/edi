"""Unshown page/tab scan views defer work and catch up once with current data."""

import json
import os

import pytest

from tests.fixtures.fast_chart_redraws.rendering import ROOT, capture

CASES = {
    f'{page}-{mode}': f'test_hidden_views:{page}-{mode}'
    for page in ('experiment', 'analysis')
    for mode in ('stacked', 'map')
}
CASES.update({
    f'request-{page}-{path}-{trigger}': f'test_inactive_requests:{page}-{path}-{trigger}'
    for page in ('experiment', 'analysis')
    for path in ('stacked-gpu', 'stacked-painter', 'map')
    for trigger in ('queued', 'renderer', 'resize')
})


@pytest.fixture(scope='module')
def hidden_redraws(request):
    selected = {
        item.callspec.params['case']
        for item in request.session.items
        if item.module is request.module and hasattr(item, 'callspec')
    }
    receipts = {}
    for case, actor in CASES.items():
        if case not in selected:
            continue
        status, output = capture(
            [
                os.environ.get('EDI_APP_TEST_RUNNER', ROOT / 'build/app/app/edi_app_tests'),
                '-input',
                ROOT / 'tests/system/app/HiddenScanRedraws.qml',
                '-o',
                '-,txt',
                'HiddenScanRedraws::' + actor,
            ],
            timeout=90,
        )
        receipts[case] = status, output
    return receipts


@pytest.mark.parametrize('case', CASES)
def test_hidden_scan_views_build_once_with_latest_data(hidden_redraws, case):
    status, output = hidden_redraws[case]
    name, _, tag = CASES[case].partition(':')
    assert status == 0 and f'::HiddenScanRedraws::{name}({tag})' in output, (
        'The exact hidden scan-view work and current-pixel actor must complete: ' + output
    )
    marker = 'INACTIVE_REQUEST ' if case.startswith('request-') else 'HIDDEN_REDRAW '
    rows = [json.loads(line.split(marker, 1)[1]) for line in output.splitlines() if marker in line]
    if case.startswith('request-'):
        assert (
            len(rows) == 1
            and ('request-' + rows[0]['page'] + '-' + rows[0]['path'] + '-' + rows[0]['trigger'])
            == case
        ), 'The requested inactive trigger and real renderer path must complete exactly once'
    else:
        assert {row['context'] for row in rows} == {'page', 'tab'} and len(rows) == 2, (
            'Each page/mode combination exercises both hidden-page and hidden-tab data changes'
        )
    assert '0 failed' in output and '0 skipped' in output, (
        'No hidden-work or current-trace assertion is failed, omitted or skipped'
    )
