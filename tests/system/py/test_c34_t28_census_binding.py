"""I14/I21: compare edi's census with independent compiler and I/O references.

The validator controls are a hand-written small record, not a repaired production
census. The production check reads the committed file without filling omissions.
"""

import copy
import json
import re
import shutil
from pathlib import Path

import pytest

from conftest import crysta_reference_source
from tests.fixtures.c34_t28_baseline import census_reference as reference
from tests.fixtures.c34_t28_compiler import crysta_headers

ROOT = Path(__file__).resolve().parents[3]
PAYLOAD_OWNERS = {
    'SpaceGroupSymop',
    'ExpandedAtomSites',
    'GeomBonds',
    'CartnTransform',
    'PowderReflnDataBase',
}
ONE_ROW = {
    'Cell': '_cell',
    'SpaceGroup': '_space_group',
    'Geom': '_geom',
    'ExperimentType': '_experiment_type',
    'PeakBase': '_peak',
    'InstrumentBase': '_instrument',
    'AbsorptionBase': '_absorption',
    'SequentialFitConfig': '_sequential_fit',
    'ProjectMetadata': '_metadata',
}
RAW_CONTAINER = re.compile(
    r'^(?:std::optional<)?std::(?:vector|map|deque|list|set|unordered_map|unordered_set)<'
)


@pytest.fixture(scope='module')
def independent():
    # All production-census escape controls share one immutable compiler/I/O
    # snapshot; fixture_costs banks this compilation once as a module cost.
    compiler = shutil.which('clang++')
    assert compiler, ' I21 the independent census comparison needs Clang'
    paths = [
        str(p.relative_to(ROOT))
        for top in ('core/src', 'lib/src', 'app/src', 'cli')
        for p in sorted((ROOT / top).rglob('*.cpp'))
    ]
    return reference.inventory(
        ROOT,
        'edi',
        compiler,
        io_paths=paths,
        identity_root=crysta_reference_source(),
        sdk_include=crysta_headers(),
    )


def read_census():
    path = ROOT / 'data/category-census.json'
    assert path.is_file(), ' I21 the committed data/category-census.json is required'
    return json.loads(path.read_text())


def category_schemas(record):
    categories = {}
    for row in record['categories']:
        categories.setdefault(row['name'], []).append(row)
    for name, schemas in categories.items():
        if len(schemas) == 1 and name != '_background':
            continue
        selectors = [row for row in schemas if row['form'] == 'one row']
        loops = [row for row in schemas if row['form'] == 'loop']
        assert len(selectors) == 1, (
            ' I21 / ADR-0077 repeated categories need exactly one selector schema'
        )
        assert loops and len(loops) == len(schemas) - 1, (
            ' I21 / ADR-0077 only loop alternatives may accompany a selector schema'
        )
        assert any('type' in col['items'] for col in selectors[0]['columns']), (
            ' I21 / ADR-0077 the selector schema must declare its type item'
        )
        assert not selectors[0].get('variants'), (
            ' I21 / ADR-0077 selector tokens belong to row schemas, not the selector'
        )
        assert all(row.get('variants') for row in loops), (
            ' I21 / ADR-0077 every row alternative must declare its selector tokens'
        )
        variants = [token for row in loops for token in row['variants']]
        assert len(variants) == len(set(variants)), (
            ' I21 / ADR-0077 each selector token must reach exactly one row schema'
        )
        assert all(col.get('storage') for row in loops for col in row['columns']), (
            ' I21 / ADR-0018 every alternative loop column must declare its storage'
        )
        if name == '_background':
            assert set(variants) == {'line-segment', 'chebyshev', 'polynomial'}, (
                ' I21 / ADR-0077 every declared background model needs a row schema'
            )
    return categories


def require_census(record, independent):
    expected = {
        row['owner'].rsplit('::', 1)[-1] + '::' + row['member'] for row in independent['members']
    }
    declared = [row['member'] for row in record['members']]
    assert len(declared) == len(set(declared)), (
        ' I21 duplicate member records cannot conceal omissions'
    )
    assert set(declared) == expected, (
        ' I21 census members must equal the independent compiler inventory: '
        + repr(sorted(expected ^ set(declared)))
    )
    categories = category_schemas(record)
    require_types(record, independent)
    columns = [
        column['member'] for row in record['categories'] for column in row.get('columns', [])
    ]
    assert len(columns) == len(set(columns)), (
        ' I21 / ADR-0077 each model member belongs to exactly one schema column'
    )
    payload = {
        row['owner'].rsplit('::', 1)[-1] + '::' + row['member']
        for row in independent['members']
        if row['owner'].rsplit('::', 1)[-1] in PAYLOAD_OWNERS
        and row['member'] != 'axis'
        # DataSource is the pre-existing renewal link, not a computed value.
        # Its independently read type still requires the census's one classification.
        and row['type'] != 'detail::DataSource'
    }
    assert payload <= set(columns), (
        ' I21 every computed payload member must be a declared column: '
        + repr(sorted(payload - set(columns)))
    )
    files = record['file_categories']
    observed = {tag.split('.')[0] for tag in independent['io_tags']}
    cif = {}
    for category in record['categories']:
        for tag in category.get('cif', []):
            assert tag not in cif, ' I21 a CIF item must have one schema owner'
            cif[tag] = category['name']
    for tag in independent['cif_tags']:
        if tag in categories or tag in record['file_categories']:
            observed.add(tag)  # A literal category stem is already its file category.
        else:
            assert tag in cif, ' I21 each literal CIF item needs a schema: ' + tag
            observed.add(cif[tag])
    # The immutable pre-move loader's legacy category spellings and T4's
    # combined data table bridge engine identity names to edi's category names.
    legacy = {
        '_atom_site_label': '_atom_site',
        '_atom_site_aniso_label': '_atom_site_aniso',
        '_pd_background': '_background',
        '_pd_data': '_data',
        '_pd_phase_block': '_linked_structure',
        '_easydiffraction_excluded_region': '_excluded_region',
        '_data_calc': '_data',
    }
    # Engine identities include calculated categories that edi does not write.
    # T4 stores measured and calculated points together in edi's `_data` table.
    identities = {
        legacy.get(row['tag'], legacy.get(row['tag'].split('.')[0], row['tag'].split('.')[0]))
        for row in independent['identity_columns']
    }
    assert identities <= set(categories), (
        ' I21 every engine identity category must resolve to an edi schema: '
        + repr(sorted(identities - set(categories)))
    )
    assert observed <= set(files), ' I21 every independent file category must appear: ' + repr(
        sorted(observed - set(files))
    )
    for name in observed:
        assert files[name] and all(target in categories for target in files[name]), (
            ' I21 file categories must resolve to real schema declarations: ' + name
        )
    owners = {row['owner'].rsplit('::', 1)[-1] for row in independent['members']}
    for owner, name in ONE_ROW.items():
        if owner in owners:
            assert (
                name in categories
                and len(categories[name]) == 1
                and categories[name][0]['form'] == 'one row'
            ), ' I14/I21 non-loop parameter blocks and categories are one row: ' + name
    assert 'LinkedStructure' not in owners or (
        len(categories.get('_linked_structure', [])) == 1
        and categories['_linked_structure'][0]['form'] == 'loop'
    ), 'Multiphase links must be a loop with one row per linked structure'
    require_member_classifications(record, categories)


def require_member_classifications(record, categories):
    for row in record['members']:
        # A one-row category can coexist with a nested item table (for example
        # the sequential extraction rules). Its real compiler type must name
        # the table; scalar cells still cannot be disguised as helpers/holders.
        item_table = row['type'].startswith('ItemVec<') and 'holds' in row
        if row['member'].split('::')[0] in ONE_ROW and 'part' not in row and not item_table:
            assert 'category' in row, (
                ' I21 a one-row model cell cannot be disguised as helper storage: ' + row['member']
            )
        assert sum(key in row for key in ('category', 'holds', 'part', 'not_storage')) == 1, (
            ' I21 each compiler member must have one classification: ' + row['member']
        )
        if 'category' in row:
            name = row['category']
            assert name in categories, ' I21 member categories must resolve'
            assert row['member'] in {
                c['member'] for schema in categories[name] for c in schema['columns']
            }, ' I21 membership must reach a column of that same category: ' + row['member']
        if 'holds' in row:
            assert row['holds'] and all(name in categories for name in row['holds']), (
                ' I21 a holder must resolve every category it contains'
            )
        if 'category' in row or 'holds' in row:
            assert not RAW_CONTAINER.match(row['type']), (
                ' I14 model storage cannot remain a standard container: ' + row['member']
            )


def require_types(record, independent):
    # Clang's first spelling preserves source aliases (std::string rather than
    # its expanded basic_string). Qualification and whitespace are immaterial.
    def spelling(value):
        return re.sub(r'\s+', '', value.replace('edi::', ''))

    expected = {
        row['owner'].rsplit('::', 1)[-1] + '::' + row['member']: spelling(row['type'])
        for row in independent['members']
    }
    for row in record['members']:
        assert spelling(row['type']) == expected[row['member']], (
            ' I21 the census must retain each independently compiled member type: ' + row['member']
        )
    for category in record['categories']:
        for column in category.get('columns', []):
            assert column['member'] in expected, (
                ' I21 schema columns must name actual compiler members'
            )
            assert spelling(column['type']) == expected[column['member']], (
                ' I21 a schema cannot disguise a member as another storage type'
            )


def test_committed_census_matches_independent_compiler_and_io_references(independent):
    require_census(read_census(), independent)


@pytest.mark.parametrize(
    'damage',
    [
        'duplicate-selector',
        'missing-selector',
        'selector-without-type',
        'selector-variants',
        'duplicate-variant',
        'empty-variants',
        'missing-model',
        'extra-model',
        'missing-loop',
        'non-loop-alternative',
        'duplicate-column',
        'missing-storage',
    ],
)
def test_declared_variant_binding_refuses_each_schema_escape(independent, damage):
    record = read_census()
    require_census(record, independent)
    changed = copy.deepcopy(record)
    schemas = [row for row in changed['categories'] if row['name'] == '_background']
    selector = next(row for row in schemas if row['form'] == 'one row')
    points = next(row for row in schemas if row.get('variants') == ['line-segment'])
    terms = next(row for row in schemas if 'chebyshev' in row.get('variants', []))
    if damage == 'duplicate-selector':
        changed['categories'].append(copy.deepcopy(selector))
    elif damage == 'missing-selector':
        changed['categories'].remove(selector)
    elif damage == 'selector-without-type':
        selector['columns'] = [col for col in selector['columns'] if 'type' not in col['items']]
    elif damage == 'selector-variants':
        selector['variants'] = ['line-segment']
    elif damage == 'duplicate-variant':
        terms['variants'].append('line-segment')
    elif damage == 'empty-variants':
        terms['variants'].clear()
    elif damage == 'missing-model':
        terms['variants'].remove('polynomial')
    elif damage == 'extra-model':
        terms['variants'].append('unknown-model')
    elif damage == 'missing-loop':
        changed['categories'].remove(terms)
    elif damage == 'non-loop-alternative':
        terms['form'] = 'columns'
    elif damage == 'duplicate-column':
        points['columns'].append(copy.deepcopy(terms['columns'][1]))
    elif damage == 'missing-storage':
        terms['columns'][0].pop('storage')
    with pytest.raises(AssertionError, match=r' I(?:14|21)'):
        require_census(changed, independent)


@pytest.mark.parametrize('damage', ['missing-point-column', 'ordinary-duplicate'])
def test_variant_admission_retains_point_columns_and_ordinary_uniqueness(independent, damage):
    changed = copy.deepcopy(read_census())
    require_census(changed, independent)
    if damage == 'missing-point-column':
        next(row for row in changed['categories'] if row.get('variants') == ['line-segment'])[
            'columns'
        ].pop()
    else:
        changed['categories'].append(
            copy.deepcopy(next(row for row in changed['categories'] if row['name'] == '_cell'))
        )
    with pytest.raises(AssertionError, match=r' I(?:14|21)'):
        require_census(changed, independent)


def control():
    # Hand-written inputs reach each validator branch before an incomplete product
    # supplies its census. This record is never used as the production reference.
    fields = [
        ('Cell', 'length_a', 'Parameter', '_cell'),
        ('PeakBase', 'cutoff_fwhm', 'double', '_peak'),
        ('PowderReflnDataBase', 'd_spacing', 'ComputedColumn<double>', '_refln'),
    ]
    record = {
        'categories': [
            {
                'name': name,
                'form': form,
                'columns': [{'member': owner + '::' + field, 'type': kind}],
            }
            for owner, field, kind, name, form in [
                (*fields[0], 'one row'),
                (*fields[1], 'one row'),
                (*fields[2], 'columns'),
            ]
        ],
        'members': [
            {'member': owner + '::' + field, 'type': kind, 'category': name}
            for owner, field, kind, name in fields
        ],
        'file_categories': {'_cell': ['_cell']},
    }
    record['categories'][0]['cif'] = ['_cell_length_a']
    observed = {
        'members': [
            {'owner': 'edi::' + owner, 'member': field, 'type': kind}
            for owner, field, kind, _ in fields
        ],
        'io_tags': {'_cell.length_a': ['core/src/io.cpp']},
        'cif_tags': {'_cell_length_a': ['core/src/io.cpp']},
        'identity_columns': [{'tag': '_refln.id', 'category': 'reflection'}],
    }
    return record, observed


@pytest.mark.parametrize(
    'damage',
    [
        'member',
        'computed',
        'category',
        'io',
        'cif',
        'classification',
        'wrong-category',
        'block-rows',
        'container',
        'outside-schema',
        'forged-helper',
        'forged-holder',
    ],
)
def test_independent_binding_refuses_each_omission_or_storage_escape(damage):
    record, observed = control()
    require_census(record, observed)
    changed = copy.deepcopy(record)
    if damage == 'member':
        changed['members'].pop()
    elif damage == 'computed':
        changed['categories'][-1]['columns'].clear()
    elif damage == 'category':
        changed['categories'].pop(0)
    elif damage == 'io':
        changed['file_categories'].pop('_cell')
    elif damage == 'cif':
        changed['categories'][0]['cif'].clear()
    elif damage == 'block-rows':
        changed['categories'][0]['form'] = 'loop'
    elif damage == 'container':
        changed['members'][0]['type'] = 'std::vector<double>'
        changed['categories'][0]['columns'][0]['type'] = 'std::vector<double>'
        observed['members'][0]['type'] = 'std::vector<double>'
    elif damage in {'forged-helper', 'forged-holder'}:
        changed['members'][0].pop('category')
        changed['members'][0]['not_storage' if damage == 'forged-helper' else 'holds'] = (
            'purported helper' if damage == 'forged-helper' else ['_peak']
        )
        changed['categories'][0]['columns'].clear()
    elif damage == 'outside-schema':
        changed['members'][0].pop('category')
    else:
        changed['members'][0]['category'] = '_peak' if damage == 'wrong-category' else '_absent'
    with pytest.raises(AssertionError, match=r' I(?:14|21)'):
        require_census(changed, observed)
