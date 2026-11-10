"""Gate 1: ADR-0080 and the owner's complete inventory, independent of its builder."""

import json
import shlex

import pytest
import yaml

from tests.fixtures.tutorial_cases.contract import (
    CASES,
    CONTRACT,
    ROOT,
    SURFACE_INTERFACE,
    case_record,
    declared_interfaces,
    interfaces_for,
    pin_quantities,
    read_records,
)


def test_owner_inventory_has_exactly_twenty_four_unique_case_records():
    actual = [row['id'] for row in read_records()]
    assert len(actual) == len(set(actual)) == 24 and set(actual) == set(CASES), (
        'Gate 1: all 24 selected cases occur once, including three-temperature CoSiO HEiDi, '
        'TbTi simulation and folded SPODI'
    )
    registry = yaml.safe_load((ROOT / 'docs/user/cli/projects.yml').read_text())['projects']
    assert set(actual) == {row['id'] for row in registry if row.get('user-facing') is True}, (
        'Gate 1: records cover exactly the public cases, excluding internal verification starts'
    )
    assert actual == [row['id'] for row in registry if row.get('user-facing') is True], (
        'Gate 1: record positions retain the declared registry order'
    )
    assert [row['order'] for row in read_records()] == list(range(1, 25)), (
        'Gate 1: every record carries its unique registry position'
    )


@pytest.mark.parametrize('case', CASES)
def test_each_case_record_has_all_fields_and_its_declared_tutorials(case):  # noqa: PLR0914 - complete record boundary
    record = case_record(case)
    required = {
        'schema',
        'id',
        'order',
        'diffraction_lib',
        'structures',
        'experiments',
        'data',
        'tags',
        'structure_from',
        'data_from',
        'pin',
        'tutorials',
    }
    assert required <= record.keys() and record['schema'] == 'edi-case/1', (
        'Gate 1: a complete case uses the declared versioned record and every required field'
    )
    outline = record['diffraction_lib']
    assert outline.get('tutorial') and outline.get('match') in {'same', 'follows'}, (
        'Gate 1: every case names its published tutorial or declared outline predecessor'
    )
    directory = ROOT / 'docs/user/cli' / case / 'project'
    assert (directory / 'project.edi').is_file(), 'Gate 1: each case has a real example project'
    fields = dict(
        shlex.split(line)
        for line in (directory / 'project.edi').read_text().splitlines()
        if line.startswith('_metadata.name ')
    )
    assert fields.get('_metadata.name') == case, 'Gate 1: the example and its record share one id'
    for category, field in [('structures', 'structures'), ('experiments', 'experiments')]:
        expected = [
            case + '-' + path.stem for path in sorted((directory / category).glob('*.edi'))
        ]
        assert expected and record[field] == expected, (
            'Gate 1: structures and experiments name every real collection entity in file order'
        )
    assert isinstance(record['data'], list) and (
        case in CONTRACT['simulations'] or record['data']
    ), 'Gate 1: measured cases name collection data; simulations may have none'
    assert record['structure_from'] == (
        'hand' if case == 'pd-neut-cwl_lbco-hrpt' else 'collection'
    ), 'Gate 1: only LBCO HRPT builds its structure by hand'
    expected_data = ['collection', 'file'] if case == 'pd-neut-tof_si-sepd' else ['collection']
    assert record['data_from'] == expected_data, (
        'Gate 1: every case uses collection data and Si SEPD also teaches local-file loading'
    )
    assert isinstance(record['pin'], dict) and record['pin'], (
        'Gate 1: no record may silently omit its regression pin and source provenance'
    )
    expected = json.loads((ROOT / 'docs/user/cli' / case / 'expected.json').read_text())
    source = expected.get('source', {}).get('pins')
    assert isinstance(source, dict) and {'commit', 'reason', 'values'} <= record['pin'].keys(), (
        'Gate 1: the pin field carries its source commit, reason and regression values'
    )
    assert all(record['pin'][key] == source.get(key) for key in ['commit', 'reason']), (
        'Gate 1: record pin provenance comes unchanged from its committed pin source'
    )
    quantities = pin_quantities(expected, simulation=case in CONTRACT['simulations'])
    assert quantities and record['pin']['values'] == {
        name: quantity['value'] for name, quantity in quantities.items()
    }, 'Gate 1: the record carries exactly its labelled regression values, including simulations'
    declared = interfaces_for(case)
    assert set(declared_interfaces(record)) == set(declared), (
        'Gate 1: exported interfaces retain the independent case declaration and default'
    )
    expected_tutorials = {
        key: pattern.format(case=case)
        for key, pattern in CONTRACT['tutorials'].items()
        if SURFACE_INTERFACE[key] in declared
    }
    assert set(record['tutorials']) <= set(CONTRACT['tutorials']) and all(
        record['tutorials'].get(key) == value for key, value in expected_tutorials.items()
    ), 'Gate 1: each declared interface retains its tutorial paths and shared case id'
    for surface in set(expected_tutorials) & {'python', 'app_docs', 'cli_docs'}:
        assert (ROOT / expected_tutorials[surface]).is_file(), (
            'Gate 1: every declared tutorial artefact must exist: ' + case + ' ' + surface
        )
    if 'app' not in declared:
        return
    app = json.loads((ROOT / 'app/tutorials/manifest.json').read_text())['tutorials']
    matches = [row for row in app if row.get('id') == case]
    assert len(matches) == 1, 'Gate 1: each case has exactly one built-in app tutorial: ' + case
    entry = matches[0]
    if 'tour' in entry:
        tour = ROOT / 'app/tutorials' / entry['tour']
        assert tour.is_file(), 'Gate 1: a referenced built-in tutorial must exist'
        steps = json.loads(tour.read_text())
    else:
        steps = entry.get('steps')
    assert steps, 'Gate 1: an app tutorial must contain teaching steps, not an empty placeholder'


@pytest.mark.parametrize('case', CASES)
def test_each_record_carries_the_complete_ordered_tag_set(case):
    tags = case_record(case)['tags']
    assert tags and all(set(tag) == {'facet', 'value', 'label'} for tag in tags), (
        'Gate 1: each tag carries its facet, semantic value and exact displayed label'
    )
    facets = [tag['facet'] for tag in tags]
    order = CONTRACT['facets']
    assert set(order) == set(facets) and facets == sorted(facets, key=order.index), (
        'Gate 1: purpose, fitting mode, sample, radiation, beam, scattering and structure '
        'tags are complete and ordered'
    )
    assert len({(tag['facet'], tag['value']) for tag in tags}) == len(tags), (
        'Gate 1: repeated or conflicting copies cannot inflate a case tag set'
    )
    vocabulary = json.loads((ROOT / 'app/examples/tags.json').read_text())['tags']
    for tag in tags:
        assert tag['value'] in vocabulary[tag['facet']], (
            'Gate 1: tags use declared semantic values'
        )
        assert tag['label'] == vocabulary[tag['facet']][tag['value']]['label'], (
            'Gate 1: tag labels retain their declared spelling, including Crystal and Magnetic'
        )
    purpose = [tag['label'] for tag in tags if tag['facet'] == 'purpose']
    assert purpose == ['Simulation' if case in CONTRACT['simulations'] else 'Fitting'], (
        'Gate 1: exactly LBCO powder and TbTi HEIDI single crystal are simulations'
    )
