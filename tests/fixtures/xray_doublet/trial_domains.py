"""Authored relations and domain limits; profiles only drive trial proposals."""

import math

CASES = {
    'ratio': ('instrument.setup_wavelength_2_to_1_ratio', '4 * source', 0.5),
    'second-line': ('instrument.setup_wavelength_2', '2.5 - 10 * source', 1.25),
    'polarization': ('instrument.setup_polarization_coefficient', '4 * source', 0.5),
    'monochromator': ('instrument.setup_monochromator_twotheta', '500 * source', 62.5),
    'march-r': ('preferred_orientation.phase.march_r', '2.5 - 10 * source', 1.25),
    'march-fraction': ('preferred_orientation.phase.march_random_fract', '4 * source', 0.5),
    'displacement': (
        'instrument.calib_sample_displacement',
        'exp(3000 * (source - 0.125)) - 1',
        0,
    ),
    'transparency': (
        'instrument.calib_sample_transparency',
        'exp(3000 * (source - 0.125)) - 1',
        0,
    ),
    'tof-calibration': ('instrument.calib_d_to_tof_linear', '10000 * (0.5 - source)', 3750),
}


def structure_text(mapping, source_kind):
    sg, letter, y, z = {
        'identity': ('P 1', 'a', 0.125, 0.3),
        'follower': ('P 2 3', 'e', 0.125, 0.125),
        'opposite': ('P -3 m 1', 'i', -0.125, 0.3),
    }[mapping]
    a, b, c, gamma = (4, 4, 6, 120) if mapping == 'opposite' else (4, 4, 4, 90)
    x_free = '()' if source_kind in {'coordinate', 'chain'} else ''
    y_free = '()' if source_kind == 'fixed' else ''
    adp_free = '()' if source_kind == 'scalar' else ''
    return f'''data_phase
_edi.schema_version 3
_cell.length_a {a}
_cell.length_b {b}
_cell.length_c {c}
_cell.angle_alpha 90
_cell.angle_beta 90
_cell.angle_gamma {gamma}
_space_group.name_h_m "{sg}"
loop_
_atom_site.id
_atom_site.wyckoff_letter
_atom_site.type_symbol
_atom_site.adp_type
_atom_site.fract_x
_atom_site.fract_y
_atom_site.fract_z
_atom_site.occupancy
_atom_site.adp_iso
X {letter} Li Biso 0.125{x_free} {y}{y_free} {z} 0.7 0.125{adp_free}
'''


def experiment_text(family):
    tof = family == 'tof-calibration'
    prefix = """data_bank
_edi.schema_version 3
_experiment_type.sample_form powder
_experiment_type.scattering_type bragg
"""
    if tof:
        prefix += """_experiment_type.radiation_probe neutron
_experiment_type.beam_mode time-of-flight
_scattering_source.neutron_scattering_length sears1992
_peak.type tof-jorgensen
_peak.rise_alpha_0 -0.4
_peak.rise_alpha_1 1
_peak.decay_beta_0 0.3
_peak.decay_beta_1 0
_peak.broad_gauss_sigma_0 25
_peak.broad_gauss_sigma_1 0
_peak.broad_gauss_sigma_2 0
_peak.broad_gauss_size 0
_peak.broad_gauss_strain 0
_peak.cutoff_fwhm 5
_instrument.setup_twotheta_bank 90
_instrument.calib_d_to_tof_offset 0
_instrument.calib_d_to_tof_linear 3750
_instrument.calib_d_to_tof_quadratic 0
"""
    else:
        prefix += """_experiment_type.radiation_probe xray
_experiment_type.beam_mode "constant wavelength"
_scattering_source.xray_form_factor it1992
_scattering_source.xray_dispersion none
_peak.type cwl-tch-pseudo-voigt
_peak.broad_gauss_u 0
_peak.broad_gauss_v 0
_peak.broad_gauss_w 0.04
_peak.broad_lorentz_x 0
_peak.broad_lorentz_y 0
_peak.cutoff_fwhm 5
_instrument.setup_wavelength 1.54
_instrument.calib_twotheta_offset 0
_instrument.setup_wavelength_2 1.6732
_instrument.setup_wavelength_2_to_1_ratio 0.375
_instrument.setup_polarization_coefficient 0.37
_instrument.setup_monochromator_twotheta 41
"""
    target, _expression, initial = CASES[family]
    if target.startswith('instrument.'):
        tag = '_' + target
        lines = prefix.splitlines()
        lines = [line for line in lines if not line.startswith(tag + ' ')]
        prefix = '\n'.join(lines) + f'\n{tag} {initial}\n'
    prefix += """loop_
_linked_structure.structure_id
_linked_structure.scale
phase 1
"""
    if family.startswith('march'):
        r, fraction = (initial, 0.3) if family == 'march-r' else (0.73, initial)
        prefix += f"""
loop_
_preferred_orientation.structure_id
_preferred_orientation.march_r
_preferred_orientation.march_random_fract
_preferred_orientation.index_h
_preferred_orientation.index_k
_preferred_orientation.index_l
phase {r} {fraction} 1 0 0
"""
    return prefix


def relation_text(family, mapping, source_kind):
    target, expression, _initial = CASES[family]
    axis = 'fract_y' if mapping != 'identity' else 'fract_x'
    source = 'phase.atom_site.X.' + ('adp_iso' if source_kind == 'scalar' else axis)
    if mapping == 'opposite':
        expression = expression.replace('source', '(-source)')
    aliases = [f'source {source}', f'target bank.{target}']
    constraints = []
    if source_kind == 'chain':
        middle = (
            'calib_d_to_tof_offset' if family == 'tof-calibration' else 'calib_twotheta_offset'
        )
        aliases.append('middle bank.instrument.' + middle)
        constraints.append('middle_relation "middle = 0.5 * source + 0.01" true')
        expression = expression.replace('source', '(2 * (middle - 0.01))')
    constraints.append(f'domain_relation "target = {expression}" true')
    return (
        '_edi.schema_version 3\n_minimizer.max_iterations 2\n'
        'loop_\n_alias.id\n_alias.parameter_unique_name\n'
        + '\n'.join(aliases)
        + '\n\nloop_\n_constraint.id\n_constraint.expression\n_constraint.enabled\n'
        + '\n'.join(constraints)
        + '\n'
    )


def texts(family, mapping='identity', source_kind='coordinate'):
    return (
        structure_text(mapping, source_kind),
        experiment_text(family),
        relation_text(family, mapping, source_kind),
    )


def grid(family):
    return (
        [5000 + 25 * i for i in range(121)]
        if family == 'tof-calibration'
        else [20 + 0.2 * i for i in range(201)]
    )


def write(root, family, mapping='identity', source_kind='coordinate', *, joint=False):
    structure, experiment, analysis = texts(family, mapping, source_kind)
    (root / 'structures').mkdir(parents=True)
    (root / 'experiments').mkdir()
    (root / 'analysis').mkdir()
    (root / 'structures/phase.edi').write_text(structure)
    data = '\nloop_\n_data.' + ('time_of_flight' if family == 'tof-calibration' else 'two_theta')
    data += '\n_data.intensity_meas\n_data.intensity_meas_su\n'
    data += ''.join(f'{x:.17g} 1 1\n' for x in grid(family))
    (root / 'experiments/bank.edi').write_text(experiment + data)
    if joint:
        (root / 'experiments/other.edi').write_text(
            experiment.replace('data_bank', 'data_other') + data
        )
        analysis = '_fitting_mode.type joint\n' + analysis
    (root / 'analysis/analysis.edi').write_text(analysis)
    return root


def admitted_source(family, value):
    if family in {'ratio', 'polarization', 'march-fraction'}:
        return 0 <= 4 * value <= 1
    if family in {'second-line', 'march-r'}:
        return 2.5 - 10 * value > 0
    if family == 'monochromator':
        return 0 <= 500 * value <= 180
    if family in {'displacement', 'transparency'}:
        return 3000 * (value - 0.125) < math.log(float.fromhex('0x1.fffffffffffffp+1023'))
    linear = 10000 * (0.5 - value)
    return linear > 0 and -0.4 + linear / 8000 > 0
