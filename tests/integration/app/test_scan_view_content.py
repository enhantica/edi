"""Observe every new scan contract in one real rendering session."""

import os
import re
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
CASES = (
    [
        f'{case}:{mode}'
        for case in (
            'test_current_row_tracks_async_coordinates',
            'test_unreadable_pattern_is_visibly_refused',
            'test_scan_toolbar_and_top_margin',
            'test_scan_top_margin',
            'test_every_pattern_is_drawn',
            'test_zoom_stays_on_and_reset_restores_axes',
        )
        for mode in ('stacked', 'map')
    ]
    + [
        f'test_independent_axis_type_buttons:{mode}-{axis}'
        for mode in ('stacked', 'map')
        for axis in ('x', 'y', 'z')
        if mode == 'map' or axis != 'z'
    ]
    + [
        *[
            f'test_background_to_experiment_ramp:{mode}-{theme}'
            for mode in ('stacked', 'map')
            for theme in ('light', 'dark')
        ],
        'test_map_key_and_image_use_frozen_interior_samples',
        'test_map_interpolates_between_neighboring_patterns',
        'test_selected_map_line_is_always_drawn',
        'test_antialiased_ink_observer',
        'test_map_interpolation_default',
        *[
            f'test_map_interpolation_toggle:{mode}-{theme}'
            for mode in ('stepped', 'smooth')
            for theme in ('light', 'dark')
        ],
        *[
            f'test_offered_maps_are_readable_in_both_themes:{mode}-{theme}'
            for mode in ('stacked', 'map')
            for theme in ('light', 'dark')
        ],
    ]
)


@pytest.fixture(scope='module')
def scan_receipt():
    binary = Path(os.environ.get('EDI_APP_TEST_RUNNER', ROOT / 'build/app/app/edi_app_tests'))
    assert binary.is_file(), 'Scan content acceptance requires the actual native test host'
    command = [
        'bash',
        str(ROOT / 'tests/fixtures/scan_views/run.sh'),
        str(binary),
        '-input',
        str(ROOT / 'tests/unit/app/tst_scan_view_content.qml'),
        '-o',
        '-,txt',
    ]
    try:
        result = subprocess.run(command, capture_output=True, text=True, check=False, timeout=40)
    except subprocess.TimeoutExpired as error:
        pytest.fail('The real scan renderer exceeded its bounded actor watchdog: ' + str(error))
    output = result.stdout + result.stderr
    print(output)
    assert (
        result.returncode >= 0
        and 'Totals:' in output
        and '::ScanViewContent::cleanupTestCase()' in output
    ), (
        'A crashed or incomplete rendering session cannot supply passing per-case receipts: '
        + output
    )
    return output


@pytest.mark.parametrize('case', CASES)
def test_scan_view_content(scan_receipt, case):
    name, _, tag = case.partition(':')
    witness = f'::ScanViewContent::{name}({tag})'
    lines = [line for line in scan_receipt.splitlines() if witness in line]
    assert any(line.startswith('PASS ') for line in lines) and not any(
        re.match(r'FAIL|SKIP', line) for line in lines
    ), 'The requested production scan contract executes and passes without skipping: ' + '\n'.join(
        lines
    )
