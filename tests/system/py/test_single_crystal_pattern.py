"""Exercise reciprocal-axis single-crystal charts using independently authored references."""

import os
from pathlib import Path

import pytest

from tests.fixtures.fast_chart_redraws.rendering import capture

ROOT = Path(__file__).resolve().parents[3]
CASES = [
    'test_powder_comparison_has_one_point_per_data_row_and_identity_line',
    'test_creating_single_crystal_experiment_immediately_draws_simulated_bars',
    *[
        f'test_independent_reflections_and_stacked_contributions:{kind}-{axis}-{quantity}'
        for kind in ('nuclear', 'magnetic')
        for axis in ('q', 'sine')
        for quantity in ('f2', 'f')
    ],
    *[f'test_legend_hides_real_contributions:{kind}' for kind in ('nuclear', 'magnetic')],
    *[
        f'test_simulation_has_calculated_bars_and_ticks_without_measured_data:{kind}'
        for kind in ('nuclear', 'magnetic')
    ],
    *[
        f'test_measured_points_and_uncertainties_in_both_modes:{axis}-{quantity}'
        for axis in ('q', 'sine')
        for quantity in ('f2', 'f')
    ],
    *[f'test_bar_width_and_thin_line_zoom_invariants:{axis}' for axis in ('q', 'sine')],
    *[
        f'test_comparison_quantities_remain_separate_from_pattern:{kind}'
        for kind in ('nuclear', 'magnetic')
    ],
]


@pytest.mark.parametrize('case', CASES)
def test_single_crystal_pattern_from_independent_references(case):
    binary = Path(os.environ.get('EDI_APP_TEST_RUNNER', ROOT / 'build/app/app/edi_app_tests'))
    assert binary.is_file(), 'Single-crystal pattern acceptance requires the actual native Qt host'
    status, output = capture([
        binary,
        '-input',
        ROOT / 'tests/unit/app/tst_single_crystal_pattern.qml',
        'SingleCrystalPattern::' + case,
    ])
    function, _, tag = case.partition(':')
    assert status == 0, (
        'The actual single-crystal chart satisfies its physical contract: ' + output
    )
    expected = (
        f'SingleCrystalPattern::{function}({tag})'
        if tag
        else f'SingleCrystalPattern::{function}()'
    )
    assert expected in output and '0 failed' in output, (
        'The requested single-crystal contract executes rather than an empty native selection'
    )
    assert 'SKIP' not in output, 'Every reciprocal-axis single-crystal contract executes'
