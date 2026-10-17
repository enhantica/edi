"""Actual native completion fence, independent original fixtures and reviewed S-R2.

Synthetic locally signed identity uses the existing offline NativeDependencies fixture.
Native sink delivery proves native release, not scientific approval or a live entitlement.
Optional output-union status follows official responses.ts at85e528a (review78).
"""

from __future__ import annotations

import base64
import copy
import importlib.util
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]


def load(name, relative):
    spec = importlib.util.spec_from_file_location(name, ROOT / relative)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


services = load('native_authority_services', 'tests/system/py/test_e11_t5_assistant_native.py')
originals = load('native_authority_originals', 'tests/system/py/test_e11_t5_stream_membership.py')
native = services.native
signer = services.signer
TOOLS = [
    {
        'name': 'inspect_project',
        'description': 'Read-only original fixture',
        'input_schema': {'type': 'object', 'properties': {}, 'additionalProperties': False},
    }
]


def feed(native, index, events):
    raw = ''.join(
        'data: ' + json.dumps(event, ensure_ascii=False, separators=(',', ':')) + '\n\n'
        for event in events
    ).encode()
    return native.command('data', index=index, base64=base64.b64encode(raw).decode())


def bound(result, request, kind):
    return [
        e
        for e in result['events']
        if e.get('type') == kind
        and e.get('request_id') == request['request_id']
        and e.get('turn_id') == request['turn_id']
        and e.get('connection_id') == request['connection_id']
    ]


@pytest.mark.parametrize('summary', ['empty', 'message-subset'])
def test_native_completed_text_and_opaque_original_survive_explicit_compact_summary(
    native, signer, summary
):
    native.authenticate(signer)
    index, request = services.start_inference(native)
    reasoning = originals.original('reasoning', 'native-opaque-A')
    del reasoning['status']  # Official output-union optional field, retained absent.
    message = originals.original('message', 'native-message-B')
    public = message['content'][0]['text']
    feed(
        native,
        index,
        [
            originals.item_event(reasoning),
            originals.item_event(message, 1),
            originals.complete([] if summary == 'empty' else [message]),
        ],
    )
    settled = native.command('finish', index=index, failure=0)
    terminals = bound(settled, request, 'turn_finished')
    assert len(terminals) == 1 and terminals[0]['status'] == 'completed', (
        'S-R2: actual native successful HTTP finish releases one completed text exchange '
        'when explicit compact final output omits only finalized nonexecuting originals'
    )
    assert ''.join(e['text'] for e in bound(settled, request, 'text_delta')) == public, (
        'S-R2: native visible text equals the planted public original, never opaque reasoning'
    )
    assert not bound(settled, request, 'inference_failed') and not bound(
        settled, request, 'tool_call'
    ), 'S-R2: a completed text-only native exchange is neither interrupted nor executable'


@pytest.mark.parametrize('delivery', ['done-original', 'terminal-only'])
@pytest.mark.parametrize('status', ['absent', 'completed'])
def test_native_complete_function_keeps_optional_status_and_actual_paired_next_wire(
    native, signer, delivery, status
):
    native.authenticate(signer)
    index, request = services.start_inference(native, tools=TOOLS)
    call = originals.original('function_call', 'native-function-A')
    if status == 'absent':
        del call['status']
    events = [originals.complete([call])]
    if delivery == 'done-original':
        events.insert(0, originals.item_event(call))
    before_finish = feed(native, index, events)
    assert not bound(before_finish, request, 'tool_call'), (
        'S-R2: validated logical completion cannot release native work before physical finish'
    )
    settled = native.command('finish', index=index, failure=0)
    calls = bound(settled, request, 'tool_call')
    terminals = bound(settled, request, 'turn_finished')
    assert len(calls) == 1 and calls[0]['call_id'] == call['call_id'], (
        'S-R2: finalized or terminal-only complete output-union calls may omit optional status '
        'without manufacturing a field or changing original correlation'
    )
    assert len(terminals) == 1 and terminals[0]['status'] == 'completed', (
        'S-R2: complete valid function membership settles successfully only after native finish'
    )
    history = [
        *request['history'],
        {'type': 'tool_call', 'call_id': call['call_id'], 'name': call['name'], 'arguments': {}},
        {
            'type': 'tool_result',
            'call_id': call['call_id'],
            'ok': True,
            'code': '',
            'result': {'fixture': 'original independently supplied read-only outcome'},
        },
    ]
    next_request = services.provider_request(
        native, request_id='next-paired-request', history=history
    )
    sent = native.command('send', payload=next_request)
    assert sent['reply']['ok'], (
        'S-R2: one correlated trusted mock result admits normal continuation'
    )
    outgoing = json.loads(sent['requests'][-1]['body'])['input']
    retained = [v for v in outgoing if v.get('type') == 'function_call']
    results = [v for v in outgoing if v.get('type') == 'function_call_output']
    assert retained == [call] and len(results) == 1 and results[0]['call_id'] == call['call_id'], (
        'S-R2: actual subsequent native wire pairs exact original callable metadata with '
        'its one supplied outcome, preserving optional-member absence'
    )


@pytest.mark.parametrize('fault', ['omitted', 'incomplete', 'failed', 'null', 'wrong-type'])
def test_native_unentitled_function_original_never_crosses_physical_finish(native, signer, fault):
    native.authenticate(signer)
    index, request = services.start_inference(native, tools=TOOLS)
    call = originals.original('function_call', 'native-refused-A')
    if fault != 'omitted':
        call['status'] = {'null': None, 'wrong-type': 17}.get(fault, fault)
    before_finish = feed(
        native,
        index,
        [
            originals.item_event(call, done=fault != 'omitted'),
            originals.complete([] if fault == 'omitted' else [call]),
        ],
    )
    settled = native.command('finish', index=index, failure=0)
    terminals = bound(settled, request, 'turn_finished')
    assert not bound(before_finish, request, 'tool_call') and not bound(
        settled, request, 'tool_call'
    ), (
        'S-R3: unfinalized omitted/explicit partial/failed/null/wrong-type call never releases '
        'actual native work despite complete parseable original arguments'
    )
    assert terminals and all(e['status'] != 'completed' for e in terminals), (
        'S-R2: rejected native call membership retains a visible non-success settlement'
    )


@pytest.mark.parametrize('later', ['contradictory-call', 'missing-message-status'])
def test_native_later_bad_sibling_cannot_release_earlier_valid_call(native, signer, later):
    native.authenticate(signer)
    index, request = services.start_inference(native, tools=TOOLS)
    first = originals.original('function_call', 'valid-earlier-call')
    second = originals.original(
        'function_call' if later == 'contradictory-call' else 'message', 'later-original'
    )
    summary_second = copy.deepcopy(second)
    if later == 'contradictory-call':
        summary_second['call_id'] = 'contradictory-final-call'
    else:
        del second['status']
        del summary_second['status']
    feed(
        native,
        index,
        [
            originals.item_event(first),
            originals.item_event(second, 1),
            originals.complete([first, summary_second]),
        ],
    )
    settled = native.command('finish', index=index, failure=0)
    assert not bound(settled, request, 'tool_call'), (
        'S-R2: whole-group validation contains a later bad sibling before any native call release'
    )
    terminals = bound(settled, request, 'turn_finished')
    assert terminals and all(e['status'] != 'completed' for e in terminals), (
        'S-R2: later invalid message/call authority cannot flush a successful executable prefix'
    )


@pytest.mark.parametrize('failure', ['trailing-malformed-record', 'transport-failure'])
def test_logical_completion_still_waits_for_actual_whole_native_stream_finish(
    native, signer, failure
):
    native.authenticate(signer)
    index, request = services.start_inference(native, tools=TOOLS)
    call = originals.original('function_call', 'finish-fenced-A')
    before_finish = feed(native, index, [originals.item_event(call), originals.complete([call])])
    assert not bound(before_finish, request, 'tool_call'), (
        'S-R2: a logical terminal does not bypass the independent native physical-finish fence'
    )
    if failure == 'trailing-malformed-record':
        native.command(
            'data', index=index, base64=base64.b64encode(b'data: {not-json}\n\n').decode()
        )
    settled = native.command(
        'finish', index=index, failure=1 if failure == 'transport-failure' else 0
    )
    assert not bound(settled, request, 'tool_call'), (
        'S-R2: trailing invalid provider bytes or actual transport failure revoke buffered calls'
    )
    terminals = bound(settled, request, 'turn_finished')
    assert terminals and all(e['status'] != 'completed' for e in terminals), (
        'S-R2: physical finish failure remains a visible interruption without an executable prefix'
    )
