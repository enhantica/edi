"""The actual legend must draw series geometry and use the table's element icon."""

import os
import subprocess

from tests.integration.app.test_e04_t1_projects import APP_TESTS, runner


def test_actual_legend_marks_preserve_geometry_and_element_parity():
    run = subprocess.run(
        [str(runner()), '-input', str(APP_TESTS / 'tst_legend_marks.qml'), '-o', '-,txt'],
        env={**os.environ, 'QT_QPA_PLATFORM': 'offscreen', 'QT_QUICK_BACKEND': 'software'},
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )
    output = run.stdout + run.stderr
    assert run.returncode == 0, (
        'Actual series geometry and element-icon parity must hold: ' + output
    )
    for case in ('jmol', 'vesta'):
        assert (
            f'PASS   : edi_app::LegendMarkParity::test_element_icon_and_colour_match_table({case})'
        ) in output, 'Each colour scheme must execute the real legend/table parity witness'
    assert (
        'PASS   : edi_app::LegendMarkParity::test_pattern_marks_are_drawn_with_series_widths()'
    ) in output, (
        'The runtime witness must exercise both horizontal series marks and vertical ticks'
    )
