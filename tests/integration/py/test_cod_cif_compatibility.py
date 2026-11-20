"""Exercise the headless Edi entrance on CIF syntax and atom-site defaults found in COD."""

import edi
import pytest

STRUCTURE = """data_structure
_cell_length_a 5
_cell_length_b 6
_cell_length_c 7
_cell_angle_alpha 90
_cell_angle_beta 90
_cell_angle_gamma 90
_space_group_name_H-M_alt 'P 1'
loop_
_atom_site_label
_atom_site_type_symbol
_atom_site_fract_x
_atom_site_fract_y
_atom_site_fract_z
_atom_site_occupancy
_atom_site_B_iso_or_equiv
Na1 ? .1 .2 .3 ? .
Cl1 Cl .4 .5 .6 .75 0
"""


@pytest.mark.parametrize('formula', ['{[Co4OH].2MeCN}n', '}text'])
def test_cif11_reads_a_bare_value_starting_with_a_curly_brace(formula: str) -> None:
    text = STRUCTURE + f'_chemical_formula_moiety {formula}\n'
    with pytest.warns(UserWarning, match=r'crysta\.schema\.cif_items_not_read') as warnings:
        structure = edi.StructureFactory.from_cif_str(text)
    assert any('_chemical_formula_moiety' in str(warning.message) for warning in warnings)
    assert len(structure.atom_sites) == 2


@pytest.mark.parametrize('formula', ['[text]', ']text'])
def test_cif11_refuses_an_unquoted_leading_square_bracket(formula: str) -> None:
    with pytest.raises(
        ValueError, match=r'opening with \[|cannot start an unquoted CIF 1\.1 value'
    ):
        edi.StructureFactory.from_cif_str(STRUCTURE + f'_chemical_formula_moiety {formula}\n')


def test_cif_import_reports_defaults_for_missing_site_values() -> None:
    with pytest.warns(UserWarning, match='taken as a default') as warnings:
        structure = edi.StructureFactory.from_cif_str(STRUCTURE)
    messages = [str(warning.message) for warning in warnings]
    assert any("site 'Na1' occupancy = 1" in message for message in messages)
    assert any("site 'Na1' isotropic displacement = 0" in message for message in messages)
    assert any("site 'Na1' element = Na" in message for message in messages)
    assert all("site 'Cl1'" not in message for message in messages)
    assert structure.atom_sites['Na1'].occupancy.value == 1
    assert structure.atom_sites['Na1'].adp_iso.value == 0
    assert structure.atom_sites['Cl1'].occupancy.value == 0.75


def _rhombohedral_structure(declarations: str) -> str:
    return (
        STRUCTURE
        .replace('_cell_length_b 6', '_cell_length_b 5')
        .replace('_cell_angle_gamma 90', '_cell_angle_gamma 120')
        .replace("_space_group_name_H-M_alt 'P 1'", declarations)
    )


@pytest.mark.parametrize('reverse', [False, True])
def test_cif_accepts_matching_space_group_alias_with_one_setting_suffix(*, reverse: bool) -> None:
    symbols = ["_space_group_name_H-M_alt 'R -3 c :H'", "_symmetry_space_group_name_H-M 'R -3 c'"]
    if reverse:
        symbols.reverse()
    with pytest.warns(UserWarning, match=r'crysta\.schema\.cif_items_not_read'):
        structure = edi.StructureFactory.from_cif_str(_rhombohedral_structure('\n'.join(symbols)))
    assert structure.space_group.it_number == 167
    assert structure.space_group.coord_system_code.lower() == 'h'


@pytest.mark.parametrize('other', ['R -3 c :R', 'R 3 c :H'])
def test_cif_refuses_conflicting_space_group_aliases(other: str) -> None:
    symbols = f"_space_group_name_H-M_alt 'R -3 c :H'\n_symmetry_space_group_name_H-M '{other}'"
    with pytest.raises(ValueError, match='different values'):
        edi.StructureFactory.from_cif_str(_rhombohedral_structure(symbols))


def test_cif_refuses_a_setting_conflicting_with_the_explicit_coordinate_code() -> None:
    symbols = "_space_group_name_H-M_alt 'R -3 c :H'\n_space_group_IT_coordinate_system_code r"
    with pytest.raises(ValueError, match=r'gives setting h but .* gives r'):
        edi.StructureFactory.from_cif_str(_rhombohedral_structure(symbols))
