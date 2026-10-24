"""Independent published CIF and name references judge every structure-import entrance."""

import importlib
import json
import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
FIXTURE = ROOT / 'tests/fixtures/dictionary_display/published_cod_1000236.cif'
CELL_TAGS = ('length_a', 'length_b', 'length_c')


def engine():
    return importlib.import_module('edi')


def published(notation):
    text = FIXTURE.read_text()
    if notation == 'underscore':
        return text
    # IUCr DDLm spellings, transcribed from the official save frames.
    replacements = {
        '_cell_': '_cell.',
        '_atom_site_aniso_': '_atom_site_aniso.',
        '_atom_site_': '_atom_site.',
        '_space_group_IT_number': '_space_group.IT_number',
        '_symmetry_space_group_name_H-M': '_space_group.name_H-M_alt',
        '_symmetry_equiv_pos_as_xyz': '_space_group_symop.operation_xyz',
    }
    for old, new in replacements.items():
        text = re.sub(r'(?m)^' + re.escape(old), new, text)
    return text


@pytest.mark.parametrize('notation', ['underscore', 'dot', 'upper'])
@pytest.mark.parametrize('factory', ['from_cif_str', 'from_cif_path'])
def test_published_cod_import_keeps_cell_atoms_symmetry_and_fixes_su(tmp_path, notation, factory):
    text = published('dot' if notation == 'upper' else notation)
    if notation == 'upper':
        text = re.sub(r'(?m)^(_\S+)', lambda match: match[1].upper(), text)
    path = tmp_path / 'published.cif'
    path.write_text(text)
    structure = getattr(engine().StructureFactory, factory)(
        text if factory.endswith('str') else path
    )
    for name in CELL_TAGS:
        parameter = getattr(structure.cell, name)
        assert parameter.value == pytest.approx(10.257, abs=1e-12), (
            'COD 1000236 revision 130149 gives every cubic cell length as 10.257 angstrom'
        )
        assert not parameter.free, (
            'CIF brackets describe published uncertainty and never make imported parameters free'
        )
        assert parameter.uncertainty is None, (
            'CIF brackets describe published uncertainty and never make imported parameters free'
        )
    assert structure.space_group.it_number == 199, (
        'The published COD structure retains space group 199'
    )
    sites = {str(site.id): site for site in structure.atom_sites}
    assert set(sites) == {'Ca1', 'Al1', 'Na1', 'F1', 'F2', 'F3'}, (
        'Every published COD atom label survives either CIF notation'
    )
    assert sites['Ca1'].fract_x.value == pytest.approx(0.4667), (
        'A nontrivial published fractional coordinate survives CIF conversion'
    )


@pytest.mark.parametrize(
    ('tag', 'kind', 'value'),
    [
        ('_atom_site_B_iso_or_equiv', 'Biso', 0.52),
        ('_atom_site.U_iso_or_equiv', 'Uiso', 0.0066),
    ],
)
def test_matched_cif_adp_name_selects_type_without_unit_conversion(tag, kind, value):
    text = (
        'data_adp\n_cell.length_a 5.1\n_cell.length_b 5.2\n_cell.length_c 5.3\n'
        '_cell.angle_alpha 88\n_cell.angle_beta 89\n_cell.angle_gamma 92\n'
        "_space_group.name_H-M_alt 'P 1'\nloop_\n_atom_site.label\n_atom_site.type_symbol\n"
        '_atom_site.fract_x\n_atom_site.fract_y\n_atom_site.fract_z\n_atom_site.occupancy\n'
        + tag
        + '\nLa1 La 0.17 0.23 0.31 0.58 '
        + str(value)
        + '\n'
    )
    site = engine().StructureFactory.from_cif_str(text).atom_sites[0]
    assert site.adp_type == kind, (
        'The matched official ADP name selects its native convention without conversion'
    )
    assert site.adp_iso.value == pytest.approx(value), (
        'The matched official ADP name selects its native convention without conversion'
    )


def test_cif_and_edi_brackets_keep_their_distinct_meanings():
    text = (
        'data_bracket\n_cell.length_a 3.89087(13)\n_cell.length_b 4.21\n_cell.length_c 5.32\n'
        '_cell.angle_alpha 88\n_cell.angle_beta 89\n_cell.angle_gamma 92\n'
        "_space_group.name_H-M_alt 'P 1'\nloop_\n_atom_site.label\n_atom_site.type_symbol\n"
        '_atom_site.fract_x\n_atom_site.fract_y\n_atom_site.fract_z\n_atom_site.occupancy\n'
        '_atom_site.B_iso_or_equiv\nLa1 La 0.17 0.23 0.31 0.58 0.52\n'
    )
    cif = engine().StructureFactory.from_cif_str(text)
    edi_text = (
        text
        .replace('_space_group.name_H-M_alt', '_space_group.name_h_m')
        .replace('_atom_site.label', '_atom_site.id')
        .replace('_atom_site.B_iso_or_equiv', '_atom_site.adp_iso')
    )
    edi = engine().StructureFactory.from_cif_str(edi_text)
    assert not cif.cell.length_a.free, (
        'A dotted official CIF cannot dispatch into the EDI free-flag reader'
    )
    assert cif.cell.length_a.uncertainty is None, (
        'A dotted official CIF cannot dispatch into the EDI free-flag reader'
    )
    assert edi.cell.length_a.free, (
        'An EDI-only item selects the EDI reader and preserves its free-flag uncertainty'
    )
    assert edi.cell.length_a.uncertainty == pytest.approx(0.00013), (
        'An EDI-only item selects the EDI reader and preserves its free-flag uncertainty'
    )


@pytest.mark.parametrize(
    ('kind', 'column', 'value'),
    [
        ('Uani', 'U_11', 0.0123),
        ('Bani', 'B_11', 0.52),
        ('beta', 'beta_11', 0.00045678),
    ],
)
def test_anisotropic_official_name_retains_the_tensor_convention(kind, column, value):
    text = (
        'data_tensor\n_cell_length_a 5.1\n_cell_length_b 5.2\n_cell_length_c 5.3\n'
        '_cell_angle_alpha 88\n_cell_angle_beta 89\n_cell_angle_gamma 92\n'
        "_space_group_name_H-M_alt 'P 1'\nloop_\n_atom_site_label\n_atom_site_type_symbol\n"
        '_atom_site_fract_x\n_atom_site_fract_y\n_atom_site_fract_z\n_atom_site_occupancy\n'
        'La1 La 0.17 0.23 0.31 0.58\nloop_\n_atom_site_aniso_label\n'
    )
    prefix = column.rsplit('_', 1)[0]
    for suffix in ('11', '22', '33', '12', '13', '23'):
        text += '_atom_site_aniso_' + prefix + '_' + suffix + '\n'
    text += 'La1 ' + ' '.join([str(value)] * 3 + ['0'] * 3) + '\n'
    structure = engine().StructureFactory.from_cif_str(text)
    assert structure.atom_sites[0].adp_type == kind, (
        'The official anisotropic tensor name selects its declared native convention'
    )
    assert structure.atom_site_aniso[0].adp_11.value == pytest.approx(value), (
        'A nontrivial anisotropic CIF value is read without changing its convention'
    )


def small_cif():
    return (
        'data_external_names\n_cell.length_a 5.12345\n_cell.length_b 6.23456\n'
        '_cell.length_c 7.34567\n_cell.angle_alpha 88.1\n_cell.angle_beta 89.2\n'
        "_cell.angle_gamma 92.3\n_space_group.name_H-M_alt 'P 1'\nloop_\n"
        '_atom_site.label\n_atom_site.type_symbol\n_atom_site.fract_x\n_atom_site.fract_y\n'
        '_atom_site.fract_z\n_atom_site.occupancy\n_atom_site.Wyckoff_symbol\n'
        '_atom_site.B_iso_or_equiv\nLa1 La 0.173 0.237 0.319 0.582 a 0.52\n'
    )


def name_witnesses():
    names = json.loads(
        (ROOT / 'tests/fixtures/dictionary_display/structure_names.json').read_text()
    )['names']
    result = []
    for canonical, spellings in names.items():
        for spelling in spellings:
            underscore = spelling.lower().replace('.', '_', 1)
            dot = underscore
            for category in ('atom_site_aniso', 'atom_site', 'space_group', 'symmetry', 'cell'):
                prefix = '_' + category + '_'
                if underscore.startswith(prefix):
                    dot = '_' + category + '.' + underscore[len(prefix) :]
                    break
            result.extend(
                (canonical, notation) for notation in sorted({spelling, underscore, dot})
            )
    return sorted(set(result))


@pytest.mark.parametrize(('canonical', 'spelling'), name_witnesses())
def test_every_independent_structure_name_in_both_notations_loads_the_same_quantity(
    canonical, spelling
):
    text = small_cif()
    if canonical == '_space_group.IT_number':
        text = text.replace("_space_group.name_H-M_alt 'P 1'", spelling + ' 1')
    else:
        text = text.replace(canonical, spelling)
    structure = engine().StructureFactory.from_cif_str(text)
    expected = {
        'length_a': 5.12345,
        'length_b': 6.23456,
        'length_c': 7.34567,
        'angle_alpha': 88.1,
        'angle_beta': 89.2,
        'angle_gamma': 92.3,
    }
    for name, value in expected.items():
        assert getattr(structure.cell, name).value == pytest.approx(value), (
            'Every official or upstream alias retains the independently written cell values'
        )
    assert structure.space_group.it_number == 1, (
        'Every space-group spelling resolves the independently declared P1 group'
    )
    site = structure.atom_sites[0]
    assert str(site.id) == 'La1', (
        'Every atom-label alias retains the independently written row identity'
    )
    assert str(site.type_symbol) == 'La', (
        'Every element alias retains the independently written species'
    )
    assert site.fract_x.value == pytest.approx(0.173), (
        'Every coordinate alias retains a nontrivial written coordinate'
    )
    assert site.fract_y.value == pytest.approx(0.237), (
        'Every coordinate spelling retains the independent y value'
    )
    assert site.fract_z.value == pytest.approx(0.319), (
        'Every coordinate spelling retains the independent z value'
    )
    assert site.occupancy.value == pytest.approx(0.582), (
        'Every occupancy alias retains the independently written fraction'
    )
    assert str(site.wyckoff_letter) == 'a', 'Every Wyckoff alias retains the declared letter'


@pytest.mark.parametrize(
    'required',
    [
        '_cell.length_a',
        '_cell.length_b',
        '_cell.length_c',
        '_cell.angle_alpha',
        '_cell.angle_beta',
        '_cell.angle_gamma',
        '_space_group.name_H-M_alt',
    ],
)
def test_missing_required_structure_scalars_are_refused_and_named(required):
    text = re.sub(r'(?m)^' + re.escape(required) + r'[^\n]*\n', '', small_cif())
    with pytest.raises(ValueError, match=r'(?i)missing|required') as failure:
        engine().StructureFactory.from_cif_str(text)
    item = required.split('.', 1)[1].lower()
    assert item in str(failure.value).lower(), (
        'A missing required CIF item is refused with the missing quantity named'
    )


def test_published_fixture_is_parsed_by_gemmi_independently_of_the_product():
    gemmi = importlib.import_module('gemmi')
    document = gemmi.cif.read_file(str(FIXTURE))
    reference = gemmi.make_small_structure_from_block(document.sole_block())
    assert reference.cell.a == pytest.approx(10.257), (
        'Gemmi independently reads the published COD lattice length'
    )
    assert len(reference.sites) == 6, 'Gemmi independently reads every published COD atom site'
    assert reference.spacegroup.number == 199, (
        'Gemmi independently resolves the published COD symmetry'
    )


@pytest.mark.parametrize('factory', ['from_cif_str', 'from_cif_path'])
def test_second_published_cod_structure_retains_rocksalt_cell_and_sites(factory):
    path = ROOT / 'tests/fixtures/dictionary_display/published_cod_1000041.cif'
    structure = getattr(engine().StructureFactory, factory)(
        path.read_text() if factory.endswith('str') else path
    )
    assert structure.cell.length_a.value == pytest.approx(5.62), (
        'COD 1000041 reports the rocksalt lattice length 5.62'
    )
    assert structure.space_group.it_number == 225, (
        'COD 1000041 reports the face-centred rocksalt space group'
    )
    sites = {str(site.id): site for site in structure.atom_sites}
    assert set(sites) == {'Na1', 'Cl1'}, (
        'Every atom in the second published COD structure is imported'
    )
    assert sites['Na1'].fract_x.value == pytest.approx(0), (
        'The published sodium site remains at the origin'
    )
    assert sites['Cl1'].fract_x.value == pytest.approx(0.5), (
        'The published chlorine site retains its half translation'
    )


@pytest.mark.parametrize(
    ('item', 'index'),
    [
        ('_atom_site.fract_x', 2),
        ('_atom_site.fract_y', 3),
        ('_atom_site.fract_z', 4),
    ],
)
def test_missing_required_atom_coordinates_are_refused_and_named(item, index):
    text = small_cif().replace(item + '\n', '')
    original = 'La1 La 0.173 0.237 0.319 0.582 a 0.52'
    values = original.split()
    values.pop(index)
    text = text.replace(original, ' '.join(values))
    with pytest.raises(ValueError, match=r'(?i)missing|required') as failure:
        engine().StructureFactory.from_cif_str(text)
    assert item.split('.', 1)[1] in str(failure.value).lower(), (
        'A missing required atom coordinate is refused with its quantity named'
    )
