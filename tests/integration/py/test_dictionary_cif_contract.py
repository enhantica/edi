"""Published CIF numbers, official names and gemmi judge both import paths and export."""

import importlib
import json
import shutil
from pathlib import Path

import pytest

from tests.fixtures.dictionary_display.constrained import project_input

ROOT = Path(__file__).resolve().parents[3]


def engine():
    return importlib.import_module('edi')


def save_cif(project, target):
    folder = target.with_suffix('')
    project.save_as(folder)
    project.report.save_cif()
    written = list((folder / 'reports').glob('*.cif'))
    assert len(written) == 1, 'The CIF writer creates exactly one report in the saved project'
    return written[0]


def test_report_cif_is_parsed_independently_with_official_names(tmp_path):
    project = engine().Project.load(ROOT / 'tests/fixtures/loop_parameter_ids/line-segment')
    assert hasattr(project.report, 'save_cif'), (
        'The report exposes the committed CIF writer counterpart'
    )
    destination = tmp_path / 'report.cif'
    destination = save_cif(project, destination)
    gemmi = importlib.import_module('gemmi')

    document = gemmi.cif.read_file(str(destination))
    assert len(document) >= 2, (
        'The independently parsed report has structure and experiment blocks'
    )
    tags = []
    for block in document:
        for item in block:
            tags.extend(
                [item.pair[0]]
                if item.pair is not None
                else item.loop.tags
                if item.loop is not None
                else []
            )
    structure_block = next(block for block in document if block.find_value('_cell.length_a'))
    # Gemmi's small-structure converter accepts DDL1 only; its CIF parser accepts both.
    assert gemmi.cif.as_number(structure_block.find_value('_cell.length_a')) == pytest.approx(
        4.1
    ), 'The CIF report preserves the independent input cell'
    labels = list(structure_block.find_values('_atom_site.label'))
    assert labels == ['A', 'B'], 'The CIF report preserves every independent input site identity'
    assert gemmi.cif.as_number(
        structure_block.find_values('_atom_site.fract_x')[0]
    ) == pytest.approx(0.17), (
        'The CIF report preserves a nontrivial independent input fractional coordinate'
    )
    assert '_cell.length_a' in tags, 'The CIF report writes the DDLm default cell name'
    assert '_pd_phase_block.id' in tags, (
        'The report links structure and experiment blocks through pdCIF phase IDs'
    )
    official = json.loads(
        (ROOT / 'tests/fixtures/dictionary_display/structure_names.json').read_text()
    )['official_defaults']
    assert all(tag in official or tag.startswith('_edi_') for tag in tags), (
        'Every exported CIF tag is an official definition or an EDI extension'
    )
    assert not any('_structure_curve' in tag for tag in tags), (
        'The CIF report excludes the per-structure curve arrays'
    )


def test_edi_alias_loads_and_only_current_name_is_written(tmp_path):
    source = tmp_path / 'input'
    shutil.copytree(ROOT / 'tests/fixtures/loop_parameter_ids/line-segment', source)
    experiment = source / 'experiments/bank.edi'
    text = experiment.read_text().replace('phase 0.7', 'phase 2.3')
    assert '_linked_structure.scale' in text, (
        'The alias witness reaches a real linked structure scale column'
    )
    experiment.write_text(text.replace('_linked_structure.scale', '_scale.value'))
    loaded = engine().Project.load(source)
    assert loaded.experiments['bank'].linked_structures[0].scale.value == pytest.approx(2.3), (
        'The accepted EDI alias preserves the hand-written nondefault scale value'
    )
    destination = tmp_path / 'saved'
    loaded.save_as(destination)
    saved = (destination / 'experiments/bank.edi').read_text()
    assert '_linked_structure.scale' in saved, (
        'A listed EDI alias reads successfully and only the current name is written back'
    )
    assert '_scale.value' not in saved, (
        'A listed EDI alias reads successfully and only the current name is written back'
    )


@pytest.mark.parametrize('upper', [False, True])
def test_two_edi_spellings_of_one_item_are_refused_with_both_names(upper):
    tag = '_cell.LENGTH_A' if upper else '_cell.length_a'
    fixture = ROOT / 'tests/fixtures/loop_parameter_ids/line-segment/structures/phase.edi'
    text = fixture.read_text()
    text = text.replace('_cell.length_a 4.1', '_cell.length_a 4.1\n' + tag + ' 4.21')
    with pytest.raises(ValueError, match=r'(?i)cell|duplicate|spelling') as failure:
        engine().StructureFactory.from_cif_str(text)
    assert '_cell.length_a' in str(failure.value).lower(), (
        'Duplicate case-insensitive EDI spellings are refused with their conflicting item names'
    )


def test_distinct_edi_aliases_of_one_item_are_refused_together(tmp_path):
    source = tmp_path / 'input'
    shutil.copytree(ROOT / 'tests/fixtures/loop_parameter_ids/line-segment', source)
    record = source / 'experiments/bank.edi'
    text = record.read_text().replace(
        '_linked_structure.scale\nphase 0.7',
        '_linked_structure.scale\n_scale.value\nphase 0.7 2.3',
    )
    record.write_text(text)
    with pytest.raises(ValueError, match=r'(?i)scale') as failure:
        engine().Project.load(source)
    message = str(failure.value)
    assert '_linked_structure.scale' in message, 'Duplicate aliases name the current EDI spelling'
    assert '_scale.value' in message, (
        'Duplicate aliases also name the conflicting old EDI spelling'
    )


@pytest.mark.parametrize(
    ('kind', 'tag', 'value'),
    [
        ('Biso', '_atom_site.B_iso_or_equiv', 0.52),
        ('Uiso', '_atom_site.U_iso_or_equiv', 0.0066),
    ],
)
def test_cif_export_uses_the_native_adp_variant_without_conversion(tmp_path, kind, tag, value):
    project = engine().Project.load(ROOT / 'tests/fixtures/loop_parameter_ids/line-segment')
    for site in project.structures['phase'].atom_sites:
        site.adp_type = kind
        site.adp_iso.value = value
    assert hasattr(project.report, 'save_cif'), 'The report exposes its CIF writer counterpart'
    path = tmp_path / 'adp.cif'
    path = save_cif(project, path)
    gemmi = importlib.import_module('gemmi')
    document = gemmi.cif.read_file(str(path))
    block = next(block for block in document if block.find_value('_cell.length_a'))
    values = list(block.find_values(tag))
    assert len(values) == 2, 'Each input ADP is written under its own official native variant name'
    assert all(gemmi.cif.as_number(text) == pytest.approx(value) for text in values), (
        'Every native ADP magnitude is preserved without a B to U conversion'
    )


@pytest.mark.parametrize('with_su', [False, True])
def test_cif_export_marks_a_constrained_occupancy_and_keeps_its_uncertainty(tmp_path, with_su):
    project = engine().Project.load(project_input(tmp_path / 'input', with_su=with_su))
    project.analysis.calculate()
    parameter = project.structures['phase'].atom_sites[1].occupancy
    assert parameter.value == pytest.approx(0.42), (
        'The complement constraint reaches its independent value'
    )
    assert not parameter.free, 'The complement occupancy is dependent before CIF publication'
    assert hasattr(project.report, 'save_cif'), 'The report exposes its CIF writer counterpart'
    path = tmp_path / 'constraint.cif'
    path = save_cif(project, path)
    gemmi = importlib.import_module('gemmi')
    document = gemmi.cif.read_file(str(path))
    block = next(block for block in document if block.find_value('_cell.length_a'))
    labels = list(block.find_values('_atom_site.label'))
    index = labels.index('B')
    flag = block.find_values('_atom_site.refinement_flags_occupancy')[index]
    assert 'P' in flag, 'The CIF report publishes the official site occupancy constraint flag'
    value = block.find_values('_atom_site.occupancy')[index]
    assert value == ('0.42(3)' if with_su else '0.42'), (
        'The CIF report preserves the complement value and its declared propagated uncertainty'
    )


def test_cif_symmetry_fixed_special_positions_are_decimal_without_su_and_flagged(tmp_path):
    source = project_input(tmp_path / 'input')
    structure = source / 'structures/phase.edi'
    text = structure.read_text().replace('"P 1"', '"P 63/m m c"')
    text = text.replace('_cell.length_c 4.1', '_cell.length_c 5.3')
    text = text.replace('_cell.angle_gamma 90', '_cell.angle_gamma 120')
    for label, occupancy, adp in [('A', '0.58', '0.3'), ('B', '0.3', '0.8')]:
        original = f'{label} La a Biso 0.17 0.23 0.31 {occupancy} {adp}'
        assert original in text, (
            'The special-position witness reaches its independently written P1 row'
        )
        text = text.replace(
            original,
            f'{label} La c Biso 0.3333333333333333 0.6666666666666666 0.25 {occupancy} {adp}',
        )
    structure.write_text(text)
    project = engine().Project.load(source)
    assert hasattr(project.report, 'save_cif'), 'The report exposes its CIF writer counterpart'
    destination = tmp_path / 'special.cif'
    destination = save_cif(project, destination)
    gemmi = importlib.import_module('gemmi')
    document = gemmi.cif.read_file(str(destination))
    block = next(block for block in document if block.find_value('_cell.length_a'))
    index = list(block.find_values('_atom_site.label')).index('A')
    for name, expected in [('fract_x', 1 / 3), ('fract_y', 2 / 3), ('fract_z', 1 / 4)]:
        token = block.find_values('_atom_site.' + name)[index]
        assert '(' not in token, 'A symmetry-fixed coordinate has no published uncertainty'
        assert gemmi.cif.as_number(token) == pytest.approx(expected, abs=1e-12), (
            'CIF decimal numbers retain the International Tables special positions'
        )
    assert 'S' in block.find_values('_atom_site.refinement_flags_posn')[index], (
        'The CIF report publishes the official special-position constraint flag'
    )


def test_edi_atom_label_alias_writes_only_the_current_site_id_name(tmp_path):
    source = tmp_path / 'input'
    shutil.copytree(ROOT / 'tests/fixtures/loop_parameter_ids/line-segment', source)
    path = source / 'structures/phase.edi'
    path.write_text(path.read_text().replace('_atom_site.id', '_atom_site.label'))
    project = engine().Project.load(source)
    assert [str(site.id) for site in project.structures['phase'].atom_sites] == ['A', 'B'], (
        'The accepted atom-label EDI alias retains each independent input row identity'
    )
    destination = tmp_path / 'saved'
    project.save_as(destination)
    text = (destination / 'structures/phase.edi').read_text()
    assert '_atom_site.id' in text, (
        'An accepted old atom-label spelling writes the current EDI item name'
    )
    assert '_atom_site.label' not in text, (
        'An accepted old atom-label spelling is never written back as a deprecated name'
    )


@pytest.mark.parametrize(('kind', 'prefix'), [('Bani', 'B'), ('Uani', 'U'), ('beta', 'beta')])
def test_cif_export_preserves_each_native_anisotropic_tensor(tmp_path, kind, prefix):
    source = tmp_path / 'input'
    shutil.copytree(ROOT / 'tests/fixtures/loop_parameter_ids/line-segment', source)
    path = source / 'structures/phase.edi'
    text = path.read_text().replace('A La a Biso', 'A La a ' + kind)
    components = ['11', '22', '33', '12', '13', '23']
    values = [0.0123456, 0.0234567, 0.0345678, 0.0012345, 0.0023456, 0.0034567]
    text += '\nloop_\n_atom_site_aniso.id\n'
    text += ''.join('_atom_site_aniso.adp_' + name + '\n' for name in components)
    text += 'A ' + ' '.join(str(value) for value in values) + '\n'
    path.write_text(text)
    project = engine().Project.load(source)
    assert hasattr(project.report, 'save_cif'), 'The report exposes its CIF writer counterpart'
    destination = save_cif(project, tmp_path / 'tensor.cif')
    gemmi = importlib.import_module('gemmi')
    block = next(
        b for b in gemmi.cif.read_file(str(destination)) if b.find_value('_cell.length_a')
    )
    labels = list(block.find_values('_atom_site_aniso.label'))
    assert labels == ['A'], 'Only the independently declared anisotropic site has a tensor row'
    for component, expected in zip(components, values, strict=True):
        tag = '_atom_site_aniso.' + prefix + '_' + component
        column = block.find_values(tag)
        assert len(column) == 1, 'Each native tensor component uses its matching official ADP name'
        assert gemmi.cif.as_number(column[0]) == pytest.approx(expected, abs=1e-12), (
            'CIF publication preserves each native tensor magnitude without convention conversion'
        )
