"""One native observation of Analysis filters with and without measured data."""

import os
import re
import subprocess
from pathlib import Path

import pytest

from tests.integration.app.test_onboarding_views import (
    test_production_onboarding_control as run_host,
)

ROOT = Path(__file__).resolve().parents[3]


@pytest.fixture(scope='module')
def availability_observation():
    # Both modes share one real window and project: the second loads measurements
    # into the initially simulated experiment. Record the whole host cost as a module cost,
    # as for the live Extra-table census, rather than charging an arbitrary mode.
    runner = Path(os.environ.get('EDI_APP_TEST_RUNNER', ROOT / 'build/app/app/edi_app_tests'))
    assert runner.is_file(), 'Analysis filter acceptance requires the actual Qt application host'
    result = subprocess.run(
        [
            str(runner),
            '-input',
            str(ROOT / 'tests/unit/app/tst_simulation_parameter_filters.qml'),
            '-o',
            '-,txt',
            'SimulationParameterFilters::test_filters_remain_usable_without_measurements',
        ],
        capture_output=True,
        text=True,
        check=False,
        timeout=60,
        env={**os.environ, 'QT_QPA_PLATFORM': 'offscreen', 'QT_QUICK_BACKEND': 'software'},
    )
    return result.stdout + result.stderr


@pytest.mark.parametrize('mode', ['simulation', 'measured'])
def test_analysis_filter_availability_and_real_selection(availability_observation, mode):
    assert not re.search(
        r'^(?:FAIL!|SKIP)\s*:.*::(?:initTestCase|init|cleanup|cleanupTestCase)\(',
        availability_observation,
        re.MULTILINE,
    ), 'The actual filter host starts and cleans up every mode: ' + availability_observation
    receipt = (
        'SimulationParameterFilters::test_filters_remain_usable_without_measurements(' + mode + ')'
    )
    assert re.search(
        r'^PASS\s*:.*' + re.escape(receipt) + r'\s*$', availability_observation, re.MULTILINE
    ), (
        'The actual parameter filters satisfy their measured-data availability requirement: '
        + availability_observation
    )


def test_measured_data_transition_keeps_analysis_filters_visible():
    run_host('tst_measured_data_controls.qml', 'MeasuredDataControls', 'analysis_transition')
