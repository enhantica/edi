"""Exercise only the app-owned structure-curve toggle and both saved values."""

import os
from pathlib import Path

import pytest
from test_table_about_and_scan_views import ROOT, run_view_phase


@pytest.fixture(scope='module')
def toolbar_receipts():
    override = os.environ.get('EDI_APP_TEST_RUNNER')
    candidates = (
        [Path(override)]
        if override
        else [ROOT / 'build/app/app/edi_app_tests', ROOT / 'build/app/edi_app_tests']
    )
    binary = next((path for path in candidates if path.is_file()), None)
    assert binary is not None, (
        'Toolbar acceptance requires the current native application test host'
    )
    receipts = {}
    for state in ('on', 'off'):
        phase = 'StructureScanViews::test_structure_toolbar_toggle_and_saved_state:' + state
        result = run_view_phase(binary, 'tst_structure_scan_views.qml', phase)
        print(f'Toolbar phase {state}: status={result.returncode}', flush=True)
        print(result.stdout + result.stderr, flush=True)
        receipts[state] = result
    return receipts


@pytest.mark.parametrize('state', ['on', 'off'])
def test_structure_toolbar_saved_state(toolbar_receipts, state):
    result = toolbar_receipts[state]
    output = result.stdout + result.stderr
    assert result.returncode == 0, (
        'The actual app-owned chart satisfies toolbar acceptance: ' + output
    )
    assert (
        f'::StructureScanViews::test_structure_toolbar_toggle_and_saved_state({state})' in output
        and '0 failed' in output
    ), 'The requested toolbar case must run completely: ' + output
    assert not any(line.startswith('SKIP') for line in output.splitlines()), (
        'Neither saved toolbar value may be skipped'
    )
