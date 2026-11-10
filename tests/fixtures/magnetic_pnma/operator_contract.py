"""Operator-family inputs with independent metric, orbit and translation expectations."""

from tests.fixtures.magnetic_pnma import commensurate


def identity(*, free=False, aniso=False, omitted=False):
    source = commensurate.structure(moment='0 1 0')
    source = source.replace('_space_group.name_h_m "P 1"', '_space_group.name_h_m "P n m a"')
    source = source.replace(
        '_parent_space_group.derived false', '_parent_space_group.derived true'
    )
    source = source.replace('A Co a 0 0 0 1 .17 Biso', 'A Co c .13 .37 .29 1 .17 Biso')
    source = source.replace('_cell.angle_alpha 90', '_cell.angle_alpha 79')
    source = source.replace('_cell.angle_beta 90', '_cell.angle_beta 91')
    source = source.replace('_cell.angle_gamma 90', '_cell.angle_gamma 73')
    if free:
        source = source.replace('_cell.length_a 4', '_cell.length_a 4()')
        source = source.replace('c .13 .37 .29', 'c .13 .37() .29')
    if aniso:
        source = source.replace('1 .17 Biso', '1 .17 Uani')
        source += (
            'loop_\n_atom_site_aniso.id\n_atom_site_aniso.adp_11\n_atom_site_aniso.adp_22\n'
            '_atom_site_aniso.adp_33\n_atom_site_aniso.adp_12\n_atom_site_aniso.adp_13\n'
            '_atom_site_aniso.adp_23\nA .02 .03 .04 0 0 0\n'
        )
    if omitted:
        source = source.replace('_space_group.name_h_m "P n m a"\n', '')
    return source


def cif(source):
    # Removing a native-name suffix after CIF conversion leaves its `_edi` prefix
    # joined to the next loop_. Operate on complete native declarations first.
    source = source.replace('\n_parent_space_group.derived true\n', '\n', 1)
    source = source.replace('\n_parent_space_group.reference_setting standard\n', '\n', 1)
    source = source.replace(
        '\nloop_\n_scattering_length.type_symbol\n_scattering_length.length_fm\nCo 2.49\n',
        '\n',
        1,
    )
    return commensurate.magnetic_cif(source)


def shifted_inversion(denominator):
    source = commensurate.structure(
        operations=('x,y,z,+1', f'-x+1/{denominator},-y,-z,+1'), moment='0 1 0'
    )
    source = source.replace(
        '_parent_space_group.derived false', '_parent_space_group.derived true'
    )
    return (
        source + 'loop_\n_scattering_length.type_symbol\n_scattering_length.length_fm\nCo 2.49\n'
    )


def tensor_table():
    source = commensurate.structure(operations=('x,y,z,+1', '-x,-y,-z,+1'), moment='0 1 0')
    source = source.replace('_space_group.name_h_m "P 1"', '_space_group.name_h_m "P -1"')
    source = source.replace(
        '_parent_space_group.derived false', '_parent_space_group.derived true'
    )
    source = source.replace('A Co a 0 0 0 1 .17 Biso', 'A Co i .13 .37 .29 1 .17 Uani')
    source += (
        'loop_\n_atom_site_aniso.id\n_atom_site_aniso.adp_11\n_atom_site_aniso.adp_22\n'
        '_atom_site_aniso.adp_33\n_atom_site_aniso.adp_12\n_atom_site_aniso.adp_13\n'
        '_atom_site_aniso.adp_23\nA .02 .03 .04 0 0 0\n'
    )
    return source
