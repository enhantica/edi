"""Observe every new scan contract in one real rendering session."""

import json
import os
import re
import signal
import subprocess
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest

from tests.fixtures.fast_chart_redraws.rendering import native_arguments

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
    ]
    + [
        *[
            f'test_background_to_experiment_ramp:{mode}-{theme}'
            for mode in ('map',)
            for theme in ('light', 'dark')
        ],
        'test_map_key_and_image_use_frozen_interior_samples',
        'test_map_interpolates_between_neighboring_patterns',
        'test_selected_map_label_is_always_drawn',
        'test_antialiased_ink_observer',
        'test_private_copy_required',
        'test_map_interpolation_default',
        *[
            f'test_map_reverse_and_key:{direction}-{theme}'
            for direction in ('forward', 'reversed')
            for theme in ('light', 'dark')
        ],
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


def reverse_parts():
    maps = json.loads((ROOT / 'tests/fixtures/scan_views/offered.json').read_text())['maps']
    palettes = json.loads((ROOT / 'tests/fixtures/approved_palettes/colours.json').read_text())[
        'palettes'
    ]
    return range((len(maps) + len(palettes) + 11) // 12)


def case_variants(case):
    if case.startswith('test_map_reverse_and_key:'):
        count = len(reverse_parts())
    elif case.startswith('test_offered_maps_are_readable_in_both_themes:'):
        maps = json.loads((ROOT / 'tests/fixtures/scan_views/offered.json').read_text())['maps']
        count = (len(maps) + 6) // 7
    else:
        return [case]
    return [case + f'-part{part}' for part in range(count)]


@pytest.fixture(scope='module')
def scan_receipt(request):
    binary = Path(os.environ.get('EDI_APP_TEST_RUNNER', ROOT / 'build/app/app/edi_app_tests'))
    assert binary.is_file(), 'Scan content acceptance requires the actual native test host'
    binary = Path(native_arguments([binary])[0])
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
        cases[index : index + size]
        for function, cases in groups.items()
        for size in (
            1
            if function
            in {'test_offered_maps_are_readable_in_both_themes', 'test_map_reverse_and_key'}
            else 2,
        )
        for index in range(0, len(cases), size)
    ]
    batches = [
        [variant] if len(cases) == 1 else cases
        for cases in batches
        for variant in (case_variants(cases[0]) if len(cases) == 1 else [None])
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
                original = re.sub(r'-part\d+$', '', case)
                previous_status, previous_output = receipts.get(original, (0, ''))
                receipts[original] = previous_status or status, previous_output + output
    return receipts


@pytest.mark.parametrize('case', CASES)
def test_scan_view_content(scan_receipt, case):
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
    variants = case_variants(case)
    for variant in variants:
        name, _, tag = variant.partition(':')
        witness = f'::ScanViewContent::{name}({tag})'
        lines = [line for line in output.splitlines() if witness in line]
        assert any(line.startswith('PASS ') for line in lines) and not any(
            re.match(r'FAIL|SKIP', line) for line in lines
        ), (
            'Every requested map part and production scan contract executes without skipping: '
            + '\n'.join(lines)
            + '\nNative failure receipt:\n'
            + output
        )
