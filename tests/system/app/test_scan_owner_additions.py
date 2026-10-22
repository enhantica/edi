"""Observe every new scan contract in one real rendering session."""

import os
import re
import signal
import subprocess
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
CASES = (
    'test_map_default_and_saved_choice',
    'test_joint_labels_outside_axis:stacked-light',
    'test_joint_labels_outside_axis:stacked-dark',
    'test_joint_labels_outside_axis:map-light',
    'test_joint_labels_outside_axis:map-dark',
    'test_stacked_schemes_and_line_width:light',
    'test_stacked_schemes_and_line_width:dark',
    'test_owner_axis_name:stacked',
    'test_owner_axis_name:map',
    'test_owner_d_availability:stacked',
    'test_owner_d_availability:map',
    'test_owner_toolbar_centred:stacked',
    'test_owner_toolbar_centred:map',
    'test_owner_secondary_click:stacked',
    'test_owner_secondary_click:map',
    'test_owner_zoom_samples:stacked',
    'test_owner_zoom_samples:map',
    'test_owner_excluded_regions:stacked',
    'test_owner_excluded_regions:map',
    'test_owner_indicator:stacked-light',
    'test_owner_indicator:stacked-dark',
    'test_owner_indicator:map-light',
    'test_owner_indicator:map-dark',
    'test_owner_indicator:evolution-light',
    'test_owner_indicator:evolution-dark',
    'test_joint_tab_availability:scan',
    'test_joint_tab_availability:joint',
    'test_joint_tab_availability:single-multi',
    'test_joint_tab_availability:single',
    'test_joint_rows_and_common_d:stacked',
    'test_joint_rows_and_common_d:map',
)
CASES += tuple('test_owner_selector_widths:' + mode for mode in ('pattern', 'stacked', 'map'))
CASES += tuple(
    'test_joint_user_chosen_axes:' + mode + '-' + axes
    for mode in ('stacked', 'map')
    for axes in ('tof', 'cwl', 'mixed')
)
CASES += (
    'test_preferences_four_colour_choices:light',
    'test_preferences_four_colour_choices:dark',
    'test_preferences_map_shortcut_and_roster',
    'test_preferences_four_choices_remembered',
)
CASES += tuple(
    'test_experiment_analysis_scan_sharing:' + project + '-' + origin + '-' + mode
    for project in ('scan', 'tof', 'cwl', 'mixed')
    for origin in ('experiment', 'analysis')
    for mode in ('stacked', 'map')
)
CASES += ('test_chart_colour_selector_location',)

CASES += tuple(
    'test_stacked_tick_labels_cover_rows_only:' + mode + '-' + theme
    for mode in ('value', 'index')
    for theme in ('light', 'dark')
)

CASES += tuple(
    'test_scan_axis_fonts:' + mode + '-' + theme
    for mode in ('stacked', 'map', 'evolution')
    for theme in ('light', 'dark')
)
CASES += tuple(
    'test_row_order_and_map_bands:' + mode + '-' + kind + '-' + theme
    for mode in ('stacked', 'map')
    for kind in ('file', 'datablock')
    for theme in ('light', 'dark')
)
CASES += tuple('test_map_numeric_dataset_ticks:' + theme for theme in ('light', 'dark'))
CASES += tuple(
    'test_row_label_thinning:' + mode + '-' + kind
    for mode in ('stacked', 'map')
    for kind in (('file', 'datablock', 'value') if mode == 'stacked' else ('file', 'datablock'))
)


@pytest.fixture(scope='module')
def scan_receipt(request):
    binary = Path(os.environ.get('EDI_APP_TEST_RUNNER', ROOT / 'build/app/app/edi_app_tests'))
    assert binary.is_file(), 'Scan content acceptance requires the actual native test host'
    groups = {}
    for item in request.session.items:
        if item.module is request.module and hasattr(item, 'callspec'):
            case = item.callspec.params['case']
            groups.setdefault(case.partition(':')[0], []).append(case)

    def run(cases):
        command = [
            'bash',
            str(ROOT / 'tests/fixtures/scan_views/run.sh'),
            str(binary),
            '-input',
            str(ROOT / 'tests/unit/app/tst_scan_view_content.qml'),
            '-o',
            '-,txt',
            *['ScanViewContent::' + case for case in cases],
        ]
        process = subprocess.Popen(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            start_new_session=True,
        )
        print(f'Acceptance actor process group {process.pid}: {cases}', flush=True)
        try:
            output, _ = process.communicate(timeout=40)
            status = process.returncode
        except subprocess.TimeoutExpired:
            os.killpg(process.pid, signal.SIGTERM)
            try:
                output, _ = process.communicate(timeout=5)
            except subprocess.TimeoutExpired:
                os.killpg(process.pid, signal.SIGKILL)
                output, _ = process.communicate()
            output += '\nThe acceptance function exceeded its unchanged actor watchdog'
            status = 124
        print(output)
        return cases, status, output

    receipts = {}
    batches = [
        cases[index : index + 2] for cases in groups.values() for index in range(0, len(cases), 2)
    ]
    batches.sort(
        key=lambda cases: (
            not cases[0].startswith('test_offered_maps'),
            not cases[0].startswith('test_background_to_experiment'),
            -len(cases),
        )
    )
    with ThreadPoolExecutor(max_workers=3) as pool:
        for cases, status, output in pool.map(run, batches):
            for case in cases:
                receipts[case] = status, output
    return receipts


@pytest.mark.parametrize('case', CASES)
def test_scan_owner_addition(scan_receipt, case):
    status, output = scan_receipt[case]
    assert (
        0 <= status < 128
        and status != 124
        and 'Totals:' in output
        and '::ScanViewContent::cleanupTestCase()' in output
    ), (
        'A crashed, skipped or incomplete acceptance function cannot supply passing receipts: '
        + output
    )
    name, _, tag = case.partition(':')
    witness = f'::ScanViewContent::{name}({tag})'
    lines = [line for line in output.splitlines() if witness in line]
    assert any(line.startswith('PASS ') for line in lines) and not any(
        re.match(r'FAIL|SKIP', line) for line in lines
    ), 'The requested production scan contract executes and passes without skipping: ' + '\n'.join(
        lines
    )
