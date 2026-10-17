"""Local mock-provider conversation correctness through actual Session/VM/native owners.

Only test-owned projects and deterministic callbacks are used. Expected call IDs,
arguments and scalar edits are planted inputs; no fitted/scientific output is an oracle.
"""

from __future__ import annotations

import base64
import importlib.util
import json
from pathlib import Path

import pytest

from tests.fixtures.assistant.response_events import message_complete, message_start, text_fragment

ROOT = Path(__file__).resolve().parents[3]
_spec = importlib.util.spec_from_file_location(
    'pairing_real_owner', ROOT / 'tests/system/app/test_e11_t5_assistant_connected.py'
)
owner = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(owner)
ui = owner.ui
signer = owner.signer


def item(call_id, name='inspect_project', arguments=None):
    return {
        'type': 'function_call',
        'id': 'item-' + call_id,
        'call_id': call_id,
        'name': name,
        'arguments': json.dumps(arguments or {}, separators=(',', ':')),
        'status': 'completed',
    }


def call_events(calls):
    events = []
    for index, call in enumerate(calls):
        events.extend([
            {
                'type': 'response.output_item.added',
                'output_index': index,
                'item': {**call, 'arguments': '', 'status': 'in_progress'},
            },
            {
                'type': 'response.function_call_arguments.done',
                'item_id': call['id'],
                'output_index': index,
                'arguments': call['arguments'],
            },
            {'type': 'response.output_item.done', 'output_index': index, 'item': call},
        ])
    return events


def response_events(calls, ending):
    events = call_events(calls)
    output = list(calls)
    if ending == 'refused':
        text = 'Please choose another approach.'
        refusal = message_start(item_id='refusal-item', channel='refusal')
        refusal.append(text_fragment(text, item_id='refusal-item', channel='refusal'))
        refusal.extend(message_complete(text, item_id='refusal-item', channel='refusal'))
        output.extend(refusal[-1]['response']['output'])
        for event in refusal[:-1]:
            if 'output_index' in event:
                event['output_index'] = len(calls)
            events.append(event)
    status = 'completed' if ending in {'completed', 'refused'} else ending
    if ending != 'transport-failure':
        events.append({
            'type': 'response.' + status,
            'response': {'id': 'independent-response', 'status': status, 'output': output},
        })
    for sequence, event in enumerate(events):
        event['sequence_number'] = sequence
    return events


def requests_after(actor, index):
    return [
        (i, request)
        for i, request in enumerate(actor.last['requests'])
        if i > index and request['url'] == owner.native_protocol.API + '/responses'
    ]


def wire_items(request):
    body = json.loads(request['body'])
    assert isinstance(body.get('input'), list), (
        'I3/N3: pairing is checked against the actual recorded outgoing provider input'
    )
    return body['input']


def paired(request):
    rows = wire_items(request)
    calls = [row for row in rows if row.get('type') == 'function_call']
    outputs = [row for row in rows if row.get('type') == 'function_call_output']
    assert all(
        sum(out.get('call_id') == call['call_id'] for out in outputs) == 1 for call in calls
    ), 'I3/N3: every replayed original function call has exactly one correlated complete output'
    return calls, outputs


def payload_rows(actor, call_id):
    return [
        row['payload']
        for row in actor.last['ui']['messages']
        if isinstance(row.get('payload'), dict)
        and row['payload'].get('type') == 'tool_result'
        and row['payload'].get('call_id') == call_id
    ]


@pytest.mark.parametrize('ending', ['failed', 'incomplete', 'refused', 'transport-failure'])
def test_unexecuted_mock_call_cannot_poison_the_next_user_request(ui, signer, tmp_path, ending):
    # Accident: original deferred calls enter normal replay after an unsuccessful response.
    ui.command('open', path=str(owner.copy_project(tmp_path, 'pairing_source')))
    owner.authenticate(ui, signer)
    index, _ = owner.begin_request(ui)
    original = ui.last['ui']['project']
    call_id = 'unexecuted-' + ending
    events = response_events([item(call_id)], ending)
    if ending == 'transport-failure':
        wire = ''.join('data: ' + json.dumps(event) + '\n\n' for event in events).encode()
        ui.command('data', index=index, base64=base64.b64encode(wire).decode())
        ui.command('finish', index=index, failure=1)
    else:
        owner.native_protocol.stream(ui, index, events, width=97)
    assert ui.last['ui']['last_error'], (
        'I13/N3: unsuccessful mock completion remains a visible recoverable conversation failure'
    )
    assert not any(
        row.get('ok') is True for row in payload_rows(ui, call_id)
    ) and not requests_after(ui, index), (
        'I3/N3: unsuccessful deferred calls do not execute or silently auto-continue'
    )
    assert ui.last['ui']['project'] == original, (
        'I4/N3: an unexecuted provider call preserves the exact independent original project'
    )
    _, request = owner.begin_request(ui)
    _calls, outputs = paired(request)
    for row in outputs:
        if row.get('call_id') == call_id:
            result = json.loads(row['output'])
            assert result['ok'] is False and result['code'], (
                'I3/N3: unexecuted calls may have honest refusal outputs, never invented success'
            )


def test_completed_mock_call_keeps_original_arguments_and_its_real_output(ui, signer, tmp_path):
    ui.command('open', path=str(owner.copy_project(tmp_path, 'pairing_positive')))
    owner.authenticate(ui, signer)
    index, _ = owner.begin_request(ui)
    call_id = 'ordinary-completed-call'
    call = item(call_id)
    owner.native_protocol.stream(ui, index, response_events([call], 'completed'))
    ui.command('inspect')  # Observe the real queued owner continuation before inspecting wire.
    pending = requests_after(ui, index)
    assert len(pending) == 1, (
        'I3/N3: an ordinary successful real tool continues the same conversation exactly once'
    )
    calls, outputs = paired(pending[0][1])
    original = next((row for row in calls if row.get('call_id') == call_id), None)
    outcome = next((row for row in outputs if row.get('call_id') == call_id), None)
    assert original == call and outcome is not None, (
        'I3/I13/N3: normal continuation preserves the exact planted original call and its output'
    )
    payload = json.loads(outcome['output'])
    assert payload['call_id'] == call_id and payload['ok'] is True, (
        'I3/N3: positive wire output carries the actual successful correlated controller result'
    )


def test_revision_changing_mock_batch_keeps_strict_fence_and_complete_wire_pairing(
    ui, signer, tmp_path
):
    # Accident: first approved edit advances revision; the next declined call loses its outcome.
    ui.command('open', path=str(owner.copy_project(tmp_path, 'pairing_edits')))
    owner.authenticate(ui, signer)
    index, _ = owner.begin_request(ui)
    owner.native_protocol.stream(
        ui, index, owner.function_events('propose_plan', owner.proposal('One explicit cell path'))
    )
    proposal = ui.last['ui']['pending_plan']
    assert proposal and proposal['plan_id'], (
        'I2/N3: the actual provider proposal is displayed before trusted user approval'
    )
    before = len(ui.last['requests'])
    ui.command('click', name='assistant.plan.approve')
    pending = [
        (i, request)
        for i, request in enumerate(ui.last['requests'][before:], start=before)
        if request['url'] == owner.native_protocol.API + '/responses'
    ]
    assert len(pending) == 1, (
        'I2/I3/N3: real user approval creates one new current provider request'
    )
    index, _ = pending[0]
    ui.command('headers', index=index, status=200, headers=[['Content-Type', 'text/event-stream']])
    original = ui.last['ui']['project']
    first = original['cell_a'] + 0.02
    calls = [
        item(
            call_id,
            'set_parameters',
            {
                'plan_id': proposal['plan_id'],
                'values': [{'path': 'structure.cell.length_a', 'value': value}],
            },
        )
        for call_id, value in [
            ('accepted-edit', first),
            ('old-revision-edit', original['cell_a'] + 0.07),
        ]
    ]
    owner.native_protocol.stream(ui, index, response_events(calls, 'completed'))
    ui.command('inspect')  # Apply queued context/disclosure handling before the recovery action.
    assert ui.last['ui']['project']['cell_a'] == first, (
        'I2/I4/N3: first edit applies and the captured-old-revision edit stays declined'
    )
    admitted = payload_rows(ui, 'accepted-edit')
    assert admitted and admitted[-1]['ok'] is True, (
        'I3/N3: the actual first successful edit keeps its complete visible result'
    )
    pending = requests_after(ui, index)
    visible_restart = bool(ui.last['ui']['last_error'])
    if not pending:
        assert ui.last['ui']['last_error'] and not ui.last['ui']['can_cancel'], (
            'I3/N3: withheld malformed continuation requires an explicit visible recovery boundary'
        )
        _, request = owner.begin_request(ui)
    else:
        assert len(pending) == 1, 'I3/N3: a checked batch yields one actual provider continuation'
        request = pending[0][1]
    retained, outputs = paired(request)
    if any(row.get('call_id') == 'old-revision-edit' for row in retained):
        outcome = next(row for row in outputs if row.get('call_id') == 'old-revision-edit')
        declined = json.loads(outcome['output'])
        assert declined['ok'] is False and declined['code'] == 'edi.assistant.stale_revision', (
            'I2/I3/N3: complete replay preserves the old-revision refusal for the batch'
        )
    else:
        assert visible_restart, (
            'I3/N3: restarting instead of replaying a declined batch remains explicitly visible'
        )
