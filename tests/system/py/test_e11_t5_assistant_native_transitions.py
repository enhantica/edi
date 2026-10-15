"""Independent review-16 native request, timer and Qt-wire accident paths."""

from __future__ import annotations

import base64
import importlib.util
import json
import os
import subprocess
from pathlib import Path

import pytest

from tests.fixtures.assistant.response_events import message_start, text_fragment

ROOT = Path(__file__).resolve().parents[3]
_spec = importlib.util.spec_from_file_location(
    'e11_native_transitions', Path(__file__).with_name('test_e11_t5_assistant_native.py')
)
transport = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(transport)
native, signer = transport.native, transport.signer


@pytest.mark.parametrize('case', ['complete', 'http-error', 'truncated'])
def test_real_qt_transport_distinguishes_truncated_success_status_from_http_error(case):
    # Accident: a real Qt connection failure carrying HTTP 200 is mapped to transport success.
    value = os.environ.get('EDI_ASSISTANT_QT_TRANSPORT_PROBE')
    binary = (
        Path(value)
        if value
        else ROOT / 'build/assistant-native-tests/assistant_qt_transport_probe'
    )
    assert binary.is_file(), (
        'I12/I13/S7: real production Qt request component is linked before wire measurement'
    )
    result = subprocess.run(
        [str(binary), case], capture_output=True, text=True, timeout=4, check=False
    )
    assert result.returncode == 0, (
        'I13/S7: local actual Qt wire completes once within its bounded component run'
    )
    observed = json.loads(result.stdout)
    assert observed['sent'] and observed['headers'] == observed['finished'] == 1, (
        'I13/S7: the independent server reaches real HTTP headers and one completion'
    )
    assert observed['body_exact'], (
        'I13/S7: the complete-looking SSE body precedes actual transport settlement'
    )
    assert observed['status'] == (503 if case == 'http-error' else 200), (
        'I13/S7: actual status metadata is retained independently of network success'
    )
    assert observed['success'] is (case != 'truncated'), (
        'I13/S7: truncated HTTP 200 fails transport; complete HTTP errors remain distinct'
    )


@pytest.mark.parametrize('status', [302, 401, 429, 500])
def test_unsuccessful_inference_status_never_dispatches_valid_sse_tools(native, signer, status):
    # Accident: native feeds a non-200 error body to the real parser before status refusal.
    native.authenticate(signer)
    before = len(native.last['requests'])
    native.command('send', payload=transport.provider_request(native))
    index = next(
        i
        for i in range(before, len(native.last['requests']))
        if native.last['requests'][i]['url'] == transport.API + '/responses'
    )
    native.command(
        'headers', index=index, status=status, headers=[['Content-Type', 'text/event-stream']]
    )
    event_count = len(native.last['events'])
    item = {
        'id': 'error-body-tool',
        'type': 'function_call',
        'call_id': 'forbidden-error-call',
        'name': 'inspect_project',
        'arguments': '{}',
        'status': 'completed',
    }
    wire = (
        'data: '
        + json.dumps({'type': 'response.output_item.done', 'output_index': 0, 'item': item})
        + '\n\n'
    ).encode()
    native.command('data', index=index, base64=base64.b64encode(wire).decode())
    native.command('finish', index=index, failure=0)
    incoming = native.last['events'][event_count:]
    assert not any(event.get('type') == 'tool_call' for event in incoming), (
        'I3/I12/S7: unsuccessful inference bodies never become trusted semantic tool calls'
    )
    assert native.last['state'].get('last_error'), (
        'I13/S7: actual unsuccessful HTTP status is visibly refused'
    )


@pytest.mark.parametrize(
    ('field', 'invalid'),
    [
        ('history', {}),
        ('tools', {}),
        ('context', []),
        ('text', {}),
        ('turn_id', 7),
        ('request_id', []),
        ('conversation_id', {}),
    ],
)
def test_malformed_nested_request_refuses_before_any_native_wire(native, signer, field, invalid):
    native.authenticate(signer)
    request = transport.provider_request(native)
    before = len(native.last['requests'])
    original = native.last['records']
    result = native.command('send', payload={**request, field: invalid})
    assert result['reply'].get('ok') is False, (
        'I3/S9: malformed required nested request types refuse without coercion'
    )
    assert len(result['requests']) == before, (
        'I12/S9: malformed request admission performs no inference network operation'
    )
    assert result['records'] == original, (
        'I12/S9: malformed inference input changes no valid own grant'
    )


@pytest.mark.parametrize('callback', ['headers', 'finish', 'data'])
@pytest.mark.parametrize(
    'clock', ['inclusive-total', 'inclusive-idle', 'backwards', 'before-idle']
)
def test_callback_checks_its_deadline_without_a_prior_owner_poll(native, signer, callback, clock):
    # Accident: callbacks renew/finish after expiry because only poll checks the prior clock.
    native.authenticate(signer)
    sent = native.command('send', payload=transport.provider_request(native))
    assert sent['reply']['ok'], 'I13/S8: actual inference admission precedes the callback deadline'
    index = len(sent['requests']) - 1
    if callback != 'headers':
        native.command(
            'headers', index=index, status=200, headers=[['Content-Type', 'text/event-stream']]
        )
    if callback == 'finish':
        event = {
            'type': 'response.completed',
            'response': {'id': 'on-time-body', 'status': 'completed', 'output': []},
        }
        native.command(
            'data',
            index=index,
            base64=base64.b64encode(('data: ' + json.dumps(event) + '\n\n').encode()).decode(),
        )
    if callback == 'data':
        native.command(
            'data',
            index=index,
            base64=base64.b64encode(
                ''.join(
                    'data: ' + json.dumps(event) + '\n\n' for event in message_start()
                ).encode()
            ).decode(),
        )
    samples = native.last['services'].count('elapsed')
    native.command(
        'elapse_unpolled',
        milliseconds={
            'inclusive-total': 900000,
            'inclusive-idle': 120000,
            'backwards': -1,
            'before-idle': 119999,
        }[clock],
    )
    assert native.last['services'].count('elapsed') == samples, (
        'I10/S8: injected clock changes are observed by the callback before any owner poll'
    )
    if callback == 'headers':
        native.command(
            'headers',
            index=index,
            status=200,
            headers=[['Content-Type', 'text/event-stream']],
            defer_events=True,
        )
    elif callback == 'data':
        event = text_fragment('LATE-CALLBACK-TEXT')
        native.command(
            'data',
            index=index,
            base64=base64.b64encode(('data: ' + json.dumps(event) + '\n\n').encode()).decode(),
            defer_events=True,
        )
    else:
        native.command('finish', index=index, failure=0, defer_events=True)
    if clock == 'before-idle':
        assert not native.last['state'].get('last_error'), (
            'I10/S8: actual callbacks remain valid immediately before the inclusive idle deadline'
        )
        if callback == 'data':
            assert any(
                'LATE-CALLBACK-TEXT' in event.get('text', '') for event in native.last['events']
            ), 'I3/S8: the on-time data control really reaches its public stream sink'
        return
    assert native.last['state'].get('last_error'), (
        'I10/I13/S8: late/backwards-clock callbacks refuse even before an owner timer poll'
    )
    assert native.last['requests'][index]['cancelled'], (
        'I10/S8: a callback at an expired/invalid clock cancels its actual operation'
    )
    assert not any(
        'LATE-CALLBACK-TEXT' in event.get('text', '') for event in native.last['events']
    ), 'I3/I10/S8: expired callback bytes cannot become newly public text'


def test_empty_association_cannot_become_matching_valid_registration_and_grant(native, signer):
    # Accident: equality of two empty host strings substitutes for nonempty verified association.
    native.authenticate(signer)
    records = native.last['records']
    registrations = [row for row in records if row['key'].startswith('1:')]
    registration = registrations[0]['key'][2:]
    replacements = []
    for row in records:
        if row['key'].startswith(('1:', '2:')):
            value = json.loads(row['bytes'])
            assert 'ext_agent_host_id' in value, (
                'I12/S9: native-created records expose the admitted stable-host association'
            )
            value['ext_agent_host_id'] = ''
            replacements.append({'key': row['key'], 'utf8': json.dumps(value)})
    native.command('store_put_batch', records=replacements)
    native.command('recreate')
    before = len(native.last['requests'])
    original = native.last['records']
    native.command('connect_saved', id=registration)
    assert not native.ready(), (
        'I12/S9: two empty own-record associations cannot establish readiness'
    )
    assert len(native.last['requests']) == before, (
        'I12/S9: invalid host association performs no catalog/renewal network work'
    )
    assert native.last['records'] == original, (
        'I12/S9: invalid association refuses without replacing an admitted own record'
    )


@pytest.mark.parametrize('prefix', ['0:', '1:', '2:'])
def test_absent_record_with_payload_is_not_silent_missing_data(native, signer, prefix):
    native.authenticate(signer)
    original = native.last['records']
    selected = next(row['key'] for row in original if row['key'].startswith(prefix))
    registration = next(row['key'][2:] for row in original if row['key'].startswith('1:'))
    native.command('absent_payload', key=selected)
    before_browser = len(native.last['browsers'])
    before_requests = len(native.last['requests'])
    native.command('clear_store_receipts')
    native.command('recreate')
    if prefix == '0:':
        native.command('sign_in')
    else:
        native.command('connect_saved', id=registration)
    assert any(row['key'] == selected for row in native.last['store_reads']), (
        'I12/S9: contradictory typed absence reaches the intended actual record read'
    )
    assert (
        len(native.last['browsers']) == before_browser
        and len(native.last['requests']) == before_requests
    ), 'I12/S9: contradictory absent-with-bytes is refused before sign-in or renewal'
    assert native.last['records'] == original and not native.ready(), (
        'I12/S9: malformed typed absence preserves own records without fabricating readiness'
    )


@pytest.mark.parametrize('accounts', [2, 3])
def test_all_loaded_registration_metadata_shares_the_declared_retained_record_budget(
    native, signer, accounts
):
    # Accident: individually valid loaded display metadata is retained without a combined ceiling.
    native.authenticate(signer)
    assert native.ready(), (
        'I12/S6: the first metadata source is an actual verified offline account'
    )
    saved = list(native.last['records'])
    host_record = next(row for row in saved if row['key'].startswith('0:'))
    for account in range(1, accounts):
        separate = transport.Native(Path(native.process.args[0]))
        try:
            separate.command('store_put', key=host_record['key'], utf8=host_record['bytes'])
            separate.command('recreate')
            separate.authenticate(
                signer, claims_patch={'sub': 'independent-account-' + str(account)}
            )
            assert separate.ready(), (
                'I12/S6: each metadata source is a separate genuine verified account'
            )
            saved.extend(
                row for row in separate.last['records'] if not row['key'].startswith('0:')
            )
        finally:
            separate.close()
    native.command(
        'store_put_batch', records=[{'key': row['key'], 'utf8': row['bytes']} for row in saved]
    )
    replacements = []
    for row in saved:
        if row['key'].startswith('1:'):
            record = json.loads(row['bytes'])
            record['label'] = 'L' * 900000
            raw = json.dumps(record, separators=(',', ':'))
            assert len(raw.encode()) < 1048576, (
                'I12/S6: each complete actual registration stays below its per-record byte cap'
            )
            replacements.append({'key': row['key'], 'utf8': raw})
    assert len(replacements) == accounts, (
        'I12/S6: independently counted distinct account mappings reach aggregate metadata loading'
    )
    native.command('store_put_batch', records=replacements)
    protected = native.last['records']
    native.command('clear_store_receipts')
    native.command('recreate')
    assert native.last['records'] == protected and native.last['writes'] == [], (
        'I12/S6: aggregate loading never rewrites or drops admitted own mappings'
    )
    if accounts == 3:
        assert accounts * 900000 > 2097152, (
            'I12/S6: independent metadata payload alone exceeds the aggregate record cap'
        )
        assert native.last['state'].get('last_error_code') == 'edi.assistant.resource_exhausted', (
            'I12/S6: aggregate valid own-record retention refuses with its declared quota type'
        )
    else:
        assert accounts * 900000 + 16384 < 2097152, (
            'I12/S6: positive metadata leaves room for actual wrappers and stable-host fields'
        )
        assert not native.last['state'].get('last_error'), (
            'I12/S6: ordinary individually and collectively bounded metadata remains loadable'
        )
