"""Plain-data import compared with independently constructed rows."""

from __future__ import annotations

import importlib
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
FIXTURE = ROOT / 'tests/fixtures/plain_data'
CASES = json.loads((FIXTURE / 'cases.json').read_text())


def observed(experiment, beam):
    data = experiment.data
    axis = data.time_of_flight if beam == 'tof' else data.two_theta
    return [
        list(row) for row in zip(axis, data.intensity_meas, data.intensity_meas_su, strict=True)
    ]


def check_rows(actual, expected):
    assert actual == expected, (
        'Plain-data import: retain exactly the hand-constructed rows, first duplicates, '
        'sorted x and independently computed uncertainties'
    )


@pytest.mark.parametrize('case', sorted(CASES))
def test_plain_data_rows_and_named_upstream_differences(case):
    specification = CASES[case]
    library = importlib.import_module('edi')
    experiment = library.ExperimentFactory.from_data_path(
        name='pattern',
        data_path=str(FIXTURE / case / specification['file']),
        beam_mode='time-of-flight' if specification['beam'] == 'tof' else 'constant wavelength',
    )
    expected_mode = 'TIME_OF_FLIGHT' if specification['beam'] == 'tof' else 'CONSTANT_WAVELENGTH'
    assert expected_mode in str(experiment.experiment_type.beam_mode), (
        'Plain-data import: x follows the requested CWL degrees or TOF microseconds beam mode'
    )
    check_rows(observed(experiment, specification['beam']), specification['rows'])


def test_nonpositive_retention_escape_is_rejected():
    specification = CASES['cwl/nonpositive']
    actual = [*specification['rows'], [18.0, 0.0, 1.0]]
    with pytest.raises(AssertionError, match='Plain-data import'):
        check_rows(actual, specification['rows'])
