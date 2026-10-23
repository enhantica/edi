"""Run only the production dependency popup inclusion and geometry actors."""

import os
from pathlib import Path

import pytest
from test_table_about_and_scan_views import ROOT, run_view_phase

CASES = ['component_list_excludes_development_sources'] + [
    case + ':' + theme
    for case in ('columns_fit_content', 'cells_have_standard_margins')
    for theme in ('light', 'dark')
]


@pytest.fixture(scope='module')
def component_receipts():
    override = os.environ.get('EDI_APP_TEST_RUNNER')
    candidates = [Path(override)] if override else [ROOT / 'build/app/app/edi_app_tests']
    binary = next((path for path in candidates if path.is_file()), None)
    assert binary is not None, 'Popup acceptance requires the actual native Qt application host'
    results = {}
    for case in CASES:
        result = run_view_phase(
            binary, 'tst_about_components.qml', 'AboutComponents::test_' + case
        )
        print(f'Popup phase {case}: status={result.returncode}', flush=True)
        print(result.stdout + result.stderr, flush=True)
        results[case] = result
    return results


@pytest.mark.parametrize('case', CASES)
def test_actual_dependency_popup(component_receipts, case):
    result = component_receipts[case]
    output = result.stdout + result.stderr
    assert result.returncode == 0, 'The production dependency popup meets its contract: ' + output
    function, _, tag = case.partition(':')
    expected = '::AboutComponents::test_' + function + ('(' + tag + ')' if tag else '()')
    assert expected in output and '0 failed' in output, (
        'The exact requested popup case must execute completely: ' + output
    )
    assert not any(line.startswith('SKIP') for line in output.splitlines()), (
        'No dependency popup inclusion or geometry case may be skipped'
    )
