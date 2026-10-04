"""unit coverage for the diffraction-lib-compatible data-path factory."""

from __future__ import annotations

from pathlib import Path

import edi
import pytest


def _write_rows(tmp_path: Path, name: str, rows: str) -> Path:
    path = tmp_path / name
    path.write_text(rows, encoding='utf-8')
    return path


def test_c11_t48_data_path_factory_preserves_columns_and_sigma_rules(
    tmp_path: Path,
) -> None:
    three_columns = _write_rows(
        tmp_path,
        'constant-wavelength.dat',
        '17.5 9.0 0.00001\n23.75 16.0 2.5\n',
    )
    constant_wavelength = edi.ExperimentFactory.from_data_path(
        name='cw-bank',
        data_path=three_columns,
        beam_mode='constant wavelength',
    )
    assert isinstance(constant_wavelength.data, edi.PdCwlData), (
        ' I17: the constant-wavelength token must select angular measured data'
    )
    assert constant_wavelength.name == 'cw-bank', (
        ' I17: the data-path factory must preserve the requested experiment name'
    )
    assert constant_wavelength.data.two_theta == [17.5, 23.75], (
        ' I17: the data-path factory must preserve angular coordinate values'
    )
    assert constant_wavelength.data.intensity_meas == [9.0, 16.0], (
        ' I17: the data-path factory must preserve measured intensity values'
    )
    assert constant_wavelength.data.intensity_meas_su == [1.0, 2.5], (
        'the upstream ASCII contract replaces only sigma values below 1e-4'
    )

    two_columns = _write_rows(
        tmp_path,
        'time-of-flight.dat',
        '1200.0 4.0\n2450.0 12.25\n',
    )
    time_of_flight = edi.ExperimentFactory.from_data_path(
        name='tof-bank',
        data_path=two_columns,
        beam_mode='time-of-flight',
    )
    assert isinstance(time_of_flight.data, edi.PdTofData), (
        ' I17: the time-of-flight token must select TOF measured data'
    )
    assert time_of_flight.data.time_of_flight == [1200.0, 2450.0], (
        ' I17: the data-path factory must preserve time-of-flight coordinate values'
    )
    assert time_of_flight.data.intensity_meas == [4.0, 12.25], (
        ' I17: the data-path factory must preserve measured intensity values'
    )
    assert time_of_flight.data.intensity_meas_su == [2.0, 3.5], (
        'the two-column contract derives sigma as the closed-form square root of intensity'
    )

    invalid_inputs = (
        ('one-column.dat', '1.0\n2.0\n', r'expected 2 or 3 columns'),
        ('negative.dat', '1.0 -4.0\n', r'cannot derive sqrt\(y\)'),
        ('non-finite.dat', '1.0 4.0 nan\n', r'non-finite value'),
    )
    for name, rows, message in invalid_inputs:
        path = _write_rows(tmp_path, name, rows)
        with pytest.raises(ValueError, match=message):
            edi.ExperimentFactory.from_data_path(name='invalid', data_path=path)
