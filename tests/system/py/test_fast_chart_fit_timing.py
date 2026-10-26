"""Gate each chart tab's actual catch-up versus Adaptive scan overhead."""

import os

import pytest

from tests.fixtures.fast_chart_redraws.measure_fit import measure_fit_tabs


@pytest.fixture(scope='module')
def fit_timings(tmp_path_factory):
    return measure_fit_tabs(
        os.environ.get('EDI_CHART_FIT_OUTPUT') or tmp_path_factory.mktemp('chart-fit-timing')
    )


@pytest.mark.parametrize('tab', ['pattern', 'stacked'])
def test_every_pattern_overhead_on_each_actual_chart_tab(fit_timings, tab):
    comparison = fit_timings['comparisons'][tab]
    assert comparison['tab'] == tab, (
        'A fit timing verdict must retain its actual visible chart tab'
    )
    assert comparison['within_five_percent'], (
        'Display catches up must stay within five percent of Adaptive on each tab/backend: '
        + str(comparison)
    )
