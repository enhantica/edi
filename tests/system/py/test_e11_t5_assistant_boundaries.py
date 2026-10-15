"""Approved finite policy and immutable protocol identities on the real core boundary."""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
_spec = importlib.util.spec_from_file_location(
    'e11_t5_boundary_protocol', ROOT / 'tests/integration/py/test_e11_t5_assistant_protocol.py'
)
protocol = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(protocol)
host = protocol.host

# Public policy: relay E11-T5 packet R3/R4, accepted plan 3e6840e49.
WIRE = 8_388_608
RETAINED = 4_194_304
EVENTS = 8192
ITEMS = 256
CALLS = 64


def wire(event):
    return protocol.sse(event).decode()


def chunks(host, events):
    return host.command('stream_chunks', chunks=[wire(event) for event in events])


def resource(reply):
    assert not reply['ok'], 'I3/I10: an exhausted aggregate cannot admit more provider work'
    assert reply['code'] == 'edi.assistant.resource_exhausted', (
        'I3: a valid over-quota aggregate has the approved stable resource refusal'
    )


def test_stream_wire_budget_counts_comments_and_is_sticky(host):
    host.command('stream_start')
    heartbeat = ':' + ' ' * 65533 + '\n\n'
    assert len(heartbeat.encode()) * 128 == WIRE, (
        'I3: the independent comment witness reaches exactly the approved wire budget'
    )
    exact = host.command('stream_repeat', text=heartbeat, count=128)
    assert exact['reply']['accepted'] == 128 and exact['reply']['last']['ok'], (
        'I3: the inclusive wire boundary accepts complete comments without retaining them'
    )
    over = host.command('stream_feed', bytes=[ord(':')])
    resource(over['reply'])
    resource(host.command('stream_finish')['reply'])


def test_stream_event_budget_counts_unknown_records_without_retaining_them(host):
    host.command('stream_start')
    unknown = wire({'type': 'future.provider.event'})
    exact = host.command('stream_repeat', text=unknown, count=EVENTS)
    assert exact['reply']['accepted'] == EVENTS and exact['reply']['last']['ok'], (
        'I3: unknown nonempty data records are accepted through the inclusive event boundary'
    )
    over = host.command('stream_repeat', text=unknown, count=1)
    resource(over['reply']['last'])
    assert not over['stream_events'], 'I3: unknown provider records create no trusted UI events'


@pytest.mark.parametrize(('kind', 'limit'), [('message', ITEMS), ('function_call', CALLS)])
def test_unique_provider_item_and_call_bounds_are_inclusive(host, kind, limit):
    host.command('stream_start')

    def event(index):
        item = {'id': 'item-' + str(index), 'type': kind}
        if kind == 'function_call':
            item.update(call_id='call-' + str(index), name='inspect_project', arguments='')
        else:
            item.update(role='assistant', content=[], status='in_progress')
        return {'type': 'response.output_item.added', 'output_index': index, 'item': item}

    exact = chunks(host, [event(i) for i in range(limit)])
    assert exact['reply']['accepted'] == limit and exact['reply']['last']['ok'], (
        'I3: unique identities fit through the independently counted inclusive item/call bound'
    )
    repeated = chunks(host, [event(0)])
    assert repeated['reply']['last']['ok'], (
        'I3: an identical repeated identity consumes no additional retained item/call slot'
    )
    over = chunks(host, [event(limit)])
    resource(over['reply']['last'])


def test_partial_arguments_across_distinct_calls_share_one_retained_budget(host):
    host.command('stream_start')
    records = []
    partial = '{"text":"' + 'x' * 600_000
    for index in range(8):
        item_id = 'item-' + str(index)
        records.extend([
            {
                'type': 'response.output_item.added',
                'output_index': index,
                'item': {
                    'id': item_id,
                    'type': 'function_call',
                    'call_id': 'call-' + str(index),
                    'name': 'inspect_project',
                    'arguments': '',
                },
            },
            {
                'type': 'response.function_call_arguments.delta',
                'output_index': index,
                'item_id': item_id,
                'delta': partial,
            },
        ])
    assert len(partial.encode()) * 8 > RETAINED, (
        'I3: independently counted partial arguments exceed the shared retention cap'
    )
    assert sum(len(wire(v).encode()) for v in records) < WIRE, (
        'I3: retention witness stays under the independent wire cap'
    )
    result = chunks(host, records)
    resource(result['reply']['last'])
    assert not any(v['type'] == 'tool_call' for v in result['stream_events']), (
        'I3: exhausting incomplete arguments emits no executable tool'
    )


@pytest.mark.parametrize(
    'identifier',
    ['a' * 256, 'é' * 128, 'a' * 257, 'é' * 129],
    ids=['ascii-at', 'unicode-at', 'ascii-over', 'unicode-over'],
)
def test_provider_identifier_budget_uses_decoded_utf8_bytes(host, identifier):
    host.command('stream_start')
    result = chunks(
        host,
        [
            {
                'type': 'response.output_item.added',
                'output_index': 0,
                'item': {
                    'id': identifier,
                    'type': 'message',
                    'role': 'assistant',
                    'content': [],
                    'status': 'in_progress',
                },
            }
        ],
    )
    if len(identifier.encode()) <= 256:
        assert result['reply']['last']['ok'], 'I3: a provider ID at the UTF-8 byte cap is valid'
    else:
        assert not result['reply']['last']['ok'], (
            'I3: overlong provider IDs refuse before retention'
        )


def test_public_json_depth_is_bounded_before_unknown_field_validation(host):
    text = '{"schema":"edi.assistant/1","type":"message","x":' + '[' * 64 + '0' + ']' * 64 + '}'
    result = host.command('user_raw', text=text)
    protocol.refused(result, 'invalid_json')


@pytest.mark.parametrize('late_kind', ['text_delta', 'turn_finished'])
def test_completed_plan_response_cannot_be_reopened_by_a_late_callback(host, late_kind):
    host.start()
    proposal = {
        'summary': 'Inspect only',
        'groups': [{'id': 'cell', 'paths': ['structure.cell.length_a']}],
        'budget': {'max_trials': 1, 'max_iterations': 1, 'max_elapsed_ms': 1000},
        'objective': {'absolute_tolerance': 0.0, 'relative_tolerance': 0.0},
    }
    host.tool('propose_plan', proposal)
    binding = host.binding()
    closed = host.provider('turn_finished', **binding, status='completed')
    pending = closed['state']['pending_plan_id']
    assert pending, 'I2: a completed proposal remains available for the real user decision'
    fields = {'text': 'late'} if late_kind == 'text_delta' else {'status': 'failed'}
    result = host.provider(late_kind, **binding, **fields)
    assert not result['reply']['ok'], 'I3: a response terminal fences all later response callbacks'
    assert result['state']['pending_plan_id'] == pending, (
        'I2/I3: a stale terminal cannot erase or alter the completed user decision card'
    )
    assert result['snapshot'] == closed['snapshot'], (
        'I4: late response refusal changes no project state'
    )


def test_same_response_text_deltas_coalesce_without_losing_public_text(host):
    host.start()
    binding = host.binding()
    text = 'Ångström 🧪 '
    result = host.command(
        'provider_repeat', count=50, payload=protocol.envelope('text_delta', **binding, text=text)
    )
    assert result['reply']['accepted'] == 50, 'I3: ordinary streamed public text remains usable'
    host.tool('inspect_project')
    result = host.provider('turn_finished', **binding, status='completed')
    history = result['requests'][-1]['history']
    messages = [v for v in history if v.get('type') == 'message' and v.get('role') == 'assistant']
    assert len(messages) == 1 and messages[0]['text'] == text * 50, (
        'I3: adjacent deltas in one role/turn/request coalesce without dropping Unicode text'
    )


@pytest.mark.parametrize(
    ('field', 'replacement'),
    [
        ('id', 'changed-item'),
        ('call_id', 'changed-call'),
        ('name', 'diagnostics'),
    ],
)
def test_repeated_output_index_cannot_change_its_original_call_identity(host, field, replacement):
    host.command('stream_start')
    item = {
        'id': 'original-item',
        'type': 'function_call',
        'call_id': 'original-call',
        'name': 'inspect_project',
        'arguments': '',
    }
    exact = chunks(host, [{'type': 'response.output_item.added', 'output_index': 0, 'item': item}])
    assert exact['reply']['last']['ok'], 'I3: an initial provider call identity is admitted'
    result = chunks(
        host,
        [
            {
                'type': 'response.output_item.added',
                'output_index': 0,
                'item': {**item, field: replacement},
            }
        ],
    )
    assert not result['reply']['last']['ok'], (
        'I3: a repeated output index cannot overwrite its established call identity'
    )
    assert not any(v['type'] == 'tool_call' for v in result['stream_events']), (
        'I3: contradictory incomplete call identities execute no tool'
    )


def test_completed_call_arguments_cannot_be_extended_and_completed_again(host):
    host.command('stream_start')
    item = {
        'id': 'item',
        'type': 'function_call',
        'call_id': 'call',
        'name': 'inspect_project',
        'arguments': '',
    }
    initial = chunks(
        host,
        [
            {'type': 'response.output_item.added', 'output_index': 0, 'item': item},
            {
                'type': 'response.function_call_arguments.done',
                'output_index': 0,
                'item_id': 'item',
                'arguments': '{}',
            },
        ],
    )
    assert initial['reply']['last']['ok'], 'I3: a complete object emits the first immutable call'
    original = [v for v in initial['stream_events'] if v['type'] == 'tool_call']
    assert len(original) == 1, 'I3: the first completed argument boundary emits one call'
    late = chunks(
        host,
        [
            {
                'type': 'response.function_call_arguments.delta',
                'output_index': 0,
                'item_id': 'item',
                'delta': ' ',
            }
        ],
    )
    assert not late['reply']['last']['ok'], (
        'I3: argument deltas after execution cannot mutate a completed call'
    )
    assert [v for v in late['stream_events'] if v['type'] == 'tool_call'] == original, (
        'I3: late argument mutation cannot replace or repeat an emitted call'
    )


def test_completed_call_replay_is_independent_of_json_object_member_order(host):
    host.start()
    binding = host.binding()
    arguments = {
        'summary': 'Read only approved cell setup',
        'groups': [{'id': 'cell', 'paths': ['structure.cell.length_a']}],
        'budget': {'max_trials': 1, 'max_iterations': 2, 'max_elapsed_ms': 1000},
        'objective': {'absolute_tolerance': 0.0, 'relative_tolerance': 0.0},
    }
    fields = {
        **binding,
        'call_id': 'semantic-call',
        'name': 'propose_plan',
        'project_id': 'project-A',
        'revision': host.last['state']['revision'],
        'arguments': arguments,
    }
    first = host.provider('tool_call', **fields)
    assert first['reply']['ok'], 'I3: the initial complete semantic call is admitted'
    reordered = {**fields, 'arguments': dict(reversed(list(arguments.items())))}
    replay = host.provider('tool_call', **dict(reversed(list(reordered.items()))))
    assert replay['reply'] == first['reply'], (
        'I3: semantically identical JSON replay returns the recorded outcome '
        'regardless of object ordering'
    )
    assert replay['state']['pending_plan_id'] == first['state']['pending_plan_id'], (
        'I2/I3: replay does not create a second plan or execute the completed call again'
    )
