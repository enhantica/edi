"""Portable independent fixture adapter; inputs contain no calculated F² column."""

import json
from pathlib import Path

import gemmi
import numpy as np

HERE = Path(__file__).resolve().parent
REFERENCE = json.loads((HERE / 'reference.json').read_text())


def project_files(destination, temperature, *, magnetic=True):
    record = REFERENCE['cases'][temperature]
    sample = record['model']
    (destination / 'structures').mkdir(parents=True)
    (destination / 'experiments').mkdir()
    cell = [value[0] for value in sample['cell']]
    text = (
        'data_structure\n_edi.schema_version 3\n_space_group.name_h_m "P n m '
        'a"\n_space_group.coord_system_code abc\n'
    )
    text += ''.join(
        f'_cell.length_{axis} {value}\n' for axis, value in zip('abc', cell, strict=True)
    )
    text += '_cell.angle_alpha 90\n_cell.angle_beta 90\n_cell.angle_gamma 90\n'
    text += (
        'loop_\n_atom_site.id\n_atom_site.type_symbol\n_atom_site.wyckoff_lett'
        'er\n_atom_site.fract_x\n_atom_site.fract_y\n_atom_site.fract_z\n_atom_'
        'site.occupancy\n_atom_site.adp_type\n_atom_site.adp_iso\n'
    )
    for site in sample['sites']:
        letter = 'a' if site['id'] == 'Co1' else 'd' if site['id'] == 'O3' else 'c'
        text += (
            ' '.join(
                [site['id'], site['element'], letter]
                + [str(v[0]) for v in site['xyz']]
                + ['1', 'beta', '0']
            )
            + '\n'
        )
    text += 'loop_\n_atom_site_aniso.id\n' + ''.join(
        '_atom_site_aniso.adp_' + key + '\n' for key in ('11', '22', '33', '12', '13', '23')
    )
    denominators = [
        cell[0] ** 2,
        cell[1] ** 2,
        cell[2] ** 2,
        cell[0] * cell[1],
        cell[0] * cell[2],
        cell[1] * cell[2],
    ]
    for site in sample['sites']:
        beta = [2 * np.pi**2 * v[0] / den for v, den in zip(site['u'], denominators, strict=True)]
        text += site['id'] + ' ' + ' '.join(map(str, beta)) + '\n'
    if temperature == '2.5K' and magnetic:
        text += """_space_group_magn.number_BNS "62.441"
_space_group_magn.name_BNS Pnma
_space_group_magn.name_UNI Pnma.1
_space_group_magn.number_OG "62.1.502"
_space_group_magn.name_OG Pnma
_parent_space_group.name_H-M_alt Pnma
_parent_space_group.IT_number 62
_parent_space_group.transform_Pp_abc "a,b,c;0,0,0"
_parent_space_group.child_transform_Pp_abc "a,b,c;0,0,0"
_parent_space_group.reference_setting standard
_parent_space_group.derived false
loop_
_space_group_symop_magn_operation.id
_space_group_symop_magn_operation.xyz
"""
        text += ''.join(
            f'{index} {op.triplet()},+1\n'
            for index, op in enumerate(gemmi.find_spacegroup_by_name('Pnma').operations(), 1)
        )
        text += """loop_
_space_group_symop_magn_centering.id
_space_group_symop_magn_centering.xyz
1 x,y,z,+1
loop_
_parent_propagation_vector.id
_parent_propagation_vector.kxkykz
1 0,0,0
loop_
_magnetic_form_factor.type_symbol
_magnetic_form_factor.ion
_magnetic_form_factor.j2_coefficient
Co Co2+ 0
loop_
_atom_site_moment.label
_atom_site_moment.crystalaxis_x
_atom_site_moment.crystalaxis_y
_atom_site_moment.crystalaxis_z
_atom_site_moment.symmform
Co1 1.20 3.64 0.57 Mx,My,Mz
Co2 0 3.35 0 0,My,0
"""
    (destination / 'structures/structure.edi').write_text(text)
    text = """data_experiment
_edi.schema_version 3
_experiment_type.sample_form "single crystal"
_experiment_type.radiation_probe neutron
_experiment_type.scattering_type bragg
_experiment_type.beam_mode "constant wavelength"
_scattering_source.neutron_scattering_length sears1992
_instrument.setup_wavelength .552
_extinction.type larson-anisotropic
"""
    text += ''.join(
        f'_extinction.coefficient_{key} {value[0]}\n'
        for key, value in zip(
            ('11', '22', '33', '12', '13', '23'), sample['extinction'], strict=True
        )
    )
    text += f'loop_\n_linked_structure.structure_id\n_linked_structure.scale\nstructure {
        record[("scale")]
    }\n'
    text += (
        'loop_\n_refln.index_h\n_refln.index_k\n_refln.index_l\n_refln.intensit'
        'y_meas\n_refln.intensity_meas_su\n'
    )
    # At 2.5 K the source sigma is 2theta, so calculation-only inputs use unit
    # weights. F²calc parity is independent of any statistical weight choice.
    text += ''.join(
        ' '.join(map(str, row[:3] + [row[4], 1.0 if temperature == '2.5K' else row[5]])) + '\n'
        for row in record['rows']
    )
    (destination / 'experiments/experiment.edi').write_text(text)
    return destination
