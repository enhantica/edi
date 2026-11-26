"""Write invented non-table legacy inputs; expected outputs are explicit baseline pins."""

from pathlib import Path

ROOT = Path(__file__).parent


def main():
    for kind, sign in [('I', '+1'), ('III', '-1')]:
        folder = ROOT / kind
        (folder / 'structures').mkdir(parents=True, exist_ok=True)
        (folder / 'experiments').mkdir(exist_ok=True)
        (folder / 'project.edi').write_text('_edi.schema_version 3\n_metadata.name legacy_pin\n')
        (folder / 'structures/phase.edi').write_text(f"""data_phase
_edi.schema_version 3
_cell.length_a 4
_cell.length_b 5
_cell.length_c 6
_cell.angle_alpha 90
_cell.angle_beta 90
_cell.angle_gamma 90
_space_group.name_h_m "P 1"
loop_
_space_group_symop_magn_operation.id
_space_group_symop_magn_operation.xyz
1 x,y,z,+1
2 -x+1/2,-y,-z,{sign}
loop_
_space_group_symop_magn_centering.id
_space_group_symop_magn_centering.xyz
1 x,y,z,+1
loop_
_atom_site.id
_atom_site.type_symbol
_atom_site.wyckoff_letter
_atom_site.fract_x
_atom_site.fract_y
_atom_site.fract_z
_atom_site.occupancy
_atom_site.adp_iso
_atom_site.adp_type
Co1 Co . .13 .27 .31 .8 .17 Biso
loop_
_atom_site_moment.label
_atom_site_moment.crystalaxis_x
_atom_site_moment.crystalaxis_y
_atom_site_moment.crystalaxis_z
Co1 .7 .9 -1.1
loop_
_magnetic_form_factor.type_symbol
_magnetic_form_factor.ion
Co Co2+
""")
        bank = (ROOT.parent / 'gui/type-iv/experiments/first.edi').read_text()
        (folder / 'experiments/first.edi').write_text(bank.replace('parent 3.6', 'phase 3.6'))


if __name__ == '__main__':
    main()
