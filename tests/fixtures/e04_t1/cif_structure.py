"""Read the published cubic LBCO fixture with Gemmi, without either product."""

import gemmi


def edi_text(path):
    block = gemmi.cif.read_file(str(path)).sole_block()
    group = gemmi.cif.as_string(block.find_value('_space_group.name_H-M_alt'))
    if group != 'P m -3 m':
        raise ValueError('This reference covers the published cubic LBCO fixture only')
    text = 'data_lbco\n_edi.schema_version 3\n_space_group.name_h_m "P m -3 m"\n'
    text += '_space_group.coord_system_code 1\n'
    for field in ('length_a', 'length_b', 'length_c', 'angle_alpha', 'angle_beta', 'angle_gamma'):
        value = block.find_value('_cell.' + field)
        # ITA group 221 fixes all three angles at 90 degrees.
        number = gemmi.cif.as_number(value) if value else 90.0
        if not value and not field.startswith('angle_'):
            raise ValueError('The published source must supply every cell length')
        text += f'_cell.{field} {number:.17g}\n'
    fields = [
        'label',
        'type_symbol',
        'Wyckoff_letter',
        'ADP_type',
        'fract_x',
        'fract_y',
        'fract_z',
        'occupancy',
        'B_iso_or_equiv',
    ]
    names = [
        'id',
        'type_symbol',
        'wyckoff_letter',
        'adp_type',
        'fract_x',
        'fract_y',
        'fract_z',
        'occupancy',
        'adp_iso',
    ]
    text += 'loop_\n' + '\n'.join('_atom_site.' + name for name in names) + '\n'
    for row in block.find('_atom_site.', fields):
        if row[3] != 'Biso':
            raise ValueError('The published LBCO reference supplies isotropic B values')
        text += (
            ' '.join(
                str(value) if index < 4 else format(gemmi.cif.as_number(value), '.17g')
                for index, value in enumerate(row)
            )
            + '\n'
        )
    return text
