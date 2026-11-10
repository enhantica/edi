"""Actual app mode selection, isolated values/covariance and named dataset quality."""

import json
import os
import subprocess
from pathlib import Path

import pytest

from tests.fixtures.independent_experiments.reference import BANKS, optimum

ROOT = Path(__file__).resolve().parents[3]


@pytest.fixture(scope='module')
def app_observation():
    binary = Path(os.environ.get('EDI_APP_TEST_RUNNER', ROOT / 'build/app/app/edi_app_tests'))
    assert binary.is_file(), 'Independent experiment gates require the real app host'
    result = subprocess.run(
        [
            str(binary),
            '-input',
            str(ROOT / 'tests/fixtures/independent_experiments/observe.qml'),
            '-o',
            '-,txt',
        ],
        capture_output=True,
        text=True,
        check=False,
        timeout=35,
        env={**os.environ, 'QT_QPA_PLATFORM': 'offscreen', 'QT_QUICK_BACKEND': 'software'},
    )
    output = result.stdout + result.stderr
    assert result.returncode == 0 and '0 failed' in output and 'SKIP' not in output, (
        'The real app completes its independent mode choice and scientific fit: ' + output
    )
    prefix = 'INDEPENDENT_EXPERIMENTS_APP '
    rows = [line.split(prefix, 1)[1] for line in output.splitlines() if prefix in line]
    assert len(rows) == 1, 'The actual app publishes one complete non-scan independent observation'
    return json.loads(rows[0])


@pytest.mark.parametrize('name', BANKS)
def test_actual_app_independent_value_and_su_match_each_dataset(name, app_observation):
    phase = BANKS[name]['phase']
    rows = [row for row in app_observation['parameters'] if phase in row['path']]
    assert len(rows) == 1, 'The app identifies each repeated atom ID by its owning structure'
    expected = optimum([name])
    assert rows[0]['value'] == pytest.approx(expected['value'], rel=2e-5, abs=1e-9), (
        'The app independent fit reaches the dataset-specific weighted optimum'
    )
    assert rows[0]['su'] == pytest.approx(expected['su'], rel=3e-4, abs=1e-9), (
        'The app independent fit keeps dataset-specific covariance, not a pooled uncertainty'
    )


@pytest.mark.parametrize('name', BANKS)
def test_actual_app_keeps_each_datasets_own_agreement(name, app_observation):
    rows = [row for row in app_observation['quality'] if row['name'] == name]
    assert len(rows) == 1, 'The app reports one quality row for each independent dataset'
    assert rows[0]['rwp'] == pytest.approx(optimum([name])['rwp'], abs=5.1e-5), (
        'The displayed per-dataset Rwp retains the report table precision in fractional units'
    )
