"""Actual Analysis category filters preserve all loop parameters and both variability states."""

import os
import re
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]


@pytest.mark.parametrize(
    ('kind', 'suffix'),
    [
        ('line-segment', 'points'),
        ('polynomial', 'polynomial'),
        ('chebyshev', 'chebyshev'),
    ],
)
@pytest.mark.parametrize('chunk', [0, 1, 2])
@pytest.mark.parametrize('id_style', ['named', 'numeric'])
def test_every_offered_category_retains_its_complete_real_loop_rows(kind, suffix, id_style, chunk):
    runner = Path(os.environ.get('EDI_APP_TEST_RUNNER', ROOT / 'build/app/app/edi_app_tests'))
    assert runner.is_file(), 'Loop-filter acceptance requires the actual production Qt host'
    case = 'ParameterLoopFilters::test_' + suffix + ('_numeric' if id_style == 'numeric' else '')
    case += '_' + str(chunk)
    result = subprocess.run(
        [
            str(runner),
            '-input',
            str(ROOT / 'tests/unit/app/tst_parameter_loop_filters.qml'),
            case,
            '-o',
            '-,txt',
        ],
        env={**os.environ, 'QT_QPA_PLATFORM': 'offscreen', 'QT_QUICK_BACKEND': 'software'},
        capture_output=True,
        text=True,
        # Process scheduling headroom; the measured system tier stays five seconds.
        timeout=15.0,
        check=False,
    )
    output = result.stdout + result.stderr
    assert result.returncode == 0 and f'PASS   : edi_app::{case}()' in output, (
        'Analysis Main must filter every actual loop category to exactly its All-categories '
        'row identities for All, Free and Fixed, with the same advertised count: ' + output
    )
    receipt = re.search(
        r'PARAMETER_LOOP_FILTERS '
        + kind
        + r' groups=(\d+) background=(\d+) variability=all,free,fixed ids='
        + id_style,
        output,
    )
    assert receipt is not None, 'Each typed background must finish all real category-filter checks'
    assert 'chunk=' + str(chunk) + ' checked=' in output, (
        'Every bounded case must complete its exact partition of the offered category inventory'
    )
    assert int(receipt[2]) == (
        12 if kind == 'line-segment' else 6 if kind == 'polynomial' else 8
    ), 'Background filtering must retain every height or coefficient, including later rows'


@pytest.mark.parametrize(
    ('kind', 'suffix'),
    [
        ('line-segment', 'points'),
        ('polynomial', 'polynomial'),
        ('chebyshev', 'chebyshev'),
    ],
)
@pytest.mark.parametrize('route', ['manual', 'auto'])
def test_background_filter_keeps_every_row_after_estimate_replaces_the_open_table(
    kind, suffix, route
):
    runner = Path(os.environ.get('EDI_APP_TEST_RUNNER', ROOT / 'build/app/app/edi_app_tests'))
    assert runner.is_file(), 'Replacement-filter acceptance requires the production Qt host'
    case = 'ParameterLoopFilters::test_' + ('auto_' if route == 'auto' else 'hot_') + suffix
    result = subprocess.run(
        [
            str(runner),
            '-input',
            str(ROOT / 'tests/unit/app/tst_parameter_loop_filters.qml'),
            case,
            '-o',
            '-,txt',
        ],
        env={**os.environ, 'QT_QPA_PLATFORM': 'offscreen', 'QT_QUICK_BACKEND': 'software'},
        capture_output=True,
        text=True,
        # Process scheduling headroom; the measured system tier stays five seconds.
        timeout=15.0,
        check=False,
    )
    output = result.stdout + result.stderr
    assert result.returncode == 0 and f'PASS   : edi_app::{case}()' in output, (
        'An already-open Analysis filter must keep every current background parameter after '
        'Estimate replaces the actual example rows, in All, Free and Fixed states: ' + output
    )
    assert re.search(
        r'PARAMETER_HOT_FILTER ' + kind + r' count=\d+ variability=all,free,fixed route=' + route,
        output,
    ), 'Every real background type must finish the post-estimate filter replacement workflow'
