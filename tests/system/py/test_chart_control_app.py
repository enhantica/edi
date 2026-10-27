"""Run the colour, persistence and toolbar witnesses through the real application."""

import os
import re
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
CASES = [
    'test_preferences_strip_uses_shared_project_colours',
    *[
        'test_common_pool_and_earth_reservation:' + name
        for name in ('Earth', 'Classic', 'Soft', 'Natural', 'Colour-blind safe')
    ],
    'test_light_figure_is_independent_of_app_theme',
    'test_element_two_to_one_and_scheme_titles',
    'test_element_scheme_names',
    *[
        'test_saved_html_and_pdf_are_light:' + name
        for name in ('Earth', 'Classic', 'Soft', 'Natural', 'Colour-blind safe')
    ],
    'test_map_direction_default_and_theme_following',
    *[f'test_spacing_geometry:{count}-{step}' for count in (1, 3, 162) for step in range(5)],
    'test_spacing_survives_project_reopen',
    'test_subtraction_uses_set_unfitted_background:Stacked',
    'test_subtraction_uses_set_unfitted_background:Map',
    'test_pattern_subtracts_each_measured_point',
    'test_no_background_disables_subtraction',
    'test_short_legend_and_selection',
]


@pytest.fixture(scope='module')
def app_results():
    binary = Path(os.environ.get('EDI_APP_TEST_RUNNER', ROOT / 'build/app/app/edi_app_tests'))
    assert binary.is_file(), (
        'The chart acceptance actor requires the current checkout native app test host'
    )
    result = subprocess.run(
        [
            'bash',
            str(ROOT / 'tests/fixtures/scan_views/run.sh'),
            str(binary),
            '-input',
            str(ROOT / 'tests/unit/app/tst_chart_controls.qml'),
            '-o',
            '-,txt',
        ],
        capture_output=True,
        text=True,
        check=False,
        timeout=120,
    )
    output = result.stdout + result.stderr
    print(output)
    assert re.search(r'Totals:.*passed', output), (
        'The actual app actor must run to a QtTest summary rather than fail during startup'
    )
    return output


@pytest.mark.parametrize('case', CASES)
def test_real_chart_control_contract(app_results, case):
    function, _, data = case.partition(':')
    suffix = re.escape(data) if data else ''
    assert re.search(
        r'PASS\s*:\s*.*ChartControls::' + re.escape(function) + r'\(' + suffix + r'\)', app_results
    ), 'The real app must satisfy its chart-control witness: ' + case
