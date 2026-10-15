"""R4/S6: actual Qt store and one connection's genuinely retained record roles.

Thresholds/representations are from the approved task packet. Every file is test-owned
under the component's QTemporaryDir/XDG root; genuine fixture identity uses the existing
signed offline PKCE/JWT route. No default user profile or live account is consulted.
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
import os
from pathlib import Path
from urllib.parse import parse_qs

import pytest

_spec = importlib.util.spec_from_file_location(
    'store_transport', Path(__file__).with_name('test_e11_t5_assistant_native.py')
)
transport = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(transport)
signer = transport.signer
RECORD_BYTES = 1048576
RETAINED_BYTES = 2097152
REGISTRATIONS = 32


@pytest.fixture
def store():
    binary = Path(
        os.environ.get(
            'EDI_ASSISTANT_STORE_PROBE',
            transport.ROOT / 'build/assistant-native-tests/assistant_store_contract_probe',
        )
    )
    assert binary.is_file(), (
        'I12/S6: actual Qt store component is linked before boundary measurement'
    )
    actor = transport.Native(binary, reply_timeout=5)
    try:
        result = actor.command('inspect')
        assert result['isolated_root'], (
            'I12/S6: real default store callbacks are confined to the test-owned '
            'temporary XDG root'
        )
        yield actor
    finally:
        actor.close()


def compact(value):
    return json.dumps(value, ensure_ascii=False, separators=(',', ':'))


def stored(actor):
    return {row['key']: json.loads(row['bytes']) for row in actor.last['records']}


def registration(actor):
    return next(row['key'][2:] for row in actor.last['records'] if row['key'].startswith('1:'))


@pytest.mark.parametrize('kind', [0, 1, 2], ids=['host', 'mapping', 'grant'])
@pytest.mark.parametrize('over', [False, True], ids=['exact-byte-cap', 'one-byte-over'])
def test_actual_default_store_record_read_and_public_caller_preserve_the_byte_boundary(
    store, signer, kind, over
):
    # Accident: actual oversized disk files collapse into a generic I/O failure at the caller.
    store.authenticate(signer)
    assert store.ready(), 'I12/S6: genuine offline validation precedes real owned-file measurement'
    identity = registration(store)
    key = '0:host' if kind == 0 else str(kind) + ':' + identity
    value = compact(stored(store)[key])
    target = RECORD_BYTES + int(over)
    raw = value + ' ' * (target - len(value.encode()))
    assert len(raw.encode()) == target, (
        'I12/S6: independently encoded complete JSON plus valid whitespace '
        'reaches the exact byte edge'
    )
    store.command('store_put', key=key, utf8=raw)
    before = store.last['disk']
    store.command('clear_store_receipts')
    read = store.command('store_read', key=key)
    assert read['reply'] == {
        'status': 'failed' if over else 'ok',
        'bytes': 0 if over else target,
    }, (
        'I12/S6: actual production store callback accepts the inclusive cap '
        'and refuses excess bytes'
    )
    assert read['store_reads'][-1]['key'] == key and read['disk'] == before, (
        'I12/S6: actual callback reach and complete owned-file preservation are observable'
    )
    requests, browsers = len(read['requests']), len(read['browsers'])
    result = store.command('connect_saved', id=identity) if kind == 2 else store.command('sign_in')
    assert result['disk'] == before and all(row['owner_only'] for row in result['disk']), (
        'I12/S6: owned JSON files remain byte-identical and private across read admission/refusal'
    )
    if over:
        assert len(result['requests']) == requests and len(result['browsers']) == browsers, (
            'I12/S6: oversized owned files start no browser or provider operation'
        )
        assert (
            not result['reply']['ok']
            and result['reply']['code'] == 'edi.assistant.resource_exhausted'
        ), (
            'I12/S6: default-store quota failure retains its declared typed '
            'category at the real caller'
        )
    else:
        assert result['reply']['ok'], (
            'I12/S6: valid complete records at the inclusive byte cap remain '
            'usable by their caller'
        )
        assert (
            len(result['requests']) > requests if kind == 2 else len(result['browsers']) > browsers
        ), (
            'I12/S6: the at-cap control reaches actual refresh or canonical '
            'browser dependency input'
        )


@pytest.mark.parametrize('count', [REGISTRATIONS, REGISTRATIONS + 1])
def test_actual_default_store_list_is_bounded_and_excess_has_typed_public_refusal(
    store, signer, count
):
    store.authenticate(signer)
    assert store.ready(), (
        'I12/S6: one real fixture registration anchors isolated listing preservation'
    )
    actual = registration(store)
    # These additional files are listing-only namespace fixtures, never account/grant proof.
    ids = {actual}
    ids.update(
        hashlib.sha256(('listing-only-' + str(i)).encode()).hexdigest() for i in range(count - 1)
    )
    store.command(
        'store_put_batch',
        records=[{'key': '1:' + identity, 'utf8': '{}'} for identity in sorted(ids - {actual})],
    )
    before = store.last['disk']
    listed = store.command('store_list')
    assert listed['disk'] == before, (
        'I12/S6: actual listing never changes isolated records or grants'
    )
    if count == REGISTRATIONS:
        assert listed['reply']['status'] == 'ok' and set(listed['reply']['ids']) == ids, (
            'I12/S6: the exact inclusive entry boundary returns all and only the '
            'supplied opaque IDs'
        )
    else:
        assert listed['reply'] == {'status': 'failed', 'ids': []}, (
            'I12/S6: actual default listing refuses the excess entry without a '
            'partial success list'
        )
        requests, browsers = len(listed['requests']), len(listed['browsers'])
        refused = store.command('sign_in')
        assert (
            refused['disk'] == before
            and len(refused['requests']) == requests
            and len(refused['browsers']) == browsers
        ), 'I12/S6: entry exhaustion preserves the existing grant and starts no authorization work'
        assert (
            not refused['reply']['ok']
            and refused['reply']['code'] == 'edi.assistant.resource_exhausted'
        ), (
            'I12/S6: entry quota refusal is typed distinctly from ordinary '
            'default-store I/O failure'
        )


def test_actual_empty_default_store_preserves_genuine_absence_without_creating_records(store):
    listed = store.command('store_list')
    assert listed['reply'] == {'status': 'ok', 'ids': []}, (
        'I12/S6: an actual empty isolated store is a supported successful listing'
    )
    for key in ['0:host', '1:' + 'a' * 64, '2:' + 'a' * 64]:
        absent = store.command('store_read', key=key)
        assert absent['reply'] == {'status': 'absent', 'bytes': 0} and absent['disk'] == [], (
            'I12/S6: actual absence has no bytes, is not a failure and creates no record'
        )


def finish_renewal(actor, index):
    # Existing verified-subject renewal may omit ID token; this is not a new identity proof.
    actor.respond(
        index,
        {
            'access_token': 'synthetic-renewed-access',
            'refresh_token': 'synthetic-renewed-refresh',
            'token_type': 'Bearer',
            'expires_in': 3600,
            'scope': transport.SCOPES,
        },
    )
    actor.automatic()


def prepare_owned_accounts(actor, signer, next_label_bytes):
    actor.authenticate(signer)
    assert actor.ready(), 'I12/S6: first account owns a genuinely verified offline grant'
    first = registration(actor)
    records = stored(actor)
    other = transport.Native(Path(actor.process.args[0]), reply_timeout=5)
    try:
        other.command('store_put', key='0:host', utf8=compact(records['0:host']))
        other.command('recreate')
        other.authenticate(signer, claims_patch={'sub': 'independent-next-subject'})
        assert other.ready(), 'I12/S6: next registration has its own real signed fixture identity'
        second = registration(other)
        records.update({
            key: value for key, value in stored(other).items() if not key.startswith('0:')
        })
    finally:
        other.close()
    for key, size in [
        ('1:' + first, 600000),
        ('2:' + first, 600000),
        ('1:' + second, next_label_bytes),
    ]:
        original = dict(records[key])
        records[key]['label'] = 'L' * size
        assert all(
            records[key][field] == value for field, value in original.items() if field != 'label'
        ), (
            'I12/S6: nonsecret fixture display growth preserves every verified '
            'identity and grant field'
        )
    assert all(len(compact(value).encode()) < RECORD_BYTES for value in records.values()), (
        'I12/S6: each independently encoded complete source record fits its '
        'own declared byte limit'
    )
    actor.command(
        'store_put_batch',
        records=[{'key': key, 'utf8': compact(value)} for key, value in records.items()],
    )
    actor.command('recreate')
    actor.command('clear_store_receipts')
    selected = actor.command('connect_saved', id=first)
    assert selected['reply']['ok'], (
        'I12/S6: the same actual connection loads its selected mapping and grant'
    )
    index = len(selected['requests']) - 1
    form = parse_qs(selected['requests'][index]['body'])
    assert form['grant_type'] == ['refresh_token'] and form['refresh_token'] == [
        records['2:' + first]['refresh_token']
    ], 'I12/S6: the actual refresh request proves the selected owned grant reached live use'
    assert {row['key'] for row in selected['store_reads']} == {'1:' + first, '2:' + first}, (
        'I12/S6: only the selected registration and grant were loaded, not other files on disk'
    )
    finish_renewal(actor, index)
    assert actor.ready() and actor.last['state']['label'] == records['1:' + first]['label'], (
        'I12/S6: the same connection owns its selected display identity and renewed current grant'
    )
    return first, second


@pytest.mark.parametrize('over', [False, True], ids=['within-one-owner', 'over-one-owner'])
def test_one_connections_current_and_newly_loaded_records_share_the_declared_budget(
    store, signer, over
):
    # Accident: disk-only totals are mistaken for live ownership, or current roles are omitted.
    first, second = prepare_owned_accounts(store, signer, 950000 if over else 600000)
    records = stored(store)
    sizes = [
        len(compact(records[key]).encode()) for key in ['1:' + first, '2:' + first, '1:' + second]
    ]
    assert sum(sizes[:2]) < RETAINED_BYTES and (sum(sizes) > RETAINED_BYTES) is over, (
        'I12/S6: independent complete encodings distinguish actual '
        'current-plus-incoming role pressure'
    )
    before = store.last['disk']
    requests = len(store.last['requests'])
    store.command('clear_store_receipts')
    result = store.command('connect_saved', id=second)
    assert any(
        row['key'] == '1:' + second and row['status'] == 'ok' for row in result['store_reads']
    ), 'I12/S6: new mapping bytes cross the actual default read callback while current roles exist'
    if over:
        assert (
            not result['reply']['ok']
            and result['reply']['code'] == 'edi.assistant.resource_exhausted'
        ), 'I12/S6: one connection refuses aggregate current and incoming own-record retention'
        assert (
            result['disk'] == before
            and len(result['requests']) == requests
            and not result['writes']
        ), 'I12/S6: aggregate refusal preserves both verified grants and starts no new refresh'
    else:
        assert result['reply']['ok'] and len(result['requests']) == requests + 1, (
            'I12/S6: genuinely bounded selection can load another mapped grant and '
            'start its refresh'
        )
        finish_renewal(store, len(result['requests']) - 1)
        assert store.ready(), (
            'I12/S6: bounded new ownership supports the complete real renewal/catalog route'
        )
