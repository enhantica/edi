"""Privacy inputs are independent encodings of a user copying ordinary diagnostics."""

import json
from operator import itemgetter
from pathlib import Path

import pytest

from tests.system.py import test_feedback_payload as payload_contract

payload_binary = payload_contract.payload_binary
invoke = payload_contract.invoke

CASES = json.loads(
    (
        Path(__file__).resolve().parents[2] / 'fixtures/onboarding/privacy_representations.json'
    ).read_text(encoding='utf-8')
)['cases']


@pytest.mark.parametrize('case', CASES, ids=itemgetter('id'))
@pytest.mark.parametrize(
    'channel', ['text', 'nested_app', 'app_array', 'current_log', 'crash_log']
)
def test_accidentally_copied_identity_is_redacted_in_each_channel(
    payload_binary, tmp_path, case, channel
):
    changes = {
        'home': case['home'],
        'user': case['user'],
        'text': 'A diagnostic report',
        'log': 'Public log text',
        'app': {'version': '8.7.6', 'details': {'folder': case['input']}},
        'include': channel != 'text',
    }
    if channel == 'app_array':
        changes['app'] = {'version': '8.7.6', 'details': [case['input']]}
    if channel == 'text':
        changes['text'] = case['input']
    if channel in {'current_log', 'crash_log'}:
        changes['log'] = case['input']
    _, result = invoke(payload_binary, tmp_path, **changes)
    payload = result['payload']
    if channel == 'text':
        actual = payload['text']
    elif channel == 'nested_app':
        actual = payload['app']['details']['folder']
    elif channel == 'app_array':
        actual = payload['app']['details'][0]
    else:
        actual = payload['log']
    assert actual == case['expected'], (
        'A complete private identifier is replaced without corrupting surrounding diagnostics: '
        + case['accident']
        + ' channel='
        + channel
    )
    assert result['requests'][0]['payload'] == payload, (
        'The injected submission receives the same redacted object shown by the builder'
    )


@pytest.mark.parametrize('kind', ['feedback', 'question', 'problem', 'idea'])
@pytest.mark.parametrize('include', [False, True], ids=['text_only', 'with_diagnostics'])
def test_account_named_after_feedback_kind_cannot_corrupt_protocol_fields(
    payload_binary, tmp_path, kind, include
):
    # Accident: an ordinary local account has the same name as the chosen feedback kind.
    _, result = invoke(
        payload_binary,
        tmp_path,
        kind=kind,
        user=kind,
        home='/profiles/' + kind,
        text='Written by ' + kind,
        include=include,
        app={'version': '8.7.6', 'system': 'Public platform', 'details': {'owner': kind}},
        log='Owner ' + kind,
    )
    assert 'payload' in result, 'Every supported kind survives an account-name collision'
    payload = result['payload']
    assert payload['kind'] == kind, (
        'Identity redaction preserves the validated feedback discriminant'
    )
    assert payload['text'] == 'Written by ~', 'Protecting protocol fields still redacts user text'
    if include:
        assert set(payload['app']) == {'version', 'system', 'details'}, (
            'Identity replacement retains the structured application field names'
        )
        assert payload['app']['version'] == '8.7.6', 'Public application version remains unchanged'
        assert payload['app']['details'] == {'owner': '~'}, (
            'User-derived metadata is redacted without replacing its structured container'
        )


@pytest.mark.parametrize('user', ['app', 'kind', 'version', 'system'])
def test_account_named_after_schema_key_cannot_rename_payload_structure(
    payload_binary, tmp_path, user
):
    # Accident: an account name matches a JSON key when its diagnostics are included.
    _, result = invoke(
        payload_binary,
        tmp_path,
        user=user,
        home='/profiles/' + user,
        text='Written by ' + user,
        app={'version': '8.7.6', 'system': 'Public platform', 'app': {'owner': user}},
        log='Owner ' + user,
    )
    payload = result['payload']
    assert set(payload) == {'kind', 'text', 'app', 'log'}, (
        'Redaction never renames the feedback wire schema keys'
    )
    assert set(payload['app']) == {'version', 'system', 'app'}, (
        'Redaction never renames structured application keys'
    )
    assert payload['kind'] == 'question' and payload['app']['version'] == '8.7.6', (
        'Protocol and application constants survive account names that match schema words'
    )
    assert payload['app']['app'] == {'owner': '~'}, (
        'Redacting an account value preserves the surrounding application object shape'
    )
