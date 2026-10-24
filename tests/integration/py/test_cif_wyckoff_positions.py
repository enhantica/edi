"""ITA position representatives, independent of engine tables, judge CIF site inference."""

import importlib
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
HERE = ROOT / 'tests/fixtures/dictionary_display'
REFERENCES = json.loads((HERE / 'wyckoff_sources.json').read_text())


def imported(tmp_path, text, factory):
    api = importlib.import_module('edi')
    path = tmp_path / 'published.cif'
    path.write_text(text)
    return getattr(api.StructureFactory, factory)(text if factory.endswith('str') else path)


def cif_text(reference, notation, missing):
    gemmi = importlib.import_module('gemmi')
    document = gemmi.cif.read_file(str(HERE / reference['file']))
    block = document.sole_block()
    # Remove both letter and multiplicity; neither may reveal the expected orbit.
    for tag in (
        list(block.find_loop('_atom_site.label').get_loop().tags)
        if block.find_loop('_atom_site.label')
        else list(block.find_loop('_atom_site_label').get_loop().tags)
    ):
        key = tag.lower().replace('.', '_')
        if 'wyckoff' in key or 'symmetry' in key:
            column = block.find_loop(tag)
            if missing == 'absent' or 'wyckoff' not in key:
                column.get_loop().remove_column(tag)
            else:
                for i in range(len(column)):
                    column[i] = missing
    text = document.as_string()
    # A CIF lacking a letter column stays lacking for all missing-token cases.
    if notation == 'dot':
        for old, new in [
            ('_cell_', '_cell.'),
            ('_atom_site_', '_atom_site.'),
            ('_symmetry_space_group_name_H-M', '_space_group.name_H-M_alt'),
            ('_space_group_IT_number', '_space_group.IT_number'),
        ]:
            text = text.replace(old, new)
    else:
        for old, new in [
            ('_cell.', '_cell_'),
            ('_atom_site.', '_atom_site_'),
            ('_space_group.name_H-M_alt', '_symmetry_space_group_name_H-M'),
            ('_space_group.IT_coordinate_system_code', '_space_group_IT_coordinate_system_code'),
        ]:
            text = text.replace(old, new)
    return text


@pytest.mark.parametrize('reference', REFERENCES, ids=list(REFERENCES))
@pytest.mark.parametrize('notation', ['dot', 'underscore'])
@pytest.mark.parametrize('missing', ['absent', '.', '?'])
@pytest.mark.parametrize('factory', ['from_cif_str', 'from_cif_path'])
def test_missing_published_wyckoff_letters_follow_international_tables(
    tmp_path, reference, notation, missing, factory
):
    row = REFERENCES[reference]
    structure = imported(tmp_path, cif_text(row, notation, missing), factory)
    actual = {str(site.id): site.wyckoff_letter for site in structure.atom_sites}
    assert actual == row['sites'], (
        'Every special and general site receives its ITA letter in the stated setting'
    )
    assert structure.space_group.it_number == row['group'], (
        'Wyckoff inference retains the published space group'
    )


@pytest.mark.parametrize('factory', ['from_cif_str', 'from_cif_path'])
def test_a_supplied_letter_is_kept_instead_of_reclassified(tmp_path, factory):
    text = (HERE / REFERENCES['tbti']['file']).read_text()
    # Deliberately explicit: precedence is observable even if coordinates suggest d.
    text = text.replace('0.53(2) d', '0.53(2) a')
    structure = imported(tmp_path, text, factory)
    sites = {str(site.id): site for site in structure.atom_sites}
    assert sites['Tb'].wyckoff_letter == 'a', (
        'An explicit CIF Wyckoff letter takes precedence over coordinate inference'
    )
    assert {key: sites[key].wyckoff_letter for key in ['Ti', 'O1', 'O2']} == {
        'Ti': 'c',
        'O1': 'f',
        'O2': 'b',
    }, 'Every supplied published letter survives loading'


@pytest.mark.parametrize('reference', REFERENCES, ids=list(REFERENCES))
@pytest.mark.parametrize('notation', ['dot', 'underscore'])
@pytest.mark.parametrize('factory', ['from_cif_str', 'from_cif_path'])
def test_every_cif_import_saves_wyckoff_values_that_the_edi_loader_accepts(
    tmp_path, reference, notation, factory
):
    row = REFERENCES[reference]
    text = cif_text(row, notation, 'absent')
    structure = imported(tmp_path, text, factory)
    api = importlib.import_module('edi')
    project = api.Project.load(ROOT / 'tests/fixtures/loop_parameter_ids/line-segment')
    gemmi = importlib.import_module('gemmi')
    name = gemmi.cif.read_string(text).sole_block().name
    project.structures.add(structure)
    destination = tmp_path / 'saved'
    project.save_as(destination)
    # Reopening comes before the letter assertion: a refused `.` must reach this boundary.
    restored = api.Project.load(destination)
    direct = api.StructureFactory.from_cif_path(destination / 'structures' / (name + '.edi'))
    for reopened in [restored.structures[name], direct]:
        actual = {str(site.id): site.wyckoff_letter for site in reopened.atom_sites}
        assert actual == row['sites'], (
            'Every imported CIF saves valid EDI letters through both project and structure loaders'
        )
