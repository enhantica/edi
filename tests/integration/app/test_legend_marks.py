"""The actual legend must draw series geometry and use the table's element icon."""

import os
import subprocess

import pytest

from tests.fixtures.element_contrast.legacy_receipts import require_readable_elements

from tests.integration.app.test_e04_t1_projects import APP_TESTS, runner


@pytest.fixture(scope='module')
def legend_run():
    # One host supplies the independent scheme and geometry receipts. Its complete
    # launch cost is retained once by the canonical module-cost instrument.
    result = subprocess.run(
        [str(runner()), '-input', str(APP_TESTS / 'tst_legend_marks.qml'), '-o', '-,txt'],
        env={**os.environ, 'QT_QPA_PLATFORM': 'offscreen', 'QT_QUICK_BACKEND': 'software'},
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )

    if result.returncode == 0:
        require_readable_elements(result.stdout + result.stderr)
    return result


def test_actual_legend_marks_preserve_geometry_and_element_parity(legend_run):
    assert legend_run.returncode == 0, (
        'Actual series geometry and element-icon parity must hold: '
        + legend_run.stdout
        + legend_run.stderr
    )


@pytest.mark.parametrize(
    'case',
    [
        'test_element_icon_and_colour_match_table(jmol)',
        'test_element_icon_and_colour_match_table(vesta)',
        'test_pattern_marks_are_drawn_with_series_widths()',
    ],
    ids=['jmol', 'vesta', 'pattern'],
)
def test_each_legend_boundary_executes_in_the_actual_host(legend_run, case):
    assert f'PASS   : edi_app::LegendMarkParity::{case}' in legend_run.stdout, (
        'Every selected element scheme and drawn series geometry must execute in the real host'
    )
