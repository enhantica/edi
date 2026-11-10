"""The real Examples catalogue equals case records, including after collection discovery."""

import copy
import json
import os
import subprocess
from pathlib import Path

import pytest

from tests.fixtures.tutorial_cases.contract import ROOT, read_records
from tests.fixtures.tutorial_cases.example_contract import (
    PROVENANCE,
    READY,
    assert_case_tags,
    assert_inventory,
    assert_painted_tags,
    assert_provenance_is_not_a_tag,
    collection_index,
    expected_rows,
)


@pytest.fixture(scope='module')
def observations(tmp_path_factory):
    records = read_records()
    registry = json.loads((ROOT / 'app/examples/tags.json').read_text())
    expected = expected_rows(records, registry)
    runner = Path(os.environ.get('EDI_APP_TEST_RUNNER', ROOT / 'build/app/app/edi_app_tests'))
    assert runner.is_file(), 'Examples contract prerequisite: the actual app test host is built'
    base = tmp_path_factory.mktemp('case-examples')
    results = {}
    for mode in ['case-only', 'collection-extras', 'painted-provenance']:
        folder = base / mode
        folder.mkdir()
        document = {
            'records': records,
            'index': collection_index(records, noisy=mode == 'collection-extras'),
            'ready': READY,
            'paintExtra': mode == 'painted-provenance',
        }
        (folder / 'case-examples.json').write_text(json.dumps(document))
        empty = folder / 'empty'
        empty.mkdir()
        (empty / 'index.json').write_text('{"schema":"edi-data-index/1","entries":[]}')
        output = folder / 'native.log'
        with output.open('w') as log:
            run = subprocess.run(
                [
                    str(runner),
                    '-input',
                    str(ROOT / 'tests/system/app/tst_case_examples.qml'),
                    '-o',
                    '-,txt',
                    'CaseExamples::test_observe_case_catalogue_and_painted_tags',
                ],
                env={
                    **os.environ,
                    'EDI_ACCEPTANCE_REFERENCE': str(folder),
                    'EDI_ONLINE_SOURCES': 'easydiffraction=' + empty.as_uri(),
                    'XDG_CONFIG_HOME': str(folder / 'config'),
                    'QT_QPA_PLATFORM': 'offscreen',
                    'QT_QUICK_BACKEND': 'software',
                    'OMP_NUM_THREADS': '1',
                    'OPENBLAS_NUM_THREADS': '1',
                },
                stdout=log,
                stderr=subprocess.STDOUT,
                text=True,
                check=False,
                timeout=120,
            )
        text = output.read_text()
        assert (
            run.returncode == 0 and '::test_observe_case_catalogue_and_painted_tags()' in text
        ), (
            'Examples contract prerequisite: the real transport/model/paint observer finishes: '
            + text
        )
        models = marker(text, 'CASE_EXAMPLES_MODEL ')
        assert len(models) == 1, (
            'Examples contract: one actual model snapshot follows index adoption'
        )
        results[mode] = {
            'rows': models[0],
            'painted': marker(text, 'CASE_EXAMPLES_PAINTED '),
            'log': str(output),
        }
    return {'expected': expected, 'modes': results}


def marker(output, prefix):
    return [
        json.loads(line.partition(prefix)[2]) for line in output.splitlines() if prefix in line
    ]


@pytest.mark.parametrize('mode', ['case-only', 'collection-extras'])
def test_live_examples_equal_exactly_the_case_records(mode, observations):
    assert_inventory(observations['modes'][mode]['rows'], observations['expected'])


@pytest.mark.parametrize('mode', ['case-only', 'collection-extras'])
def test_every_case_row_has_only_its_curated_registry_labels_icons_and_tones(mode, observations):
    assert_case_tags(observations['modes'][mode]['rows'], observations['expected'])


@pytest.mark.parametrize('mode', ['case-only', 'collection-extras'])
def test_source_facility_and_instrument_never_appear_as_actual_tag_pills(mode, observations):
    observed = observations['modes'][mode]
    assert_provenance_is_not_a_tag(observed['rows'], observed['painted'], observations['expected'])


@pytest.mark.parametrize('mode', ['case-only', 'collection-extras'])
def test_actual_badge_text_matches_the_model_tags_without_title_or_origin(mode, observations):
    observed = observations['modes'][mode]
    assert_painted_tags(observed['rows'], observed['painted'])


def control_rows():
    row = {
        'exampleId': 'case-a',
        'tagLabels': ['Fitting', 'Crystal'],
        'tagIcons': ['fit-glyph', 'structure-glyph'],
        'tagColors': ['#102030', '#405060'],
        'tagDarkColors': ['#708090', '#a0b0c0'],
    }
    return (
        {'case-a': row},
        [copy.deepcopy(row)],
        [{'id': 'case-a', 'labels': row['tagLabels'].copy()}],
    )


@pytest.mark.parametrize('damage', ['extra', 'missing', 'duplicate'])
def test_inventory_observer_refuses_extra_missing_and_duplicate_cases(damage):
    expected, rows, _ = control_rows()
    assert_inventory(rows, expected)
    if damage == 'missing':
        rows.clear()
    else:
        rows.append({**rows[0], 'exampleId': 'case-b' if damage == 'extra' else 'case-a'})
    with pytest.raises(AssertionError, match='Examples contract:'):
        assert_inventory(rows, expected)


@pytest.mark.parametrize('field', ['tagLabels', 'tagIcons', 'tagColors', 'tagDarkColors'])
@pytest.mark.parametrize('damage', ['missing', 'extra', 'renamed'])
def test_curated_tag_observer_refuses_any_missing_extra_or_changed_chip(field, damage):
    expected, rows, _ = control_rows()
    assert_case_tags(rows, expected)
    if damage == 'missing':
        rows[0][field].pop()
    elif damage == 'extra':
        rows[0][field].append('unexpected')
    else:
        rows[0][field][0] = 'renamed'
    with pytest.raises(AssertionError, match='Examples contract:'):
        assert_case_tags(rows, expected)


@pytest.mark.parametrize('value', PROVENANCE)
@pytest.mark.parametrize('surface', ['model', 'painted'])
def test_provenance_observer_refuses_metadata_chips_but_allows_origin_text(value, surface):
    expected, rows, painted = control_rows()
    rows[0]['origin'] = value
    assert_provenance_is_not_a_tag(rows, painted, expected)
    if surface == 'model':
        rows[0]['tagLabels'].append(value)
    else:
        painted[0]['labels'].append(value)
    with pytest.raises(AssertionError, match='Examples contract:'):
        assert_provenance_is_not_a_tag(rows, painted, expected)


@pytest.mark.parametrize(
    'facet', ['source', 'facility', 'facilities', 'instrument', 'instruments']
)
def test_case_record_cannot_relabel_provenance_as_a_curated_facet(facet):
    registry = {
        'tags': {'structure': {'crystal': {'label': 'Crystal', 'tone': 'plain'}}},
        'tones': {'plain': {'light': '#102030', 'dark': '#405060'}},
    }
    records = [
        {'id': 'case-a', 'tags': [{'facet': 'structure', 'value': 'crystal', 'label': 'Crystal'}]}
    ]
    expected_rows(records, registry)
    records[0]['tags'][0]['facet'] = facet
    with pytest.raises(AssertionError, match='Examples contract:'):
        expected_rows(records, registry)


@pytest.mark.parametrize('damage', ['missing-row', 'duplicate-row', 'hidden-chip', 'extra-chip'])
def test_painted_observer_refuses_rows_or_chips_that_disagree_with_the_model(damage):
    _, rows, painted = control_rows()
    assert_painted_tags(rows, painted)
    if damage == 'missing-row':
        painted.clear()
    elif damage == 'duplicate-row':
        painted.append(copy.deepcopy(painted[0]))
    elif damage == 'hidden-chip':
        painted[0]['labels'].pop()
    else:
        painted[0]['labels'].append('unexpected')
    with pytest.raises(AssertionError, match='Examples contract:'):
        assert_painted_tags(rows, painted)


def test_observer_detects_an_opaque_provenance_chip_outside_the_model(observations):
    observed = observations['modes']['painted-provenance']
    assert_inventory(observed['rows'], observations['expected'])
    assert_case_tags(observed['rows'], observations['expected'])
    assert any('Fixture Observatory' in row['labels'] for row in observed['painted']), (
        'Examples contract: the actual opaque escape pill is observed without a modelData property'
    )
    with pytest.raises(AssertionError, match='Examples contract:'):
        assert_provenance_is_not_a_tag(
            observed['rows'], observed['painted'], observations['expected']
        )
    with pytest.raises(AssertionError, match='Examples contract:'):
        assert_painted_tags(observed['rows'], observed['painted'])
