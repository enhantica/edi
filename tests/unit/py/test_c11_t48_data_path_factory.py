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


@pytest.mark.parametrize(
    'beam_mode', ['constant wavelength', 'time-of-flight'], ids=['cwl', 'tof']
)
@pytest.mark.parametrize(
    ('filename', 'rows'),
    [
        ('one-column.dat', '1.0\n2.0\n'),
        ('negative.dat', '1.0 -4.0\n'),
        ('non-finite.dat', '1.0 4.0 nan\n'),
    ],
    ids=['malformed-columns', 'nonpositive-bragg', 'nonfinite-sigma'],
)
def test_data_path_factory_refuses_empty_result_after_filtering(
    tmp_path, beam_mode, filename, rows
):
    # The plain-data reader filters unusable rows, then refuses one empty result.
    path = _write_rows(tmp_path, filename, rows)
    with pytest.raises(ValueError, match='holds no data rows'):
        edi.ExperimentFactory.from_data_path(name='invalid', data_path=path, beam_mode=beam_mode)


@pytest.mark.parametrize(
    'beam_mode', ['constant wavelength', 'time-of-flight'], ids=['cwl', 'tof']
)
def test_data_path_factory_keeps_good_rows_among_all_filtered_classes(tmp_path, beam_mode):
    path = _write_rows(
        tmp_path,
        'filtered.dat',
        '11 9 3\nheader\n2\n7 -4 2\n8 0 2\n10 4 nan\n9 16 4\n11 25 5\n',
    )
    experiment = edi.ExperimentFactory.from_data_path(
        name='filtered-bank', data_path=path, beam_mode=beam_mode
    )
    assert experiment.name == 'filtered-bank', (
        'Plain-data factory: a mixed usable/unusable file preserves its independently chosen name'
    )
    assert list(experiment.data.axis()) == [9.0, 11.0], (
        'Plain-data factory: filter malformed, nonpositive and nonfinite rows; '
        'sort x and keep the first duplicate'
    )
    assert experiment.data.intensity_meas == [16.0, 9.0], (
        'Plain-data factory: retained intensities belong to the first surviving rows at each x'
    )
    assert experiment.data.intensity_meas_su == [4.0, 3.0], (
        'Plain-data factory: sorting and filtering preserve the supplied nontrivial uncertainties'
    )
