"""Exercise reciprocal-axis single-crystal charts using independently authored references."""

import os
from pathlib import Path

import pytest

from tests.fixtures.fast_chart_redraws.rendering import capture, native_arguments

ROOT = Path(__file__).resolve().parents[3]
CASES = [
    *[
        f'test_constrained_moment_nuclear_counterfactual:{mode}-{axis}-{quantity}'
        for mode in ('fixed', 'expression', 'alias')
        for axis in ('q', 'sine')
        for quantity in ('f2', 'f')
    ],
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
        f'test_simulation_has_calculated_bars_and_ticks_without_measurements:{kind}'
        for kind in ('nuclear', 'magnetic')
    ],
    *[
        f'test_measured_points_and_uncertainties_in_both_modes:{axis}-{quantity}-{mode}'
        for axis in ('q', 'sine')
        for quantity in ('f2', 'f')
        for mode in ('bars', 'lines')
    ],
    *[f'test_bar_width_and_thin_line_zoom_invariants:{axis}' for axis in ('q', 'sine')],
    *[
        f'test_comparison_quantities_remain_separate_from_pattern:{kind}'
        for kind in ('nuclear', 'magnetic')
    ],
]


@pytest.fixture(scope='module')
def native_host():
    binary = Path(os.environ.get('EDI_APP_TEST_RUNNER', ROOT / 'build/app/app/edi_app_tests'))
    assert binary.is_file(), 'Single-crystal acceptance requires the actual native Qt host'
    # Freezing and hashing the shared host is module setup, outside individual GUI workflows.
    native_arguments([binary])
    return binary


@pytest.mark.parametrize('case', CASES)
def test_single_crystal_pattern_from_independent_references(case, native_host):
    status, output = capture(
        [
            native_host,
            '-input',
            ROOT / 'tests/unit/app/tst_single_crystal_pattern.qml',
            'SingleCrystalPattern::' + case,
        ],
        env={**os.environ, 'OMP_NUM_THREADS': '1', 'OPENBLAS_NUM_THREADS': '1'},
    )
    assert 'Could not find the following test functions' not in output, (
        'The selected native single-crystal function must exist before product behavior is judged'
    )
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
