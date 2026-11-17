"""Small file-boundary witnesses; numerical values have closed-form sources."""

from pathlib import Path


def materialize(root, *, status=False, centred=False):
    root = Path(root)
    for directory in ('structures', 'experiments', 'analysis'):
        (root / directory).mkdir(parents=True, exist_ok=True)
    (root / 'project.edi').write_text('_edi.schema_version 3\n_metadata.name admission\n')
    (root / 'analysis/analysis.edi').write_text(
        '_edi.schema_version 3\n_minimizer.max_iterations 100\n'
        '_minimizer.chi_square_tolerance 1e-12\n'
    )
    group = 'I m -3 m' if centred else 'P 1'
    (root / 'structures/phase.edi').write_text(f'''data_phase
_edi.schema_version 3
_cell.length_a 6
_cell.length_b 6
_cell.length_c 6
_cell.angle_alpha 90
_cell.angle_beta 90
_cell.angle_gamma 90
_space_group.name_h_m "{group}"
loop_
_atom_site.id
_atom_site.type_symbol
_atom_site.wyckoff_letter
_atom_site.fract_x
_atom_site.fract_y
_atom_site.fract_z
_atom_site.occupancy
_atom_site.adp_type
_atom_site.adp_iso
Ni Ni a 0 0 0 1 Biso 0
''')
    rows = ((1, 0, 0, 1000, 1), (2, 0, 0, 10, 1), (2, 1, 1, 14, 2), (2, 2, 0, -2, 3))
    text = """data_bank
_edi.schema_version 3
_experiment_type.sample_form "single crystal"
_experiment_type.radiation_probe neutron
_experiment_type.scattering_type bragg
_experiment_type.beam_mode "constant wavelength"
_scattering_source.neutron_scattering_length sears1992
_instrument.setup_wavelength 0.8
_extinction.type none
loop_
_linked_structure.structure_id
_linked_structure.scale
phase 2.3
loop_
_refln.index_h
_refln.index_k
_refln.index_l
_refln.intensity_meas
_refln.intensity_meas_su
"""
    for row in rows:
        text += ' '.join(map(str, row))
        text += '\n'
    if status:
        text += (
            '\nloop_\n_excluded_reflection.id\n_excluded_reflection.index_h\n'
            '_excluded_reflection.index_k\n_excluded_reflection.index_l\n1 1 0 0\n'
        )
    if centred:
        text += '\n_reflns.absences exclude\n'
    (root / 'experiments/bank.edi').write_text(text)
    return root
