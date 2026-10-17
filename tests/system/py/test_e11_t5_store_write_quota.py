"""U2: write quotas at real isolated Qt callbacks and genuine offline token completion.

Limits and atomic-category expectations come from the accepted packet. Byte lengths use
independent compact UTF-8 encoding of fixture inputs and declared credential metadata.
"""

from __future__ import annotations

import base64
import importlib.util
import json
from pathlib import Path

import pytest

_spec = importlib.util.spec_from_file_location(
    'write_store_contract', Path(__file__).with_name('test_e11_t5_assistant_store.py')
)
store_contract = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(store_contract)
transport = store_contract.transport
store = store_contract.store
signer = store_contract.signer
CAP = 1048576
ROTATION = 2097152


def encoded(value):
    return json.dumps(value, ensure_ascii=False, separators=(',', ':')).encode()


@pytest.mark.parametrize('kind', [0, 1, 2], ids=['host', 'mapping', 'credentials'])
@pytest.mark.parametrize('over', [False, True], ids=['inclusive-cap', 'one-byte-over'])
def test_actual_default_write_classifies_known_size_and_preserves_atomic_record(store, kind, over):
    # Accident: the write sibling of typed read/list admission collapses quota into I/O failure.
    key = '0:host' if kind == 0 else str(kind) + ':' + 'a' * 64
    store.command('store_put', key=key, utf8='{"previous":"intact"}')
    before = store.last['disk']
    value = {'literal': ''}
    value['literal'] = 'W' * (CAP + int(over) - len(encoded(value)))
    raw = encoded(value).decode()
    assert len(raw.encode()) == CAP + int(over), (
        'I12/S6/U2: independent UTF-8 fixture reaches the inclusive write '
        'cap or exactly one byte over'
    )
    result = store.command('store_write', key=key, utf8=raw)
    if over:
        assert result['disk'] == before and result['writes'] == [], (
            'I12/S6/U2: oversized atomic replacement preserves the prior '
            'whole record without writes'
        )
        assert result['reply'] == {'thrown_refusal': 'resource_exhausted', 'written_bytes': 0}, (
            'I12/S6/U2: actual default callback exposes known write quota '
            'distinctly from ordinary I/O'
        )
    else:
        assert result['reply'] == {'status': 'ok', 'written_bytes': CAP}, (
            'I12/S6/U2: actual whole-record write accepts the inclusive byte boundary'
        )
        assert store_contract.stored(store)[key] == value and all(
            row['owner_only'] for row in result['disk']
        ), 'I12/S6/U2: successful at-cap replacement stores the exact supplied private record'
    assert result['requests'] == [] and result['browsers'] == [], (
        'I12/S6/U2: direct isolated store admission starts no authorization or HTTP operation'
    )


@pytest.mark.parametrize('kind', [0, 1, 2], ids=['host', 'mapping', 'credentials'])
def test_actual_default_write_permission_failure_is_not_quota(store, kind):
    key = '0:host' if kind == 0 else str(kind) + ':' + 'b' * 64
    store.command('store_put', key=key, utf8='{"previous":"permission-control"}')
    store.command('store_permissions', key=key, private=False)
    before = store.last['disk']
    result = store.command('store_write', key=key, utf8='{"replacement":"small"}')
    assert result['reply'] == {'status': 'failed', 'written_bytes': 0}, (
        'I12/S6/U2: actual protection/I/O failure remains StoreStatus.failed, never a quota label'
    )
    assert result['disk'] == before and result['writes'] == [], (
        'I12/S6/U2: refused ordinary replacement preserves prior bytes and permissions'
    )
    store.command('store_permissions', key=key, private=True)
    recovered = store.command('store_write', key=key, utf8='{"replacement":"small"}')
    assert recovered['reply']['status'] == 'ok', (
        'I12/S6/U2: restoring actual private permissions reaches the same successful callback'
    )


def test_actual_credential_lock_failure_is_distinct_and_recovers_after_release(store):
    key = '2:' + 'c' * 64
    store.command('store_put', key=key, utf8='{"previous":"locked-control"}')
    read = store.command('store_read', key=key)
    assert read['reply']['status'] == 'ok', (
        'I12/S6/U2: real credentials read acquires its own record lock'
    )
    before = read['disk']
    refused = store.command('store_contending_write', key=key, utf8='{"replacement":"small"}')
    assert (
        refused['reply'] == {'status': 'failed', 'written_bytes': 0} and refused['disk'] == before
    ), (
        'I12/S6/U2: a second real store owner cannot replace locked '
        'credentials or mislabel contention as quota'
    )
    store.command('recreate')
    recovered = store.command('store_contending_write', key=key, utf8='{"replacement":"small"}')
    assert recovered['reply']['status'] == 'ok', (
        'I12/S6/U2: release of the original real owner permits the identical contending write'
    )


def complete_sized_grant(actor, signer, renewal, over):
    sign, actor.jwks = signer
    if renewal:
        actor.authenticate(signer)
        assert actor.ready(), (
            'I12/U2: renewal starts with an independently verified usable original grant'
        )
        original = store_contract.stored(actor)
        identity = store_contract.registration(actor)
        selected = actor.command('connect_saved', id=identity)
        assert selected['reply']['ok'], (
            'I12/U2: actual saved-grant renewal reaches the canonical token request'
        )
        nonce = None
    else:
        query = actor.begin()
        original = store_contract.stored(actor)
        nonce = query['nonce']
        actor.command(
            'callback',
            query={
                'code': 'synthetic-code',
                'state': query['state'],
                'client_id': transport.CLIENT,
            },
        )
        identity = None
    index = len(actor.last['requests']) - 1
    assert actor.last['requests'][index]['url'] == transport.AUTH + '/api/accounts/oauth/token', (
        'I12/U2: complete byte-boundary input is supplied only to the '
        'real canonical token exchange'
    )
    label = 'L' * 5000 + '@synthetic.invalid'
    claims = {
        'iss': transport.AUTH,
        'aud': transport.CLIENT,
        'sub': transport.SUBJECT,
        'iat': transport.WALL,
        'exp': transport.WALL + 3600,
        'email': label,
    }
    if nonce is not None:
        claims['nonce'] = nonce
    actor.jwt = sign(claims)
    tokens = {
        'access_token': 'synthetic-new-access',
        'refresh_token': '',
        'id_token': actor.jwt,
        'token_type': 'Bearer',
        'expires_in': 3600,
        'scope': transport.SCOPES,
    }
    previous = original.get('2:' + identity, {}) if identity else {}
    expected = {
        **previous,
        **{key: value for key, value in tokens.items() if key != 'expires_in'},
        'client_id': transport.CLIENT,
        'subject': transport.SUBJECT,
        'ext_agent_host_id': original['0:host']['id'],
        'label': label,
        'expires_at': transport.WALL + 3600,
    }
    padding = CAP + int(over) - len(encoded(expected))
    assert padding > 0, (
        'I12/U2: independently sized synthetic refresh bytes have positive bounded length'
    )
    tokens['refresh_token'] = expected['refresh_token'] = 'R' * padding
    assert len(encoded(expected)) == CAP + int(over) and len(encoded(tokens)) <= CAP, (
        'I12/S6/U2: valid token JSON fits HTTP while persisted metadata '
        'alone crosses the record boundary'
    )
    assert len(encoded(expected)) + len(encoded(tokens)) + len(encoded(previous)) <= ROTATION, (
        'I12/S6/U2: current, incoming and proposed credential encodings '
        'genuinely fit their aggregate role'
    )
    actor.command('clear_store_receipts')
    actor.handled.add(index)
    later_requests = len(actor.last['requests'])
    actor.command(
        'headers', index=index, status=200, headers=[['Content-Type', 'application/json']]
    )
    raw = encoded(tokens)
    for offset in range(0, len(raw), 65536):
        actor.command(
            'data', index=index, base64=base64.b64encode(raw[offset : offset + 65536]).decode()
        )
    actor.command('finish', index=index, failure=0)
    actor.automatic()
    return expected, original.get('2:' + identity) if identity else None, identity, later_requests


@pytest.mark.parametrize('renewal', [False, True], ids=['initial-signed-grant', 'signed-renewal'])
@pytest.mark.parametrize('over', [False, True], ids=['inclusive-cap', 'one-byte-over'])
def test_genuine_signed_token_completion_preserves_write_quota_category_and_prior_grant(
    store, signer, renewal, over
):
    expected, old_grant, identity, later_requests = complete_sized_grant(
        store, signer, renewal, over
    )
    if over:
        assert not store.ready(), (
            'I12/S6/U2: oversized completion never claims authenticated readiness'
        )
        if renewal:
            assert store_contract.stored(store)['2:' + identity] == old_grant, (
                'I12/S6/U2: failed oversize rotation leaves the previous usable whole grant intact'
            )
        else:
            assert not any(key.startswith('2:') for key in store_contract.stored(store)), (
                'I12/S6/U2: refused first completion publishes no oversized or '
                'partial credential record'
            )
        assert not any(key.startswith('2:') for key in store.last['writes']), (
            'I12/S6/U2: known oversize credential size is refused before its write callback'
        )
        assert not any(
            request['url'] == transport.API + '/models'
            for request in store.last['requests'][later_requests:]
        ), 'I12/S6/U2: refused record completion starts no later inference catalog operation'
        assert store.last['state']['last_error_code'] == 'edi.assistant.resource_exhausted', (
            'I12/S6/U2: genuine token-to-record size refusal retains the '
            'declared public resource category'
        )
    else:
        assert store.ready(), (
            'I12/S6/U2: genuine independently signed at-cap credential remains supported'
        )
        saved = store_contract.stored(store)
        identity = store_contract.registration(store)
        assert saved['2:' + identity] == expected, (
            'I12/S6/U2: atomic successful completion stores all independently '
            'declared grant and identity fields'
        )
    assert all(row['owner_only'] and row['bytes'] <= CAP for row in store.last['disk']), (
        'I12/S6/U2: every actual persisted own record remains private and within the inclusive cap'
    )
