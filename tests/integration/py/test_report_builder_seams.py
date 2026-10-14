"""Report capture/filter seams at closed-form project inputs."""

import json
import math

import edi
import pytest

from tests.integration.py.test_report_iucr_persistence import project


def built(source):
    loaded = edi.Project.load(source)
    assert hasattr(loaded, 'report'), 'The planned report builder must be available for this seam'
    return loaded


def test_cw_d_axis_uses_bragg_law_and_ascending_points(tmp_path):
    source = project(tmp_path, '4()', None)
    experiment = source / 'experiments/bank.edi'
    text = experiment.read_text().replace(
        '_instrument.setup_wavelength 1.54', '_instrument.setup_wavelength 1.87'
    )
    text = text.replace('40 5.0484848484848488 1', '30 5.0484848484848488 1')
    experiment.write_text(text)
    loaded = built(source)
    loaded.calculate()
    loaded.report.x_axis = 'd_spacing'
    model = json.loads(loaded.report.model().to_json())
    pattern = model['experiments'][0]['pattern']
    assert pattern['x']['title'] == 'd (Å)', 'The report axis must name d spacing and its unit'
    measured = next(series for series in pattern['series'] if series['id'] == 'meas')
    positions = [x for x in measured['x'] if x is not None]
    assert positions == sorted(positions), (
        'A decreasing CW d axis must become ascending report points'
    )
    expected = 1.87 / (2 * math.sin(math.radians(15)))
    assert positions[-1] == pytest.approx(expected, rel=2e-15), (
        'At wavelength 1.87 and two-theta 30 the report d coordinate must equal Bragg law'
    )


@pytest.mark.parametrize(('level', 'count'), [(None, 5), (0.9, 3), (1.0, 0)])
def test_core_correlation_filter_keeps_top_five_and_threshold_pairs(level, count, tmp_path):
    source = project(tmp_path, '4()', None)
    analysis = source / 'analysis/analysis.edi'
    metadata = """
_fit_result.result_kind deterministic
_fit_result.success true
_fit_result.message done
_fit_result.iterations 1
_fit_result.fitting_time 0
_fit_result.reduced_chi_square 1
_fit_result.objective_name chi_square
_fit_result.objective_value 3
_fit_result.n_data_points 9
_fit_result.n_parameters 6
_fit_result.n_free_parameters 6
_fit_result.degrees_of_freedom 3
_fit_result.covariance_available true
_fit_result.exit_reason done
_fit_result.prof_wr_factor 0.1
_fit_result.profile_function cwl-tch-pseudo-voigt
_fit_result.background_function line-segment
_fit_result.descent ladder
loop_
_fit_parameter_correlation.id
_fit_parameter_correlation.source_kind
_fit_parameter_correlation.parameter_unique_name_i
_fit_parameter_correlation.parameter_unique_name_j
_fit_parameter_correlation.correlation
"""
    pairs = [
        ('pA', 'pB', 0.99),
        ('pA', 'pC', 0.97),
        ('pB', 'pC', 0.95),
        ('pD', 'pE', 0.82),
        ('pD', 'pF', 0.81),
        ('pE', 'pF', 0.40),
    ]
    for index, (left, right, value) in enumerate(pairs):
        metadata += (
            f'{index + 1} deterministic bank.background.{left}.intensity '
            f'bank.background.{right}.intensity {value}\n'
        )
    analysis.write_text(analysis.read_text() + metadata)
    loaded = built(source)
    loaded.report.correlation_threshold = level
    model = json.loads(loaded.report.model().to_json())
    correlations = model['correlations']
    labels = correlations['labels'] if correlations else []
    assert len(labels) == count, (
        'The report must use the shared filter: five strongest parameters by default, '
        'the three strong parameters above 0.9, and no pairs at level one'
    )
    if level == 0.9:
        assert {label.split('.')[-2] for label in labels} == {'pA', 'pB', 'pC'}, (
            'The filter must select the declared strong trio, independent of input order'
        )


def test_scan_evolution_keeps_extracted_x_numeric_su_and_core_text(tmp_path):
    source = project(tmp_path, '4()', None)
    analysis = source / 'analysis/analysis.edi'
    text = analysis.read_text().replace(
        '_fitting_mode.type single', '_fitting_mode.type sequential'
    )
    text += '\n_sequential_fit.data_dir scan\n_sequential_fit.file_pattern *.dat\n'
    text += '_sequential_fit.template_file point.dat\n'
    text += (
        'loop_\n_sequential_fit_extract.id\n_sequential_fit_extract.target\n'
        '_sequential_fit_extract.pattern\n_sequential_fit_extract.required\n'
        'T diffrn.ambient_temperature ^TEMP\\s+([0-9.]+) true\n'
    )
    analysis.write_text(text)
    directory = source / 'scan'
    directory.mkdir()
    (directory / 'point.dat').write_text('TEMP 52.345\n40 5 1\n44 6 1\n')
    (source / 'analysis/results.csv').write_text(
        'file_path,fit_result.reduced_chi_square,fit_result.success,fit_result.iterations,'
        'diffrn.ambient_temperature,bank.background.pA.intensity,'
        'bank.background.pA.intensity.uncertainty\n'
        'scan/point.dat,1,True,1,52.345,10.30925,0.00157\n'
    )
    loaded = built(source)
    model = json.loads(loaded.report.model().to_json())
    series = model.get('evolution')
    assert isinstance(series, list) and series, (
        'A scan report exposes a nonempty root evolution list of parameter series; '
        f'root keys={sorted(model)}, evolution={series!r}'
    )
    assert all(isinstance(row, dict) for row in series), (
        f'Root evolution entries are named parameter objects; evolution={series!r}'
    )
    name = 'bank.background.pA.intensity'
    selected = [row for row in series if row.get('name') == name]
    assert len(selected) == 1 and isinstance(selected[0].get('points'), list), (
        'Evolution exposes one named parameter series with a points list; '
        f'wanted={name!r}, evolution={series!r}'
    )
    points = selected[0]['points']
    assert all(
        isinstance(point, dict) and {'x', 'y', 'su', 'text'} <= point.keys() for point in points
    ), f'Each evolution point exposes x, y, su and text; parameter={name!r}, points={points!r}'
    matching = [
        point
        for point in points
        if (point['x'], point['y'], point['su']) == (52.345, 10.30925, 0.00157)
    ]
    assert matching, (
        'Evolution retains extracted T=52.345, value=10.30925 and su=0.00157 '
        f'in its named series; parameter={name!r}, points={points!r}'
    )
    assert all(point['text'] == '10.3093(16)' for point in matching), (
        'The same numeric evolution point carries the core IUCr spelling 10.3093(16); '
        f'parameter={name!r}, matching points={matching!r}'
    )


def test_tof_d_axis_uses_linear_calibration_with_nonzero_offset(tmp_path):
    source = project(tmp_path, '4()', None)
    experiment = source / 'experiments/bank.edi'
    experiment.write_text("""data_bank
_edi.schema_version 3
_calculator.type crysta
_experiment_type.sample_form powder
_experiment_type.beam_mode time-of-flight
_experiment_type.radiation_probe neutron
_experiment_type.scattering_type bragg
_peak.type tof-jorgensen
_peak.rise_alpha_0 0.1
_peak.rise_alpha_1 0.2
_peak.decay_beta_0 0.01
_peak.decay_beta_1 0.02
_peak.broad_gauss_sigma_0 0
_peak.broad_gauss_sigma_1 0
_peak.broad_gauss_sigma_2 15
_peak.broad_gauss_size 0
_peak.broad_gauss_strain 0
_peak.cutoff_fwhm 20
_instrument.setup_twotheta_bank 152.827
_instrument.calib_d_to_tof_offset 100
_instrument.calib_d_to_tof_linear 5000
_instrument.calib_d_to_tof_quadratic 0
_instrument.calib_d_to_tof_reciprocal 0
_absorption.type none
loop_
_linked_structure.structure_id
_linked_structure.scale
phase 0.7
_background.type line-segment
loop_
_background.id
_background.position
_background.intensity
pA 19000 4()
pB 31000 5()
loop_
_data.time_of_flight
_data.intensity_meas
_data.intensity_meas_su
20000 10 1
25000 11 1
30000 12 1
""")
    loaded = built(source)
    loaded.calculate()
    loaded.report.x_axis = 'd_spacing'
    model = json.loads(loaded.report.model().to_json())
    pattern = model['experiments'][0]['pattern']
    measured = next(series for series in pattern['series'] if series['id'] == 'meas')
    positions = [x for x in measured['x'] if x is not None]
    assert positions == pytest.approx([3.98, 4.98, 5.98], rel=2e-15), (
        'At TOF 20000, 25000 and 30000, zero 100 and DIFC 5000, DIFA zero gives (TOF-zero)/DIFC'
    )
