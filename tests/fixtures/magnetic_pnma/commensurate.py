"""Exact commensurate examples derived from lattice characters, not engine output."""


def structure(  # noqa: PLR0913 — each argument is an independent crystallographic input
    *,
    period=1,
    vectors=('0,0,0',),
    operations=('x,y,z,+1',),
    centrings=('x,y,z,+1',),
    parent='P 1',
    parent_number=1,
    b=5,
    gamma=90,
    moment='0.7 1.3 -0.4',
):
    text = f"""data_cosio
_edi.schema_version 3
_cell.length_a {4 * period}
_cell.length_b {b}
_cell.length_c 6
_cell.angle_alpha 90
_cell.angle_beta 90
_cell.angle_gamma {gamma}
_space_group.name_h_m "P 1"
_parent_space_group.name_H-M_alt "{parent}"
_parent_space_group.IT_number {parent_number}
_parent_space_group.transform_Pp_abc "a,b,c;0,0,0"
_parent_space_group.child_transform_Pp_abc "{period}a,b,c;0,0,0"
_parent_space_group.reference_setting standard
_parent_space_group.derived false
loop_
_space_group_symop_magn_operation.id
_space_group_symop_magn_operation.xyz
"""
    text += ''.join(f'{i} {op}\n' for i, op in enumerate(operations, 1))
    text += 'loop_\n_space_group_symop_magn_centering.id\n_space_group_symop_magn_centering.xyz\n'
    text += ''.join(f'{i} {op}\n' for i, op in enumerate(centrings, 1))
    text += 'loop_\n_parent_propagation_vector.id\n_parent_propagation_vector.kxkykz\n'
    text += ''.join(f'{i} {k}\n' for i, k in enumerate(vectors, 1))
    text += """loop_
_atom_site.id
_atom_site.type_symbol
_atom_site.wyckoff_letter
_atom_site.fract_x
_atom_site.fract_y
_atom_site.fract_z
_atom_site.occupancy
_atom_site.adp_iso
_atom_site.adp_type
A Co a 0 0 0 1 .17 Biso
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
"""
    return text + f'A {moment}\n'


VALID = {
    'tripled': {'period': 3, 'vectors': ('1/3,0,0',)},
    'half-order-displaced-sublattice': {'period': 2, 'vectors': ('1/2,0,0',)},
    'sixteenth-exact': {'period': 16, 'vectors': ('1/16,0,0',)},
    'sixteenth-decimal': {'period': 16, 'vectors': ('0.0625,0,0',)},
    'rounded-third': {'period': 3, 'vectors': ('0.333333,0,0',)},
    'anti-translation-in-centring': {
        'period': 2,
        'vectors': ('1/2,0,0',),
        'centrings': ('x,y,z,+1', 'x+1/2,y,z,-1'),
    },
    'anti-translation-in-operations': {
        'period': 2,
        'vectors': ('1/2,0,0',),
        'operations': ('x,y,z,+1', 'x+1/2,y,z,-1'),
    },
    'strained-parent': {'parent': 'P 4', 'parent_number': 75},
    'grey-zero': {'operations': ('x,y,z,+1', 'x,y,z,-1')},
}
INVALID = {
    'primitive-third': {'vectors': ('1/3,0,0',)},
    'wrong-anticharacter': {
        'period': 2,
        'vectors': ('0,0,0',),
        'centrings': ('x,y,z,+1', 'x+1/2,y,z,-1'),
    },
    'wrong-positive-character': {
        'period': 2,
        'vectors': ('1/2,0,0',),
        'centrings': ('x,y,z,+1', 'x+1/2,y,z,+1'),
    },
    'missing-theta': {'operations': ('x,y,z',)},
    'invalid-theta': {'operations': ('x,y,z,0',)},
    'missing-identity': {'operations': ('-x,-y,-z,+1',)},
    'not-closed': {'operations': ('x,y,z,+1', 'x+1/3,y,z,+1'), 'period': 3},
    'rotating-centring': {'centrings': ('x,y,z,+1', '-x,-y,z,+1')},
    'wrong-child-metric': {'operations': ('x,y,z,+1', 'x+y,-y,z,+1')},
    'grey-nonzero': {'period': 2, 'vectors': ('1/2,0,0',), 'operations': ('x,y,z,+1', 'x,y,z,-1')},
    'fraction-before-decimal-duplicate': {'period': 22, 'vectors': ('1/2,0,0', '0.5,0,0')},
    'decimal-before-fraction-duplicate': {'period': 22, 'vectors': ('0.5,0,0', '1/2,0,0')},
    'reciprocal-duplicate': {'period': 3, 'vectors': ('1/3,0,0', '4/3,0,0')},
    'negative-duplicate': {'period': 3, 'vectors': ('1/3,0,0', '-1/3,0,0')},
}
