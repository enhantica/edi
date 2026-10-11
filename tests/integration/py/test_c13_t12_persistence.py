"""E13-E16/E18-E19: independently supplied identities and dictionary slots."""

import pytest
from c13_t12_support import (
    BAD_IDS,
    BAD_NAMES,
    SPELLINGS,
    case_id,
    engine,
    loops,
    named,
    project,
    snapshot,
    tokens,
)


@pytest.mark.parametrize(('value', 'spelling'), SPELLINGS, ids=case_id)
def test_identity_spelling_and_exact_roundtrip(tmp_path, value, spelling):
    model = project(tmp_path / 'input')
    model.structure.atom_sites[0].id = value
    model.save_as(tmp_path / 'saved')
    text = (tmp_path / 'saved/structures/structure.edi').read_text()
    lexemes = tokens(text)
    start = next(i for i, token in enumerate(lexemes) if token[0] == '_atom_site.id')
    while lexemes[start][0].startswith('_'):
        start += 1
    assert lexemes[start][0] == spelling, ' writer must obey the hand-written CIF spelling table'
    restored = engine.Project.load(tmp_path / 'saved')
    assert [s.id for s in restored.structure.atom_sites] == [value, 'Y'], (
        ' decoding and encoding each occur once; literal quotes remain part of identity'
    )


@pytest.mark.parametrize('literal', ["'X'", '"X"', 'a\'b"c', '_x', 'data_a', 'loop_'])
@pytest.mark.parametrize('route', ['edi-text', 'cif-text'])
def test_distinct_literal_quotes_and_control_like_ids_load(literal, route):
    # Spell supplied values with the opposite delimiter, never a product encoder.
    spelling = '"' + literal + '"' if "'" in literal else "'" + literal + "'"
    structure, _, _, _ = loops._texts('atom_site')
    structure = structure.replace('Y Gd ', spelling + ' Gd ')
    if route == 'cif-text':
        structure = loops._cif(structure, 'structure')
    loaded = engine.StructureFactory.from_cif_str(structure)
    assert [s.id for s in loaded.atom_sites] == ['X', literal], (
        ' file readers preserve literal quotes and quoted control-like values'
    )


@pytest.mark.parametrize('category', ['background', 'excluded_region', 'data'])
def test_declared_ids_obey_stored_and_ordinal_category_contract(tmp_path, category):
    model = loops._load(tmp_path / 'input', category, 'project')[0]
    model.save_as(tmp_path / 'saved')
    text = (tmp_path / 'saved/experiments/experiment.edi').read_text()
    lexemes = tokens(text)
    key = '_' + category + '.id'
    key_at = next(i for i, token in enumerate(lexemes) if token[0] == key)
    start = key_at
    while start > 0 and lexemes[start - 1][0].startswith('_'):
        start -= 1
    column = key_at - start
    tags = []
    while lexemes[start][0].startswith('_'):
        tags.append(lexemes[start][0])
        start += 1
    actual = [lexemes[start + column + i * len(tags)][1] for i in range(2)]
    expected = {
        'background': ['p17', 'p93'],
        'excluded_region': ['r17', 'r93'],
        'data': ['1', '2'],
    }[category]
    assert actual == expected, (
        'Background and exclusion keys are stored; measured rows retain one-based ordinal identity'
    )
    restored = engine.Project.load(tmp_path / 'saved')
    restored.save_as(tmp_path / 'saved-again')
    again = tokens((tmp_path / 'saved-again/experiments/experiment.edi').read_text())
    key_at = next(i for i, token in enumerate(again) if token[0] == key)
    start = key_at
    while start > 0 and again[start - 1][0].startswith('_'):
        start -= 1
    column = key_at - start
    while again[start][0].startswith('_'):
        start += 1
    assert [again[start + column + i * len(tags)][1] for i in range(2)] == expected, (
        'Both stored and ordinal identities must survive the complete save/load/save boundary'
    )


def test_fit_state_uses_literal_dictionary_slots_and_undo(tmp_path):
    model = project(tmp_path / 'input')
    instrument = model.experiments[0].instrument
    instrument.calib_sample_displacement = engine.Parameter(0.23)
    a, b = instrument.calib_twotheta_offset, instrument.calib_sample_displacement
    a.start_value, b.start_value = 0.17, 0.29
    a.start_uncertainty, b.start_uncertainty = 0.003, 0.007
    if hasattr(a, '_label'):
        a._label.name = 'calib_sample_displacement'
    model.save_as(tmp_path / 'saved')
    text = (tmp_path / 'saved/analysis/analysis.edi').read_text()
    expected = {'experiment.calib_twotheta_offset', 'experiment.calib_sample_displacement'}
    rows = [line.split()[0] for line in text.splitlines() if line.startswith('experiment.')]
    assert len(rows) == len(expected), ' fit state cannot emit duplicate slot rows'
    assert set(rows) == expected, (
        ' F5 fit-state ids come from dictionary spellings, never editable display labels'
    )
    restored = engine.Project.load(tmp_path / 'saved')
    restored._undo_fit()
    restored_instrument = restored.experiments[0].instrument
    assert restored_instrument.calib_twotheta_offset.value == pytest.approx(0.17), (
        ' offset snapshot must retain its own slot through save/load/undo'
    )
    assert restored_instrument.calib_sample_displacement.value == pytest.approx(0.29), (
        ' displacement snapshot must retain its own slot through save/load/undo'
    )


@pytest.mark.parametrize('name', BAD_NAMES, ids=case_id)
@pytest.mark.parametrize('kind', ['structure', 'experiment'])
def test_persisted_name_refuses_before_publication(tmp_path, name, kind):
    model = project(tmp_path / 'input')
    getattr(model, kind).name = name
    destination = tmp_path / 'published'
    destination.mkdir()
    (destination / 'sentinel').write_bytes(b'unchanged destination\x00')
    before = snapshot(tmp_path)
    named(lambda: model.save_as(destination), name)
    assert snapshot(tmp_path) == before, (
        ' domain refusal leaves destination and staging listing unchanged'
    )


@pytest.mark.parametrize('name', ['wish_1_10', '1000236', 'pd-neut', '_x', ''])
def test_persisted_name_positive_controls(tmp_path, name):
    model = project(tmp_path / 'input')
    model.experiments[0].name = name
    model.experiments[0].instrument.calib_twotheta_offset.start_value = 0.17
    model.save_as(tmp_path / 'saved')
    key = name or 'experiment'
    assert (tmp_path / 'saved/experiments' / (key + '.edi')).is_file(), (
        ' the canonical datablock key supplies the persisted stem'
    )
    restored = engine.Project.load(tmp_path / 'saved')
    bank = next(bank for bank in restored.experiments if bank.name == key)
    assert bank.name == key, ' unnamed experiment reloads under its canonical key'
    assert bank.instrument.calib_twotheta_offset.start_value == pytest.approx(0.17), (
        ' canonical bank key agrees with the persisted fit-state prefix'
    )


def test_case_fold_collision_is_atomic_at_save(tmp_path):
    model = project(tmp_path / 'input')
    model.experiments[0].name, model.experiments[1].name = 'Bank', 'bank'
    before = snapshot(tmp_path)
    message = named(lambda: model.save_as(tmp_path / 'saved'), 'bank')
    assert 'Bank' in message, ' case-fold refusal names both colliding entities'
    assert snapshot(tmp_path) == before, ' case-fold refusal precedes staging or publication'


@pytest.mark.parametrize(('_rule', 'value'), BAD_IDS, ids=case_id)
# Before: a site-id refusal was counted as fit-state encoder coverage. After:
# this is publication safety; the native encoder/routing gates prove E19's seam.
@pytest.mark.parametrize('family', ['site', 'scattering', 'site-with-fit-state'])
def test_unrepresentable_model_id_refuses_save_atomically(tmp_path, _rule, value, family):
    model = project(tmp_path / 'input')
    if family == 'scattering':
        model.structure.scattering_lengths_fm = {value: 6.1}
    else:
        model.structure.atom_sites[0].id = value
        if family == 'site-with-fit-state':
            model.structure.atom_sites[0].fract_x.start_value = 0.17
    before = snapshot(tmp_path)
    with pytest.raises((ValueError, RuntimeError)) as caught:
        model.save_as(tmp_path / 'saved')
    message = str(caught.value)
    assert any(word in message.lower() for word in ('id', 'key', 'identity', 'scattering')), (
        ' domain refusal identifies the identity family'
    )
    assert any(
        word in message.lower()
        for word in (
            'character',
            'ascii',
            'control',
            'represent',
            'line',
            'quote',
            '0x',
            '\\u',
            '\\x',
        )
    ), ' domain refusal names the character or spelling rule'
    assert snapshot(tmp_path) == before, (
        ' invalid identity cannot publish or leave a staging directory'
    )


@pytest.mark.parametrize('category', list(loops.ROWS))
# LF/CR break the line grammar before decoded-cell construction; separate below.
@pytest.mark.parametrize(('rule', 'value'), BAD_IDS[2:6])
def test_unrepresentable_identity_refuses_at_load(tmp_path, category, rule, value):
    structure, experiment, analysis, original = loops._texts(category)
    location = loops.ROWS[category][0]
    values = {'structure': structure, 'experiment': experiment, 'analysis': analysis}
    # Only the first identity field of the supplied category changes.
    target, _ = loops._loop(category)
    changed = target.replace('\n' + original + ' ', '\n"' + value + '" ', 1)
    values[location] = values[location].replace(target, changed)
    root = tmp_path / 'input'
    for folder, filename, content in [
        ('structures', 'structure', values['structure']),
        ('experiments', 'experiment', values['experiment']),
        ('analysis', 'analysis', values['analysis']),
    ]:
        (root / folder).mkdir(parents=True, exist_ok=True)
        (root / folder / (filename + '.edi')).write_text(content)
    with pytest.raises((ValueError, RuntimeError)) as caught:
        engine.Project.load(root)
    assert category in str(caught.value) or rule.lower() in str(caught.value).lower(), (
        ' load refusal names the affected category or forbidden character rule'
    )
    assert any(
        word in str(caught.value).lower()
        for word in (
            'character',
            'ascii',
            'control',
            'represent',
            '0x',
            '\\x',
            '\\n',
            '\\r',
            'newline',
            'single-line',
            'non-printable',
        )
    ), ' unrelated link or slot failure cannot replace a character-domain refusal'


def test_single_line_text_field_identity_roundtrips_and_multiline_refuses(tmp_path):
    structure, _, _, _ = loops._texts('atom_site')
    single = structure.replace('Y Gd ', ';text field\n;\nGd ')
    loaded = engine.StructureFactory.from_cif_str(single)
    assert [site.id for site in loaded.atom_sites] == ['X', 'text field'], (
        ' single-line CIF text-field identity decodes to its exact value'
    )
    model = project(tmp_path / 'input')
    model.structure = loaded
    model.save_as(tmp_path / 'saved')
    assert [site.id for site in engine.Project.load(tmp_path / 'saved').structure.atom_sites] == [
        'X',
        'text field',
    ], ' a single-line text-field identity saves with canonical single-line quoting'


def test_multiline_text_field_identity_refuses_at_load():
    structure, _, _, _ = loops._texts('atom_site')
    multiline = structure.replace('Y Gd ', ';two\nlines\n;\nGd ')
    with pytest.raises((ValueError, RuntimeError)) as caught:
        engine.StructureFactory.from_cif_str(multiline)
    assert 'atom_site' in str(caught.value), (
        ' multiline identity load refusal must name the category'
    )


@pytest.mark.parametrize('category', list(loops.ROWS))
@pytest.mark.parametrize(('rule', 'value'), BAD_IDS[:2])
def test_malformed_multiline_identity_refuses_in_parser(tmp_path, category, rule, value):
    structure, experiment, analysis, original = loops._texts(category)
    location = loops.ROWS[category][0]
    values = {'structure': structure, 'experiment': experiment, 'analysis': analysis}
    # Only the first identity field of the supplied category changes.
    target, _ = loops._loop(category)
    changed = target.replace('\n' + original + ' ', '\n"' + value + '" ', 1)
    values[location] = values[location].replace(target, changed)
    root = tmp_path / 'input'
    for folder, filename, content in [
        ('structures', 'structure', values['structure']),
        ('experiments', 'experiment', values['experiment']),
        ('analysis', 'analysis', values['analysis']),
    ]:
        (root / folder).mkdir(parents=True, exist_ok=True)
        (root / folder / (filename + '.edi')).write_text(content)
    with pytest.raises((ValueError, RuntimeError)) as caught:
        engine.Project.load(root)
    assert category in str(caught.value) or rule.lower() in str(caught.value).lower(), (
        ' load refusal names the affected category or forbidden character rule'
    )
    assert any(
        word in str(caught.value).lower()
        for word in ('line', '0x0a', '0x0d', 'newline', 'carriage')
    ), ' malformed LF/CR input is refused by the parser with its line rule named'


@pytest.mark.parametrize('spelling', ['t17', "'t17'", '"t17"'])
def test_declared_extract_identity_decodes_once_and_saves_canonically(tmp_path, spelling):
    model = loops._load(tmp_path / 'input', 'sequential_fit_extract', 'project')[0]
    path = tmp_path / 'input/analysis/analysis.edi'
    text = path.read_text().replace('t17 temperature', spelling + ' temperature')
    path.write_text('_sequential_fit.data_dir scan\n' + text)
    (tmp_path / 'input/scan').mkdir()
    (tmp_path / 'input/scan/point.txt').write_text('TEMP 123\n')
    model = engine.Project.load(tmp_path / 'input')
    model.save_as(tmp_path / 'saved')
    text = (tmp_path / 'saved/analysis/analysis.edi').read_text()
    lexemes = tokens(text)
    start = next(i for i, token in enumerate(lexemes) if token[0] == '_sequential_fit_extract.id')
    while lexemes[start][0].startswith('_'):
        start += 1
    assert lexemes[start][0] == 't17', (
        ' declared extract rules use a decoded model key and one canonical encoder'
    )


# F6: positive token observations exercise each real writer after all earlier
# validators have passed. Values come from the file, not a non-consumed field.
def test_every_writer_encodes_the_actual_identity_source(tmp_path):
    structure, experiment, _, _ = loops._texts('preferred_orientation')
    structure = structure.replace('data_structure', 'data__phase')
    structure = structure.replace('X Gd ', "'site a' Gd ")
    structure += (
        "loop_\n_scattering_length.type_symbol\n_scattering_length.length_fm\n'_scatter' 6.1\n"
    )
    experiment = experiment.replace('data_experiment', 'data__bank')
    experiment = experiment.replace('\nstructure ', "\n'_phase' ")
    analysis = """_sequential_fit.data_dir scan
loop_
_sequential_fit_extract.id
_sequential_fit_extract.target
_sequential_fit_extract.pattern
_sequential_fit_extract.required
'_extract' temperature '(.*)' true
loop_
_fit_parameter.id
_fit_parameter.start_value
_fit_parameter.start_uncertainty
'structure.site a.fract_x' 0.17 .
"""
    source = tmp_path / 'input'
    for path, text in [
        ('structures/_phase.edi', structure),
        ('experiments/_bank.edi', experiment),
        ('analysis/analysis.edi', analysis),
        ('scan/point.txt', 'TEMP 123\n'),
    ]:
        target = source / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(text)
    model = engine.Project.load(source)
    model.save_as(tmp_path / 'saved')
    expected = {
        ('structures/_phase.edi', '_atom_site.id'): "'site a'",
        ('structures/_phase.edi', '_scattering_length.type_symbol'): "'_scatter'",
        ('experiments/_bank.edi', '_linked_structure.structure_id'): "'_phase'",
        ('experiments/_bank.edi', '_preferred_orientation.structure_id'): "'_phase'",
        ('analysis/analysis.edi', '_sequential_fit_extract.id'): "'_extract'",
        ('analysis/analysis.edi', '_joint_fit.experiment_id'): "'_bank'",
        ('analysis/analysis.edi', '_fit_parameter.id'): "'structure.site a.fract_x'",
    }
    for (file, tag), spelling in expected.items():
        cells = tokens((tmp_path / 'saved' / file).read_text())
        at = next(i for i, token in enumerate(cells) if token[0] == tag)
        while cells[at][0].startswith('_'):
            at += 1
        assert cells[at][0] == spelling, (
            ' each actual writer encodes its canonical declared or composed source'
        )
