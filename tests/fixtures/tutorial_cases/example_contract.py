"""Case records define the Examples inventory and its curated presentation."""

from collections import Counter

from tests.fixtures.tutorial_cases.contract import CONTRACT

RETIRED = (
    'pd-neut-cwl_cosio-d20_scan',
    'pd-neut-cwl_yap-spodi_3k',
    'pd-neut-tof_si_simulation',
    'pd-xray-cwl_nacl_simulation',
)
PROVENANCE = [
    'EasyDiffraction Database',
    'Fixture Provenance',
    'Fixture Observatory',
    'Fixture Beamline',
]
READY = 'catalogue-input-ready'


def expected_rows(records, registry):
    assert records and len({record['id'] for record in records}) == len(records), (
        'Examples contract: case records are nonempty with unique identities'
    )
    expected = {}
    for record in records:
        tags = record['tags']
        assert tags and all(tag['facet'] in CONTRACT['facets'] for tag in tags), (
            'Examples contract: tags use curated facets, excluding source, facility and instrument'
        )
        assert len({(tag['facet'], tag['value']) for tag in tags}) == len(tags), (
            'Examples contract: curated semantic tags occur once per case'
        )
        definitions = [registry['tags'][tag['facet']][tag['value']] for tag in tags]
        assert [tag['label'] for tag in tags] == [item['label'] for item in definitions], (
            'Examples contract: the record retains the one registry spelling of every curated tag'
        )
        expected[record['id']] = {
            'exampleId': record['id'],
            'tagLabels': [tag['label'] for tag in tags],
            'tagIcons': [item.get('glyph', '') for item in definitions],
            'tagColors': [registry['tones'][item['tone']]['light'] for item in definitions],
            'tagDarkColors': [registry['tones'][item['tone']]['dark'] for item in definitions],
        }
    return expected


def assert_inventory(rows, expected):
    ids = [row['exampleId'] for row in rows]
    assert Counter(ids) == Counter(expected.keys()), (
        'Examples contract: exactly one live row per case record; '
        f'extra={sorted(set(ids) - set(expected))}, missing={sorted(set(expected) - set(ids))}'
    )


def assert_case_tags(rows, expected):
    for identity, wanted in expected.items():
        found = [row for row in rows if row['exampleId'] == identity]
        assert len(found) == 1, (
            'Examples contract: every case has one tag-bearing row: ' + identity
        )
        for key in ['tagLabels', 'tagIcons', 'tagColors', 'tagDarkColors']:
            assert found[0][key] == wanted[key], (
                'Examples contract: ordered labels, glyphs and tones equal the case record: '
                + identity
                + ' '
                + key
            )


def assert_provenance_is_not_a_tag(rows, painted, expected):
    allowed = {label for row in expected.values() for label in row['tagLabels']}
    labels = [label for row in rows for label in row['tagLabels']]
    labels += [label for row in painted for label in row['labels']]
    assert set(labels) <= allowed and not set(labels).intersection(PROVENANCE), (
        'Examples contract: source, facility and instrument never become tag chips'
    )


def assert_painted_tags(rows, painted):
    assert Counter(row['id'] for row in painted) == Counter(row['exampleId'] for row in rows), (
        'Examples contract: the real list renders each actual model row once'
    )
    for row in rows:
        labels = next(item['labels'] for item in painted if item['id'] == row['exampleId'])
        assert labels == row['tagLabels'], (
            'Examples contract: painted badges equal model tags; titles and origins are separate'
        )


def collection_index(records, *, noisy):
    entries = [
        {
            'id': record['id'],
            'kind': 'project',
            'name': record.get('title', record['id']),
            'description': 'Authored catalogue transport input; not a scientific project archive',
            'instrument': PROVENANCE[3],
            'facility': PROVENANCE[2],
            'source': PROVENANCE[1],
            'radiation': 'neutron',
            'technique': 'powder constant wavelength',
            'files': [{'path': 'projects/' + record['id'] + '.zip', 'format': 'zip'}],
            'case': record,
        }
        for record in records
    ]
    if noisy:
        for identity in [*RETIRED, 'collection-only-specimen']:
            entries.append({**entries[0], 'id': identity, 'name': identity})
            del entries[-1]['case']
    entries.append({
        'id': READY,
        'kind': 'structure',
        'name': 'Index completion witness',
        'files': [{'path': 'structures/ready.edi', 'format': 'edi'}],
    })
    return {'schema': 'edi-data-index/1', 'entries': entries}
