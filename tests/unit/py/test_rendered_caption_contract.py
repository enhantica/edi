"""Caption rules discover every received caption and refuse incomplete observations."""

import pytest

from tests.fixtures.captions.contract import caption_problems, check_caption


def row(**changes):
    return {
        'kind': 'field',
        'owner': 'unlisted.axis',
        'slot': 0,
        'text': 'Sample form',
        'width': 123.5,
        'height': 17.25,
        'enabled': False,
        **changes,
    }


@pytest.mark.parametrize(
    'text',
    [
        'Sample form',
        'Calculation range',
        'Name',
        'ID',
        '2θ',
        'TOF',
        'd spacing',
        's.u. (μB)',
        '\N{GREEK SMALL LETTER ALPHA}₀',
        '\N{GREEK SMALL LETTER BETA}1',
        'x12',
        '\N{GREEK SMALL LETTER CHI}² change tolerance',
        '\N{GREEK SMALL LETTER LAMDA}',
    ],
)
def test_capital_prose_and_complete_scientific_tokens_are_retained(text):
    assert check_caption(text), (
        'The common caption rule preserves capitals and case-significant symbols'
    )


@pytest.mark.parametrize(
    'text',
    [
        'sample form',
        'beam mode',
        'probe',
        'scattering type',
        'dimensionality',
        'polarisation',
        'min',
        'max',
        'step',
        'calculation range',
        'description',
        'data quality',
        '\N{GREEK SMALL LETTER ALPHA}lpha',
    ],
)
def test_lowercase_prose_cannot_escape_by_starting_with_a_symbol_letter(text):
    assert not check_caption(text), (
        'A scientific exception must be a complete symbol, never a prose prefix'
    )


@pytest.mark.parametrize('kind', ['field', 'group', 'header'])
def test_each_received_runtime_role_is_checked_without_a_dictionary_allowlist(kind):
    assert not caption_problems([row(kind=kind)]), (
        'A real caption can be disabled and outside the prior dictionary list'
    )
    assert caption_problems([row(kind=kind, text='new dynamic caption')]), (
        'Every received runtime caption is checked, including an unlisted future field or header'
    )


@pytest.mark.parametrize(
    'changes',
    [
        {'text': None},
        {'text': ''},
        {'width': 0},
        {'height': -1},
        {'width': float('nan')},
        {'width': True},
        {'kind': 'body'},
        {'kind': []},
        {'owner': ''},
        {'slot': -1},
        {'slot': True},
        {'enabled': 'disabled'},
    ],
)
def test_a_caption_without_valid_rendered_evidence_cannot_satisfy_the_census(changes):
    assert caption_problems([row(**changes)]), (
        'Malformed or unpainted captions refuse rather than disappearing from the census'
    )


@pytest.mark.parametrize('records', [None, {}, [], [None], [{'text': 'Name'}]])
def test_empty_or_partial_caption_payloads_fail_closed(records):
    assert caption_problems(records), (
        'A missing or partial runtime census cannot qualify the capitalisation rule'
    )
