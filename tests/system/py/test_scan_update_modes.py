"""Observe separate scan update choices, migration, ordered drawing and backlog."""

import os
from pathlib import Path

import pytest

from tests.fixtures.fast_chart_redraws.rendering import ROOT, capture


@pytest.fixture(scope='module')
def update_captures(request):
    cases = {
        item.callspec.params['case']
        for item in request.session.items
        if item.module is request.module and hasattr(item, 'callspec')
    }
    binary = Path(os.environ.get('EDI_APP_TEST_RUNNER', ROOT / 'build/app/app/edi_app_tests'))
    return {
        case: capture(
            [
                binary,
                '-input',
                ROOT / 'tests/system/app/ScanUpdates.qml',
                '-o',
                '-,txt',
                'ScanUpdates::' + case,
            ],
            timeout=150,
        )
        for case in sorted(cases)
    }


@pytest.mark.parametrize(
    'case',
    [
        'test_choices_and_legacy',
        'test_catchup:pattern',
        'test_catchup:stacked',
        'test_wait_views:stacked',
        'test_wait_views:map',
        'test_wait_without_a_pattern_view',
    ],
)
def test_real_scan_update_contract(update_captures, case):
    status, output = update_captures[case]
    name, _, tag = case.partition(':')
    assert status == 0, 'The actual scan-update contract must pass: ' + output
    assert f'PASS   : edi_app::ScanUpdates::{name}({tag})' in output, (
        'Every requested scan-update scenario must run without skipping'
    )
    assert '::ScanUpdates::cleanupTestCase()' in output, (
        'The scan-update actor must complete cleanup after real scientific work'
    )
