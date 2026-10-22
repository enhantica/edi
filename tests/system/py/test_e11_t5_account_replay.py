"""U1: account/connection scopes retire planted public and opaque provider originals.

Offline accounts use independent signed identities through the real native callback.
Expected items are literal fixture inputs; actual outgoing HTTP bodies are observed.
"""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest

from tests.fixtures.assistant.response_events import message_complete, message_start, text_fragment

_spec = importlib.util.spec_from_file_location(
    'account_transport', Path(__file__).with_name('test_e11_t5_assistant_native.py')
)
transport = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(transport)
native = transport.native
signer = transport.signer


def records(actor):
    return {row['key']: json.loads(row['bytes']) for row in actor.last['records']}


def registration(actor):
    return next(key[2:] for key in records(actor) if key.startswith('1:'))


def establish_accounts(actor, signer):
    actor.authenticate(signer)
    assert actor.ready(), 'I12/U1: account A has a genuinely verified offline grant'
    first = registration(actor)
    other = transport.Native(Path(actor.process.args[0]), reply_timeout=5)
    try:
        other.command('store_put', key='0:host', utf8=json.dumps(records(actor)['0:host']))
        other.command('recreate')
        other.authenticate(signer, claims_patch={'sub': 'independent-account-B'})
        assert other.ready(), (
            'I12/U1: account B independently passes the real signed-identity verifier'
        )
        second = registration(other)
        assert first != second, (
            'I12/U1: two signed subjects have distinct issued-client registrations'
        )
        values = records(other)
        actor.command(
            'store_put_batch',
            records=[
                {'key': key, 'utf8': json.dumps(value, separators=(',', ':'))}
                for key, value in values.items()
                if key != '0:host'
            ],
        )
    finally:
        other.close()
    return first, second


def request(actor, marker):
    value = transport.provider_request(actor, request_id='account-bound-next-request')
    value['history'] = [{'type': 'message', 'role': 'user', 'text': 'Fresh visible question'}]
    if marker == 'unchanged':
        value['conversation_id'] = 'same-displayed-conversation'
    return value


def plant_originals(actor, marker):
    value = request(actor, marker)
    sent = actor.command('send', payload=value)
    assert sent['reply']['ok'], (
        'I13/U1: verified account A starts the planted real native response'
    )
    index = len(sent['requests']) - 1
    actor.handled.add(index)
    actor.command(
        'headers', index=index, status=200, headers=[['Content-Type', 'text/event-stream']]
    )
    ending = message_complete('Account A original public answer', item_id='account-A-message')
    public = ending[-1]['response']['output'][0]
    opaque = {
        'id': 'account-A-opaque',
        'type': 'reasoning',
        'status': 'completed',
        'summary': [],
        'encrypted_content': 'literal-account-A-continuation',
    }
    ending[-1]['response']['output'] = [public, opaque]
    transport.stream(
        actor,
        index,
        [
            *message_start(item_id=public['id']),
            text_fragment('Account A original public answer', item_id=public['id']),
            *ending[:-1],
            {
                'type': 'response.output_item.added',
                'output_index': 1,
                'item': {**opaque, 'status': 'in_progress'},
            },
            {'type': 'response.output_item.done', 'output_index': 1, 'item': opaque},
            ending[-1],
        ],
    )
    assert any(
        e.get('type') == 'turn_finished' and e.get('status') == 'completed'
        for e in actor.last['events']
    ), 'I13/U1: the complete original public/opaque response reaches successful native settlement'
    return [public, opaque]


def renew(actor, identity):
    result = actor.command('connect_saved', id=identity)
    assert result['reply']['ok'], 'I12/U1: selected verified registration enters actual renewal'
    index = len(result['requests']) - 1
    assert result['requests'][index]['url'] == transport.AUTH + '/api/accounts/oauth/token', (
        'I12/U1: reconnect consumes the selected genuine stored refresh grant'
    )
    actor.handled.add(index)
    actor.respond(
        index,
        {
            'access_token': 'synthetic-account-renewed-access',
            'refresh_token': 'synthetic-account-renewed-refresh',
            'token_type': 'Bearer',
            'expires_in': 3600,
            'scope': transport.SCOPES,
        },
    )
    actor.automatic()
    assert actor.ready(), (
        'I12/U1: renewal of an already verified subject completes its real catalog'
    )


def transition(actor, signer, mode, first, second):
    previous = transport.provider_request(actor)['connection_id']
    if mode == 'sign-in':
        actor.authenticate(signer)
    else:
        if mode == 'expiry-reconnect':
            actor.command('advance', seconds=3600, milliseconds=1)
            assert actor.last['state']['status'] == 'expired', (
                'I12/U1: actual grant expiry is observable before explicit reconnect'
            )
            before = len(actor.last['requests'])
            rejected = actor.command('send', payload=request(actor, 'omitted'))
            assert not rejected['reply']['ok'] and len(rejected['requests']) == before, (
                'I12/U1: expired authorization cannot dispatch a continuation before renewal'
            )
        renew(actor, second if mode == 'saved-other-account' else first)
    assert actor.ready() and transport.provider_request(actor)['connection_id'] != previous, (
        'I12/U1: successful sign-in/reconnect establishes a fresh actual connection scope'
    )


def outgoing(actor, marker):
    before = len(actor.last['requests'])
    sent = actor.command('send', payload=request(actor, marker))
    assert sent['reply']['ok'] and len(sent['requests']) == before + 1, (
        'I13/U1: valid fresh history reaches exactly one actual outgoing provider request'
    )
    return json.loads(sent['requests'][-1]['body'])['input']


@pytest.mark.parametrize('marker', ['omitted', 'unchanged'])
@pytest.mark.parametrize(
    'mode', ['saved-other-account', 'saved-same-account', 'sign-in', 'expiry-reconnect']
)
def test_every_successful_connection_transition_retires_original_public_and_opaque_items(
    native, signer, marker, mode
):
    # Accident: old original groups survive generation-safe successful account replacement.
    first, second = establish_accounts(native, signer)
    originals = plant_originals(native, marker)
    transition(native, signer, mode, first, second)
    wire = outgoing(native, marker)
    assert not any(row.get('id') in {item['id'] for item in originals} for row in wire), (
        'I12/I13/U1: a new connection never sends prior-account public or opaque originals'
    )
    assert wire == [{'role': 'user', 'content': 'Fresh visible question'}], (
        'I12/I13/U1: outgoing new-scope history contains exactly the supplied fresh user input'
    )


@pytest.mark.parametrize('marker', ['omitted', 'unchanged'])
def test_unchanged_connection_continuation_preserves_both_originals(native, signer, marker):
    native.authenticate(signer)
    originals = plant_originals(native, marker)
    wire = outgoing(native, marker)
    assert wire[1:] == originals, (
        'I13/U1: ordinary unchanged-connection continuation retains exact '
        'public and opaque originals'
    )


@pytest.mark.parametrize(
    'mode', ['saved-other-account', 'saved-same-account', 'sign-in', 'expiry-reconnect']
)
def test_old_blocked_history_does_not_poison_a_new_authenticated_scope(native, signer, mode):
    first, second = establish_accounts(native, signer)
    malformed_history = request(native, 'unchanged')
    malformed_history['history'] = [
        {
            'type': 'tool_result',
            'call_id': 'unmatched-account-A-result',
            'ok': True,
            'code': '',
            'result': {'literal': 'prior-scope-only'},
        }
    ]
    before = len(native.last['requests'])
    rejected = native.command('send', payload=malformed_history)
    assert (
        not rejected['reply']['ok']
        and rejected['reply']['code'] == 'edi.assistant.interrupted'
        and len(rejected['requests']) == before
    ), 'I13/U1: original inconsistent account-A history creates a visible blocked recovery state'
    blocked = native.command('send', payload=request(native, 'unchanged'))
    assert not blocked['reply']['ok'], (
        'I13/U1: unchanged blocked scope cannot silently restart itself'
    )
    transition(native, signer, mode, first, second)
    assert outgoing(native, 'unchanged') == [
        {'role': 'user', 'content': 'Fresh visible question'}
    ], 'I12/I13/U1: successful connection replacement retires only the old blocked conversation'


def test_explicit_new_conversation_retires_old_originals_within_same_connection(native, signer):
    native.authenticate(signer)
    originals = plant_originals(native, 'unchanged')
    value = request(native, 'unchanged')
    value['conversation_id'] = 'user-explicit-new-conversation'
    sent = native.command('send', payload=value)
    assert sent['reply']['ok'], 'I13/U1: explicit user conversation restart remains supported'
    wire = json.loads(sent['requests'][-1]['body'])['input']
    assert wire == [{'role': 'user', 'content': 'Fresh visible question'}] and all(
        item not in wire for item in originals
    ), 'I13/U1: deliberate restart clears old originals without an account change'


@pytest.mark.parametrize('mode', ['failed-sign-in', 'sign-out'])
def test_existing_failure_and_sign_out_scope_controls_clear_originals(native, signer, mode):
    native.authenticate(signer)
    originals = plant_originals(native, 'unchanged')
    if mode == 'failed-sign-in':
        native.command('fail', value='browser')
        failed = native.command('sign_in')
        assert not failed['reply']['ok'], (
            'I12/U1: actual browser-dependency failure reaches normal connection failure'
        )
        native.command('fail', value='')
    else:
        native.command('sign_out')
        native.automatic()
        index = len(native.last['requests']) - 1
        assert native.last['requests'][index]['url'] == transport.AUTH + '/independent-revoke', (
            'I12/U1: normal sign-out reaches the canonical fixture revocation request'
        )
        native.handled.add(index)
        native.respond(index, None)
        assert native.last['state']['status'] != 'ready', (
            'I12/U1: sign-out retires the authenticated connection'
        )
    native.authenticate(signer)
    wire = outgoing(native, 'unchanged')
    assert wire == [{'role': 'user', 'content': 'Fresh visible question'}] and all(
        item not in wire for item in originals
    ), 'I12/I13/U1: failure and sign-out controls retire exact prior original output'
