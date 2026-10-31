"""CIF declarations are settled only against the finished, saved model."""

import importlib
import math
import re
import warnings
from operator import itemgetter

import pytest
import yaml

from tests.fixtures import cif_import_cases as case

ROUTES = ['factory-str', 'factory-path', 'project']
if case.API == 'edi':
    ROUTES += ['collection-str', 'collection-path', 'collection-edi-path']


@pytest.mark.parametrize('route', ROUTES)
@pytest.mark.parametrize('kind', ['structure', 'experiment'])
@pytest.mark.parametrize('shape', ['item', 'column'])
@pytest.mark.parametrize('row', case.inventory(), ids=itemgetter('uid'))
def test_every_item_alias_variant_and_absence_has_a_saved_outcome(
    tmp_path, capfd, route, kind, shape, row
):
    errors = []
    for i, name in enumerate(row['cif_names']):
        for style, spelling in enumerate(dict.fromkeys([name, name.replace('.', '_', 1).upper()])):
            for j, value in enumerate([case.token(row), '?', '.', "'?'", "''"]):
                text = case.payload(kind, row, spelling, shape, value)
                assert case.key(spelling) in case.columns(text), (
                    'Each inventory probe is present in the actual CIF input'
                )
                capfd.readouterr()
                result = case.observe(
                    kind,
                    text,
                    tmp_path / f'{i}-{style}-{j}',
                    route,
                    '.edi' if route == 'collection-edi-path' else '.cif',
                )
                result['notes'] += capfd.readouterr().err.splitlines()
                try:
                    case.accounted(
                        result,
                        spelling,
                        value,
                        row['edi_names'][0],
                        count=2 if shape == 'column' else 1,
                    )
                except AssertionError as error:
                    errors.append(f'{spelling} {value}: {error}')
    assert not errors, (
        'Every declaration reaches a saved value or a named terminal outcome: ' + repr(errors)
    )


@pytest.mark.parametrize('route', ROUTES)
@pytest.mark.parametrize('kind', ['structure', 'experiment'])
def test_unknown_and_mixed_columns_are_reported_once_per_block(tmp_path, capfd, route, kind):
    text = case.STRUCTURE if kind == 'structure' else case.EXPERIMENT
    text += (
        '\n_audit.external_note payload\nloop_\n_unknown.one\n'
        '_cell.unlisted\n_unknown.absent\nleft right ?\n'
    )
    capfd.readouterr()
    result = case.observe(kind, text, tmp_path, route)
    result['notes'] += capfd.readouterr().err.splitlines()
    assert 'refused' not in result, (
        'Unknown publication metadata preserves an otherwise valid input'
    )
    for name, value in [
        ('_audit.external_note', 'payload'),
        ('_unknown.one', 'left'),
        ('_cell.unlisted', 'right'),
    ]:
        case.accounted(result, name, value, name)


@pytest.mark.parametrize('route', ROUTES)
@pytest.mark.parametrize('kind', ['structure', 'experiment'])
@pytest.mark.parametrize('layout', ['next-line', 'split-row', 'comment', 'semicolon'])
def test_cif_grammar_has_one_reader_even_with_an_edi_suffix(tmp_path, route, kind, layout):
    text = case.STRUCTURE if kind == 'structure' else case.EXPERIMENT
    if layout == 'next-line':
        text = text.replace('_cell_length_a 5.1000', '_cell_length_a\n5.1000').replace(
            'value 1.5406', 'value\n1.5406'
        )
    elif layout == 'split-row':
        text = text.replace('0.23000 0.31000', '0.23000\n0.31000').replace('11 24 3', '11\n24 3')
    elif layout == 'comment':
        text = text.replace('0.52000\n', '0.52000 # published row\n').replace(
            '11 24 3', '11 24 3 # point'
        )
    else:
        text += '_audit.note\n;A published\ntext field\n;\n'
    result = case.observe(kind, text, tmp_path, route, '.edi')
    assert 'refused' not in result, (
        'CIF whitespace, row wrapping and text fields are read by their content'
    )
    name, expected = (
        ('_cell.length_a', '5.1000')
        if kind == 'structure'
        else ('_instrument.setup_wavelength', '1.5406')
    )
    assert case.same(result['cells'][case.key(name)][0], expected), (
        'The chosen CIF reader preserves its nontrivial model value'
    )


@pytest.mark.parametrize('route', ROUTES)
@pytest.mark.parametrize('kind', ['structure', 'experiment'])
@pytest.mark.parametrize(
    'tail',
    [
        "_audit.note 'unterminated",
        'save_frame\n_audit.note x\nsave_',
        'global_\n_audit.note x',
        'stop_',
        '_audit.note [1 2]',
        'loop_\n_unknown.a\n_unknown.b\n1 2 3',
    ],
    ids=['quote', 'save-frame', 'global', 'stop', 'cif2-list', 'incomplete-loop'],
)
def test_chosen_parser_failure_refuses_without_partial_import(tmp_path, route, kind, tail):
    text = (case.STRUCTURE if kind == 'structure' else case.EXPERIMENT) + tail + '\n'
    result = case.observe(kind, text, tmp_path, route)
    assert 'refused' in result, (
        'An unsupported or malformed CIF must not fall through to a permissive reader'
    )
    assert re.search(
        r'line|quote|loop|save_|global_|stop_|list|CIF2', result['refused'], re.IGNORECASE
    ), 'Parser refusals retain the grammar reason and its location'
    assert not (tmp_path / 'saved').exists(), 'A refused import writes no partial model'


@pytest.mark.parametrize('route', ROUTES)
@pytest.mark.parametrize(
    'control',
    [
        'precision',
        'symmetry',
        'rotation',
        'invalid-letter',
        'empty-letter',
        'placeholder',
        'two-blocks',
    ],
)
def test_named_accounting_controls_observe_the_finished_model(tmp_path, capfd, route, control):
    if control == 'precision':
        text = case.tensor(scalar='0.0200')
    elif control == 'symmetry':
        text = case.tensor('P m -3 m', scalar='0.0222')
    elif control == 'rotation':
        text = case.tensor('P m -3 m', moved=True)
    elif control in {'invalid-letter', 'empty-letter'}:
        letter = 'z' if control == 'invalid-letter' else "''"
        text = case.STRUCTURE.replace('Ba1 Ba a', 'Ba1 Ba ' + letter)
    elif control == 'placeholder':
        text = 'data_placeholder\n_cell_length_a ?\n' + case.STRUCTURE
    else:
        text = case.STRUCTURE + case.STRUCTURE.replace('data_witness', 'data_second')
    capfd.readouterr()
    result = case.observe('structure', text, tmp_path, route)
    result['notes'] += capfd.readouterr().err.splitlines()
    if control == 'two-blocks':
        assert 'refused' in result, 'Two structure blocks must refuse atomically'
        assert all(n in result['refused'] for n in ['witness', 'second']), (
            'Two structure blocks refuse atomically and identify both blocks'
        )
        return
    assert 'refused' not in result, (
        'Each valid accounting witness is imported into its finished model'
    )
    expected_tags = {
        'precision': ['_atom_site.U_iso_or_equiv'],
        'symmetry': [
            '_atom_site.U_iso_or_equiv',
            '_atom_site_aniso.U_22',
            '_atom_site_aniso.U_33',
        ],
        'rotation': ['_atom_site_aniso.U_13'],
        'invalid-letter': ['_atom_site_Wyckoff_symbol'],
        'empty-letter': ['_atom_site_Wyckoff_symbol'],
    }
    for tag in expected_tags.get(control, []):
        assert any(case.notices(n, tag) for n in result['notes']), (
            'Every disagreement is reported under the declaration name in its source frame: ' + tag
        )
    if control in {'precision', 'symmetry'}:
        expected = '0.0240' if control == 'precision' else '0.0111'
        assert case.same(result['cells'][case.key('_atom_site.adp_iso')][0], expected), (
            'The saved isotropic equivalent comes from the final tensor after symmetry'
        )
    if control == 'rotation':
        assert case.same(result['cells'][case.key('_atom_site_aniso.adp_13')][0], '0.0000'), (
            'The moved cubic site has zero off-diagonal displacement after symmetry'
        )
    if control == 'placeholder':
        assert any('placeholder' in n for n in result['notes']), (
            'An absence-only placeholder block is skipped with an explicit report'
        )


@pytest.mark.parametrize('route', ROUTES)
@pytest.mark.parametrize('form', ['U', 'B', 'beta'])
@pytest.mark.parametrize('group', ['P m -3 m', 'P 3 1 2'], ids=['cubic', 'hexagonal'])
@pytest.mark.parametrize('sparse', [False, True])
def test_source_frame_tensor_is_settled_by_the_inverse_lattice_operation(
    tmp_path, capfd, route, form, group, sparse
):
    # Sparse hexagonal tensors omit U12 and therefore do not claim isotropy.
    text = case.tensor(group, form, moved=True, sparse=sparse)
    capfd.readouterr()
    result = case.observe('structure', text, tmp_path, route)
    result['notes'] += capfd.readouterr().err.splitlines()
    assert 'refused' not in result, (
        'Full and sparse declared tensors reach the same saved-model boundary'
    )
    expected_type = {'U': 'Uani', 'B': 'Bani', 'beta': 'beta'}[form]
    assert case.decoded(result['cells'][case.key('_atom_site.adp_type')][0]) == expected_type, (
        'A supplied tensor retains its declared displacement form after import'
    )
    components = [
        float(result['cells'][case.key('_atom_site_aniso.adp_' + part)][0])
        for part in case.COMPONENTS
    ]
    assert all(math.isfinite(value) for value in components), (
        'A full or sparse tensor becomes a complete finite saved tensor rather than disappearing'
    )
    if group == 'P m -3 m' or not sparse:
        physical = [0.02, 0.02, 0.02, 0.01 if group == 'P 3 1 2' else 0, 0, 0]
        reciprocal = (
            [2 / (5 * math.sqrt(3)), 2 / (5 * math.sqrt(3)), 1 / 7]
            if group == 'P 3 1 2'
            else [0.2] * 3
        )
        pairs = [(0, 0), (1, 1), (2, 2), (0, 1), (0, 2), (1, 2)]
        expected = [
            value
            * (
                8 * math.pi**2
                if form == 'B'
                else 2 * math.pi**2 * reciprocal[i] * reciprocal[j]
                if form == 'beta'
                else 1
            )
            for value, (i, j) in zip(physical, pairs, strict=True)
        ]
        assert components == pytest.approx(expected, rel=1e-8, abs=1e-10), (
            'The final tensor agrees with the cubic or hexagonal '
            'isotropic closed form in its saved units'
        )
    if group == 'P 3 1 2' and not sparse:
        assert not any('not used' in n or 'not read' in n for n in result['notes']), (
            'An isotropic hexagonal tensor and moved coordinates agree '
            'in their source frame; a transpose gives false reports'
        )
        assert case.same(result['cells'][case.key('_atom_site.fract_x')][0], '0.3000'), (
            'The hexagonal representative retains its independent free coordinate'
        )
        assert case.same(
            result['cells'][case.key('_atom_site.fract_y')][0], '-0.3000'
        ) or case.same(result['cells'][case.key('_atom_site.fract_y')][0], '0.7000'), (
            'The moved site uses the ITA representative (x,-x,0) modulo lattice translations'
        )


@pytest.mark.parametrize('route', ROUTES)
@pytest.mark.parametrize('separate', ['35', '34'])
def test_measured_brackets_are_point_uncertainties_and_must_agree(tmp_path, route, separate):
    text = case.EXPERIMENT.replace('10 21 2', '10 1234(35) ' + separate)
    result = case.observe('experiment', text, tmp_path, route)
    if separate == '34':
        assert 'refused' in result, (
            'Conflicting bracket and explicit point uncertainties refuse the whole experiment'
        )
        assert '35' in result['refused'], 'The point-uncertainty refusal states the bracket value'
        assert '34' in result['refused'], (
            'The point-uncertainty refusal states both conflicting values'
        )
    else:
        assert 'refused' not in result, (
            'Agreeing measured-point uncertainty declarations are consumed'
        )
        assert result['cells'][case.key('_data.intensity_meas')][0] == '1234', (
            'Measured intensity retains the published central value'
        )
        assert result['cells'][case.key('_data.intensity_meas_su')][0] == '35', (
            'A measured bracket is retained as its point uncertainty'
        )


@pytest.mark.parametrize('route', ROUTES)
def test_published_parameter_is_fixed_without_a_saved_uncertainty(tmp_path, route):
    text = case.STRUCTURE.replace('5.1000', '5.1000(7)')
    result = case.observe('structure', text, tmp_path, route, '.edi')
    assert 'refused' not in result, (
        'A published CIF parameter reads through every content-selected entrance'
    )
    assert '(' not in result['cells'][case.key('_cell.length_a')][0], (
        'Published parameter uncertainties and free flags are not written as native fit semantics'
    )
    assert any(
        'length_a' in n and ('published' in n or 'uncertainty' in n or 's.u.' in n)
        for n in result['notes']
    ), 'Discarded published uncertainties are reported once under their original declaration'


@pytest.mark.parametrize('suffix', ['.CIF', '.cif'])
def test_project_members_use_case_insensitive_suffixes_and_edi_shadowing(tmp_path, capfd, suffix):
    api = importlib.import_module(case.API)
    source = case.project_input('structure', case.STRUCTURE, tmp_path, suffix)
    capfd.readouterr()
    with warnings.catch_warnings(record=True):
        warnings.simplefilter('always')
        project = api.Project.load(source)
        project.save_as(tmp_path / 'first')
    target = tmp_path / 'first/structures/witness.edi'
    assert target.is_file(), (
        'Uppercase and lowercase CIF members are discovered and '
        'regenerated as native entity documents'
    )
    assert not list((tmp_path / 'first').rglob('*.cif')), (
        'A project save regenerates CIF members as native documents'
    )
    native = target.read_text().replace('5.1', '5.9', 1)
    (source / 'structures/witness.edi').write_text(native)
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter('always')
        project = api.Project.load(source)
    notes = [str(w.message) for w in caught] + capfd.readouterr().err.splitlines()
    assert any('witness' + suffix in n and 'not read' in n for n in notes), (
        'A shadowed CIF member is named in the load report'
    )
    assert project.structures['witness'].cell.length_a.value == pytest.approx(5.9), (
        'The same-stem native file takes precedence over CIF'
    )


def test_observer_rejects_lookup_only_and_partial_column_escapes(tmp_path):
    result = case.observe(
        'experiment',
        case.EXPERIMENT + "_diffrn_source.facility 'Authored facility'\n",
        tmp_path,
    )
    assert 'refused' not in result, 'A supported facility declaration reaches the real reader'
    assert not any(case.notices(note, '_diffrn_source.facility') for note in result['notes']), (
        'The supported facility is consumed rather than reported unused'
    )
    assert [
        case.decoded(v) for v in result['cells'].get(case.key('_instrument.facility'), [])
    ] == ['Authored facility'], (
        'The saved model retains the facility after the real reader looks it up'
    )
    native = (
        (case.ROOT / 'tests/fixtures/loop_parameter_ids/line-segment/experiments/bank.edi')
        .read_text()
        .replace('data_bank', 'data_witness', 1)
    )
    for marker in ['', '_instrument.name ?\n_instrument.facility ?\n']:
        result = case.observe('experiment', native + '\n' + marker, tmp_path / str(len(marker)))
        assert 'refused' not in result, (
            'Optional instrument descriptions may be omitted or unknown'
        )
        for tag in ['_instrument.name', '_instrument.facility']:
            assert result['cells'].get(case.key(tag), [] if marker else ['?']) == ['?'], (
                'An unspecified instrument description is written as the unknown marker'
            )
    for found in [[], ['0.1'], ['0.271828', '0.1']]:
        with pytest.raises(AssertionError, match='saved column'):
            case.accounted(
                {'cells': {'_geom_bond_distance_incr': found}, 'notes': []},
                '_geom.bond_distance_incr',
                '0.271828',
                '_geom.bond_distance_incr',
            )


@pytest.mark.parametrize('method', ['from_cif_str', 'from_cif_path'])
@pytest.mark.parametrize(
    ('group', 'published', 'expected'),
    [('P 1', '0.0200', 0.0240), ('P m -3 m', '0.0222', 0.0111)],
    ids=['orthogonal', 'cubic-after-symmetry'],
)
def test_factory_returns_the_finished_tensor_equivalent_before_attachment(
    tmp_path, method, group, published, expected
):
    api = importlib.import_module(case.API)
    text = case.tensor(group, scalar=published)
    path = tmp_path / 'tensor.cif'
    path.write_text(text)
    obj = getattr(api.StructureFactory, method)(text if method.endswith('str') else path)
    assert obj.atom_sites[0].adp_iso.value == pytest.approx(expected, abs=1e-13), (
        'The factory returns the settled tensor equivalent before project attachment or save'
    )


@pytest.mark.parametrize('route', ROUTES)
def test_experiment_multiblock_selection_refuses_two_matching_blocks(tmp_path, route):
    text = case.EXPERIMENT + case.EXPERIMENT.replace('data_witness', 'data_second')
    result = case.observe('experiment', text, tmp_path, route)
    assert 'refused' in result, 'An experiment entrance refuses two experiment blocks atomically'
    assert all(n in result['refused'] for n in ['witness', 'second']), (
        'The experiment-block ambiguity refusal identifies both matching blocks'
    )


@pytest.mark.parametrize('marker', ['?', '.'])
def test_missing_wyckoff_is_inferred_but_a_supplied_charge_suffix_is_reported(tmp_path, marker):
    text = case.STRUCTURE.replace('Ba1 Ba a', 'Ba1 Ba ' + marker)
    result = case.observe('structure', text, tmp_path / 'absent')
    assert 'refused' not in result, 'An absent Wyckoff letter is inferred from the coordinates'
    assert case.decoded(result['cells'][case.key('_atom_site.wyckoff_letter')][0]) == 'a', (
        'A P1 coordinate lies on the sole ITA position a'
    )
    charged = case.STRUCTURE.replace('Ba1 Ba a', 'Ba1 Ca2+ a')
    result = case.observe('structure', charged, tmp_path / 'charge')
    assert 'refused' not in result, 'A charged type symbol retains its chemical element'
    assert case.decoded(result['cells'][case.key('_atom_site.type_symbol')][0]) == 'Ca', (
        'The type suffix does not change the independent calcium element'
    )
    assert any('Ca2+' in note and 'suffix' in note for note in result['notes']), (
        'A supplied charge suffix has its own explicit unused outcome'
    )


def test_each_dictionary_category_has_an_explicit_import_role():
    document = yaml.safe_load((case.source_root() / 'data/dictionary/parameters.yaml').read_text())
    categories = {row['category'] for row in case.inventory()}
    categories |= {row['id'] for row in document.get('categories', [])}
    source = case.source_root() / 'src/core/cif_import.cpp'
    assert source.is_file(), 'The CIF importer declares the role of every model category'
    text = source.read_text()
    assert 'kCifCategories' in text, (
        'One explicit category-role table guards importer population growth'
    )
    spelled = set(re.findall(r'"(_[A-Za-z0-9_]+)"', text))
    missing = {name for name in categories if '_' + name.lstrip('_') not in spelled}
    assert not missing, (
        'A new dictionary category without an explicit import role must refuse the census: '
        + repr(sorted(missing))
    )


@pytest.mark.parametrize('kind', ['structure', 'experiment'])
@pytest.mark.parametrize('method', ['str', 'cif-path', 'edi-path'])
def test_collection_refusal_keeps_the_original_saved_model(tmp_path, kind, method):
    api = importlib.import_module(case.API)
    project = api.Project.load(case.ROOT / 'tests/fixtures/loop_parameter_ids/line-segment')
    project.save_as(tmp_path / 'before')
    text = case.STRUCTURE if kind == 'structure' else case.EXPERIMENT
    text += text.replace('data_witness', 'data_second')
    table = project.structures if kind == 'structure' else project.experiments
    if method == 'str':
        call, argument = table.add_from_cif_str, text
    else:
        path = tmp_path / ('input.edi' if method == 'edi-path' else 'input.cif')
        path.write_text(text)
        call = getattr(table, 'add_from_' + ('edi' if method == 'edi-path' else 'cif') + '_path')
        argument = path
    with pytest.raises((ValueError, RuntimeError), match=r'witness|second|block'):
        call(argument)
    project.save_as(tmp_path / 'after')
    for folder in ['structures', 'experiments']:
        before = {p.name: p.read_bytes() for p in (tmp_path / 'before' / folder).glob('*.edi')}
        after = {p.name: p.read_bytes() for p in (tmp_path / 'after' / folder).glob('*.edi')}
        assert after == before, (
            'A refused collection import leaves every original entity unchanged'
        )
