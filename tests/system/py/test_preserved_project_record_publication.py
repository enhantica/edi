"""Actual Save delegates preserve the complete planned unowned CIF record content."""

import gemmi
import pytest

from tests.system.py import test_save_policy_continuations as policy
from tests.system.py import test_sealed_publication_contract as sealed

tutorial_observer = policy.tutorial_observer
# Modeled declarations and retired fields are the declared writer-owned set
# (linked-data contract and the retired-description decision); prefixes are not ownership.
OWNED = frozenset(
    ['_edi.schema_version', '_su_format.rule']
    + [
        '_metadata.' + key
        for key in (
            'name',
            'title',
            'description',
            'authors',
            'created',
            'last_modified',
            'timestamp',
            'dimensionality',
            'polarisation',
            'instrument',
            'facility',
            'purpose',
        )
    ]
)


def carried(text):
    block = gemmi.cif.read_string('data_independent_record\n' + text).sole_block()
    result = {}
    for item in block:
        if item.pair is not None:
            tag, token = item.pair
            if tag.lower() not in OWNED:
                result[tag.lower()] = [gemmi.cif.as_string(token)]
        elif item.loop is not None:
            for at, tag in enumerate(item.loop.tags):
                if tag.lower() not in OWNED:
                    result[tag.lower()] = [
                        gemmi.cif.as_string(value)
                        for value in item.loop.values[at :: len(item.loop.tags)]
                    ]
    return result


@pytest.mark.parametrize('route', sealed.ROUTES)
@pytest.mark.parametrize('phase', ['pre-core', 'copy'])
@pytest.mark.parametrize('mutation', ['unchanged', 'same-size'])
@pytest.mark.parametrize('spelling', ['scalar', 'literal'])
def test_every_save_delegate_publishes_exact_planned_carried_record_content(
    tutorial_observer, tmp_path, route, phase, mutation, spelling
):
    row = policy.observe(
        tutorial_observer,
        tmp_path,
        f'sealed-publication/{route}/{phase}/{mutation}/{spelling}/project-record',
    )
    assert row['injected'] and row['role'] == 'project-record', (
        'The accident reaches the actual original project record after its save decision'
    )
    expected = carried(row['recordBefore'])
    assert expected['_audit.note'] == ['independent content A'], (
        'The receipt oracle retains the independently authored pre-accident scalar'
    )
    expected_other = (
        'first authored paragraph\n_metadata.name literal carried words\n\nlast authored paragraph'
        if spelling == 'literal'
        else 'independently authored carried record'
    )
    assert expected['_audit.other'] == [expected_other], (
        'The unowned CIF value retains its authored characters and significant blank lines'
    )
    for publication in row['recordPublications']:
        assert carried(publication['text']) == expected, (
            'Every actual record publication preserves the whole planned unowned CIF content: '
            + publication['boundary']
        )
    assert row['externalDataConserved'], (
        'A project-record save never alters the independent linked scientific input files'
    )
    if row['recordPrivateSource']:
        assert row['originalUserSourceConserved'], (
            'Retiring a private browser/archive cache leaves the original user input bytes intact'
        )
    if (row['refused'] or row['replanned']) and not row['committed']:
        assert row['destinationUnchanged'], (
            'A record save refused before publication retains every previous user destination byte'
        )
    else:
        assert row['committed'] and row['recordPublications'], (
            'An accepted record save reaches an actual observed publication with carried content'
        )
    if mutation == 'unchanged':
        assert row['committed'] and not row['refused'] and not row['replanned'], (
            'Owned metadata rewrites alone permit a normal successful actual Save'
        )
