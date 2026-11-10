"""Hidden  gates for the public object vocabulary and typed axes."""

from __future__ import annotations

import edi
import pytest
from c11_t40_helpers import descriptor, make_schema_2_case, oracle


def test_c11_t40_diffraction_lib_oracle_is_the_reviewed_source_pin() -> None:
    reference = oracle()
    assert reference['source']['commit'] == '0ffba46f4b501066a73e77f00fa29fa13519b417', (
        'the vocabulary oracle must retain the reviewed diffraction-lib source commit'
    )
    assert reference['source']['repo'] == 'https://github.com/easyscience/diffraction-lib'
    assert descriptor('peak', 'broad_gauss_size')['edi_names'] == ['_peak.broad_gauss_size']
    assert descriptor('atom_sites', 'adp_iso')['cif_names'] == [
        '_atom_site.B_iso_or_equiv',
        '_atom_site.U_iso_or_equiv',
    ]
    wavelength = descriptor('instrument', 'setup_wavelength')
    assert wavelength['internal_name'] == 'wavelength'
    assert wavelength['edi_names'] == ['_instrument.setup_wavelength']
    assert reference['enums']['BeamModeEnum'] == {
        'CONSTANT_WAVELENGTH': 'constant wavelength',
        'TIME_OF_FLIGHT': 'time-of-flight',
    }


def test_e09_t54_instrument_spelling_uses_properties_not_internal_labels() -> None:
    divergences = {
        row['attribute']: row['internal_name']
        for row in oracle()['descriptors']
        if row['surface'] == 'instrument' and row['attribute'] != row['internal_name']
    }
    assert divergences == {
        'calib_d_to_tof_linear': 'd_to_tof_linear',
        'calib_d_to_tof_offset': 'd_to_tof_offset',
        'calib_d_to_tof_quadratic': 'd_to_tof_quadratic',
        'calib_d_to_tof_reciprocal': 'd_to_tof_reciprocal',
        'calib_sample_displacement': 'sample_displacement',
        'calib_sample_transparency': 'sample_transparency',
        'calib_twotheta_offset': 'twotheta_offset',
        'setup_monochromator_twotheta': 'monochromator_twotheta',
        'setup_polarization_coefficient': 'polarization_coefficient',
        'setup_twotheta_bank': 'twotheta_bank',
        'setup_wavelength': 'wavelength',
        'setup_wavelength_2': 'wavelength_2',
        'setup_wavelength_2_to_1_ratio': 'wavelength_2_to_1_ratio',
    }, 'the instrument vocabulary must use all 13 public property spellings'


def test_c11_t40_structure_objects_match_the_upstream_vocabulary() -> None:
    cell = edi.Cell()
    for name in (
        'length_a',
        'length_b',
        'length_c',
        'angle_alpha',
        'angle_beta',
        'angle_gamma',
    ):
        assert isinstance(getattr(cell, name), edi.Parameter)
    for retired in ('a', 'b', 'c', 'alpha', 'beta', 'gamma'):
        assert not hasattr(cell, retired)

    site = edi.AtomSite()
    for name in (
        'id',
        'type_symbol',
        'wyckoff_letter',
        'fract_x',
        'fract_y',
        'fract_z',
        'occupancy',
        'adp_iso',
    ):
        assert hasattr(site, name)
    for retired in ('label', 'element', 'wyckoff', 'b_iso'):
        assert not hasattr(site, retired)

    structure = edi.Structure()
    assert hasattr(structure.space_group, 'name_h_m')
    assert hasattr(structure.space_group, 'coord_system_code')
    assert not isinstance(structure.space_group, str)
    assert not hasattr(structure, 'space_group_code')


def test_c11_t40_experiment_is_categorised_and_flat_names_are_retired() -> None:
    experiment = edi.BraggPdExperiment()
    expected = {
        'peak': (
            'broad_gauss_sigma_0',
            'broad_gauss_sigma_1',
            'broad_gauss_sigma_2',
            'broad_gauss_size',
            'broad_gauss_strain',
            'rise_alpha_0',
            'rise_alpha_1',
            'decay_beta_0',
            'decay_beta_1',
            'type',
        ),
        'instrument': (
            'setup_twotheta_bank',
            'calib_d_to_tof_offset',
            'calib_d_to_tof_linear',
            'calib_d_to_tof_quadratic',
        ),
        'linked_structure': ('scale', 'structure_id'),
        'absorption': ('type',),
        'experiment_type': (
            'sample_form',
            'beam_mode',
            'radiation_probe',
            'scattering_type',
        ),
    }
    for category_name, leaves in expected.items():
        category = getattr(experiment, category_name)
        for leaf in leaves:
            assert hasattr(category, leaf), f'{category_name}.{leaf}'

    illegal_union_members = {
        'peak': (
            'broad_lorentz_gamma_0',
            'broad_lorentz_gamma_1',
            'broad_lorentz_gamma_2',
            'broad_lorentz_size',
            'broad_lorentz_strain',
            'broad_gauss_u',
            'broad_gauss_v',
            'broad_gauss_w',
            'broad_lorentz_x',
            'broad_lorentz_y',
        ),
        'instrument': ('setup_wavelength', 'calib_twotheta_offset'),
        'absorption': ('abscor1', 'abscor2'),
    }
    for category_name, leaves in illegal_union_members.items():
        category = getattr(experiment, category_name)
        for leaf in leaves:
            assert not hasattr(category, leaf), f'{category_name}.{leaf} must be type-specific'

    retired_flat = {
        'alpha0',
        'alpha1',
        'beta0',
        'beta1',
        'sigma0',
        'sigma1',
        'sigma2',
        'size_g',
        'strain_g',
        'gamma0',
        'gamma1',
        'gamma2',
        'size_l',
        'strain_l',
        'zero',
        'dtt1',
        'dtt2',
        'u',
        'v',
        'w',
        'x',
        'y',
        'wavelength',
        'twotheta_offset',
        'scale',
        'structure_id',
        'bank_two_theta_deg',
        'peak_type',
        'absorption_type',
        'abscor1',
        'abscor2',
        'kind',
        'beam_mode',
    }
    assert not {name for name in retired_flat if hasattr(experiment, name)}
    assert not hasattr(edi, 'ExperimentKind')


def test_c11_t40_typed_axis_tokens_and_edi_defaults_are_presence_safe(tmp_path) -> None:
    reference = oracle()['enums']
    enum_contract = {
        'SampleFormEnum': reference['SampleFormEnum'],
        'BeamModeEnum': reference['BeamModeEnum'],
        'RadiationProbeEnum': reference['RadiationProbeEnum'],
        'ScatteringTypeEnum': reference['ScatteringTypeEnum'],
    }
    for class_name, members in enum_contract.items():
        enum_class = getattr(edi, class_name)
        for member in members:
            assert hasattr(enum_class, member)

    explicit = edi.Project.load(make_schema_2_case(tmp_path / 'explicit', 'tof_valid'))
    axes = explicit.experiment.experiment_type
    assert axes.sample_form == edi.SampleFormEnum.POWDER, (
        'the explicit project must retain its powder sample-form token'
    )
    assert axes.beam_mode == edi.BeamModeEnum.TIME_OF_FLIGHT, (
        'the explicit project must retain its time-of-flight beam-mode token'
    )
    assert axes.radiation_probe == edi.RadiationProbeEnum.NEUTRON, (
        'the explicit project must retain its neutron probe token'
    )
    assert axes.scattering_type == edi.ScatteringTypeEnum.BRAGG, (
        'the explicit project must retain its Bragg scattering token'
    )
    assert explicit.experiment.peak.type == edi.PeakProfileTypeEnum.TOF_JORGENSEN, (
        'the explicit TOF project must retain its exact peak selector'
    )

    absent_root = make_schema_2_case(tmp_path / 'absent', 'tof_valid')
    experiment_file = absent_root / 'experiments/wish_5_6.edi'
    text = experiment_file.read_text(encoding='utf-8')
    for tag in (
        '_experiment_type.sample_form',
        '_experiment_type.beam_mode',
        '_experiment_type.radiation_probe',
        '_experiment_type.scattering_type',
    ):
        text = '\n'.join(line for line in text.splitlines() if not line.startswith(tag)) + '\n'
    experiment_file.write_text(text, encoding='utf-8')
    defaults = edi.Project.load(absent_root).experiment.experiment_type
    assert defaults.sample_form == edi.SampleFormEnum.POWDER, (
        'an absent sample-form tag must select the ruled powder default'
    )
    assert defaults.beam_mode == edi.BeamModeEnum.TIME_OF_FLIGHT, (
        'an absent beam-mode tag must select the ruled time-of-flight default'
    )
    assert defaults.radiation_probe == edi.RadiationProbeEnum.NEUTRON, (
        'an absent radiation-probe tag must select the ruled neutron default'
    )
    assert defaults.scattering_type == edi.ScatteringTypeEnum.BRAGG, (
        'an absent scattering-type tag must select the ruled Bragg default'
    )


def test_c11_t40_measured_pattern_names_axis_and_refuses_ambiguous_modes(tmp_path) -> None:
    tof = edi.Project.load(make_schema_2_case(tmp_path / 'tof', 'tof_valid'))
    pattern = tof.experiment.data
    assert pattern is not None
    assert list(pattern.time_of_flight) == [20.0, 40.0, 80.0]
    assert not hasattr(pattern, 'two_theta'), (
        'the TOF concrete data type must not expose the CW-only two-theta axis'
    )
    assert list(pattern.intensity_meas) == [0.0, 0.0, 0.0]
    assert list(pattern.intensity_meas_su) == [1.0, 1.0, 1.0]
    assert list(pattern.axis()) == [20.0, 40.0, 80.0]
    for retired in ('grid', 'observed', 'sigma'):
        assert not hasattr(pattern, retired)

    cwl = edi.Project.load(make_schema_2_case(tmp_path / 'cwl', 'cwl_valid'))
    cwl_pattern = cwl.experiment.data
    assert cwl_pattern is not None
    assert not hasattr(cwl_pattern, 'time_of_flight'), (
        'the CW concrete data type must not expose the TOF-only time-of-flight axis'
    )
    assert list(cwl_pattern.two_theta)[:3] == [18.25, 31.613267, 39.5]
    assert list(cwl_pattern.axis()) == list(cwl_pattern.two_theta)

    both_root = make_schema_2_case(tmp_path / 'both', 'tof_valid')
    both_path = both_root / 'experiments/wish_5_6.edi'
    both_path.write_text(
        both_path.read_text(encoding='utf-8').replace(
            'loop_\n_data.time_of_flight',
            '_data.two_theta 12.5\n\nloop_\n_data.time_of_flight',
            1,
        ),
        encoding='utf-8',
    )
    with pytest.raises(edi.IoError, match=r'(?i)(axis|two.theta|time.of.flight|exactly one)'):
        edi.Project.load(both_root)

    neither_root = make_schema_2_case(tmp_path / 'neither', 'tof_valid')
    neither_path = neither_root / 'experiments/wish_5_6.edi'
    neither_path.write_text(
        neither_path.read_text(encoding='utf-8').replace(
            '_data.time_of_flight', '_data.untyped_axis', 1
        ),
        encoding='utf-8',
    )
    with pytest.raises(edi.IoError, match=r'(?i)(axis|two.theta|time.of.flight|exactly one)'):
        edi.Project.load(neither_root)
