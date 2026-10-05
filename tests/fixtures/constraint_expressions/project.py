"""Small declared models and closed-form observations for constraint checks."""

from pathlib import Path


def materialize(  # noqa: PLR0913 - independent file-boundary witnesses
    root,
    aliases=(),
    expressions=(),
    *,
    symmetry=False,
    polynomial=False,
    dependent_free=False,
    observations=None,
    second_structure=False,
):
    root = Path(root)
    for directory in ('structures', 'experiments', 'analysis'):
        (root / directory).mkdir(parents=True, exist_ok=True)
    (root / 'project.edi').write_text('_edi.schema_version 3\n_metadata.name relations\n')
    analysis = '_edi.schema_version 3\n_fitting_mode.type single\n_minimizer.max_iterations 80\n'
    if aliases:
        analysis += 'loop_\n_alias.id\n_alias.parameter_unique_name\n'
        analysis += ''.join(f'{name} {target}\n' for name, target in aliases)
    if expressions:
        analysis += 'loop_\n_constraint.expression\n'
        analysis += ''.join(f'"{expression}"\n' for expression in expressions)
    (root / 'analysis/analysis.edi').write_text(analysis)
    group = 'P m -3 m' if symmetry else 'P 1'
    flag = '()' if dependent_free else ''
    xyz = '0 0 0' if symmetry else '0.17 0.23 0.31'
    structure = f'''data_phase
_edi.schema_version 3
_cell.length_a 4.1
_cell.length_b 4.1{flag if symmetry else ''}
_cell.length_c 4.1
_cell.angle_alpha 90
_cell.angle_beta 90
_cell.angle_gamma 90
_space_group.name_h_m "{group}"
loop_
_atom_site.id
_atom_site.type_symbol
_atom_site.wyckoff_letter
_atom_site.adp_type
_atom_site.fract_x
_atom_site.fract_y
_atom_site.fract_z
_atom_site.occupancy
_atom_site.adp_iso
A La a Biso {xyz} 0.7 0.3
B La a Biso {xyz} 0.3 0.8{flag if not symmetry else ''}
'''
    (root / 'structures/phase.edi').write_text(structure)
    if second_structure:
        (root / 'structures/other.edi').write_text(
            structure.replace('data_phase', 'data_other').replace('0.7 0.3', '0.7 0.65')
        )
    if polynomial:
        background = """_background.type polynomial
_background.origin 40
loop_
_background.id
_background.order
_background.coef
base 0 4()
ramp 1 1()
curve 2 3
"""
    else:
        background = """_background.type line-segment
loop_
_background.id
_background.position
_background.intensity
left 20 3
right 100 9
"""
    if observations is None:
        observations = [(20 + 2 * i, 100) for i in range(41)]
    data = ''
    if observations is not None:
        data = 'loop_\n_data.two_theta\n_data.intensity_meas\n_data.intensity_meas_su\n'
        data += ''.join(f'{x:.17g} {y:.17g} 1\n' for x, y in observations)
    extra = 'other 0\n' if second_structure else ''
    (root / 'experiments/bank.edi').write_text(f"""data_bank
_edi.schema_version 3
_calculator.type crysta
_experiment_type.sample_form powder
_experiment_type.radiation_probe neutron
_experiment_type.scattering_type bragg
_experiment_type.beam_mode "constant wavelength"
_peak.type cwl-tch-pseudo-voigt
_peak.broad_gauss_u 0
_peak.broad_gauss_v 0
_peak.broad_gauss_w 0.15
_peak.broad_lorentz_x 0
_peak.broad_lorentz_y 0
_peak.cutoff_fwhm 5
_instrument.setup_wavelength 1.54
_instrument.calib_twotheta_offset 0
loop_
_linked_structure.structure_id
_linked_structure.scale
phase {0 if polynomial else 1}
{extra}
{background}
{data}""")
    return root
