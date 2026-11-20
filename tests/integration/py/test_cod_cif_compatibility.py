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


@pytest.mark.parametrize('hall', ['R 3 2"', 'R_3_2"'])
def test_cif_reads_an_ambiguous_hermann_mauguin_name_with_a_hall_symbol(hall: str) -> None:
    declarations = f"_space_group_name_H-M_alt 'R 3 2'\n_symmetry_space_group_name_Hall '{hall}'"
    with pytest.warns(UserWarning, match=r'crysta\.schema\.cif_items_not_read') as warnings:
        structure = edi.StructureFactory.from_cif_str(_rhombohedral_structure(declarations))
    assert structure.space_group.it_number == 155
    assert structure.space_group.coord_system_code.lower() == 'h'
    assert all(
        '_symmetry_space_group_name_Hall' not in str(warning.message) for warning in warnings
    )


def test_cif_refuses_a_hall_symbol_inconsistent_with_the_hermann_mauguin_name() -> None:
    declarations = "_space_group_name_H-M_alt 'R 3 2'\n_space_group.name_Hall 'P 1'"
    with pytest.raises(ValueError, match=r'_space_group\.name_Hall.*does not select a setting'):
        edi.StructureFactory.from_cif_str(_rhombohedral_structure(declarations))


@pytest.mark.parametrize('code', ['', '\n_space_group_IT_coordinate_system_code 2abc'])
def test_cif_reads_an_origin_only_suffix_with_an_orthorhombic_symbol(code: str) -> None:
    text = STRUCTURE.replace("'P 1'", f"'P b a n :2'{code}")
    with pytest.warns(UserWarning, match=r'crysta\.schema\.cif_items_not_read'):
        structure = edi.StructureFactory.from_cif_str(text)
    assert structure.space_group.it_number == 50
    assert structure.space_group.coord_system_code == '2abc'


def test_cif_refuses_incompatible_operations_with_an_origin_only_suffix() -> None:
    text = STRUCTURE.replace("'P 1'", "'P b a n :2'")
    text += "loop_\n_space_group_symop_operation_xyz\n'x,y,z'\n"
    with pytest.raises(ValueError, match='coordinate-system code'):
        edi.StructureFactory.from_cif_str(text)


@pytest.mark.parametrize('marker', ['?', '.'])
def test_cif_reports_the_site_and_column_of_an_absent_fractional_coordinate(marker: str) -> None:
    text = STRUCTURE.replace('Na1 ? .1', f'Na1 ? {marker}')
    with pytest.raises(
        ValueError, match=r"site 'Na1' requires a fractional coordinate.*_atom_site_fract_x"
    ):
        edi.StructureFactory.from_cif_str(text)


def test_cif_reports_the_row_and_column_of_an_absent_site_label() -> None:
    text = STRUCTURE.replace('Na1 ?', '? ?')
    with pytest.raises(
        ValueError, match=r'atom-site row 1 requires a site label.*_atom_site_label'
    ):
        edi.StructureFactory.from_cif_str(text)
