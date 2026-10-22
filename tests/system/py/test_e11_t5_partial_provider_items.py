"""Explicit incomplete item semantics from published Responses schema, not owner SSE."""

from __future__ import annotations

import importlib.util
import os
from pathlib import Path

import pytest

from tests.fixtures.assistant.diagnostic_streams import sse

ROOT = Path(__file__).resolve().parents[3]


def load(name, relative):
    spec = importlib.util.spec_from_file_location(name, ROOT / relative)
    value = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(value)
    return value


protocol = load('partial_protocol', 'tests/integration/py/test_e11_t5_assistant_protocol.py')
services = load('partial_native', 'tests/system/py/test_e11_t5_assistant_native.py')
transport = services.native
signer = services.signer
TOOLS = [
    {
        'name': 'inspect_project',
        'description': 'Read-only independent inspection',
        'input_schema': {'type': 'object', 'properties': {}, 'additionalProperties': False},
    }
]


def call(status, arguments):
    return {
        'id': 'partial-function',
        'type': 'function_call',
        'call_id': 'partial-call',
        'name': 'inspect_project',
        'arguments': arguments,
        'status': status,
    }


def opening(item):
    return {
        'type': 'response.output_item.added',
        'output_index': 0,
        'item': {**item, 'status': 'in_progress', 'arguments': ''},
    }


def final(item, status):
    return {
        'type': 'response.' + status,
        'response': {
            'id': 'partial-response',
            'status': status,
            'output': [item],
            'error': (
                {'code': 'server_error', 'message': 'Independent interrupted generation'}
                if status == 'failed'
                else None
            ),
            'incomplete_details': {'reason': 'max_output_tokens'}
            if status == 'incomplete'
            else None,
        },
    }


def parser():
    binary = Path(
        os.environ.get(
            'EDI_ASSISTANT_CORE_PROBE', ROOT / 'build/app/core/assistant_contract_probe'
        )
    )
    assert binary.is_file(), 'I13/D3: partial item witnesses use the actual public parser'
    value = protocol.Host(binary)
    value.command('stream_start')
    return value


@pytest.mark.parametrize('status', ['failed', 'incomplete'])
def test_legitimate_partial_tool_is_bounded_nonexecuting_evidence_not_local_json_failure(status):
    # Both output_item.done and terminal-only snapshots are distinct concrete producer channels.
    observations = []
    for item_done in [False, True]:
        host = parser()
        try:
            item = call('incomplete', '{"unfinished":')
            events = [
                opening(item),
                {
                    'type': 'response.function_call_arguments.delta',
                    'item_id': item['id'],
                    'output_index': 0,
                    'delta': item['arguments'],
                },
            ]
            if item_done:
                events.append({
                    'type': 'response.output_item.done',
                    'output_index': 0,
                    'item': item,
                })
            events.append(final(item, status))
            result = host.command('stream_feed', bytes=list(sse(events)))
            finished = host.command('stream_finish')['reply']
            output = host.command('stream_output')['reply']
            terminals = [e for e in result['stream_events'] if e['type'] == 'turn_finished']
            observations.append({
                'item_done_channel': item_done,
                'legitimate_partial_not_local_json_error': result['reply']['ok'],
                'settled_non_success_stream': finished['ok'],
                'no_normalized_executable_call': not any(
                    e['type'] == 'tool_call' for e in result['stream_events']
                ),
                'one_non_success_terminal': len(terminals) == 1
                and terminals[0]['status'] != 'completed',
                'incomplete_absent_from_completed_replay': output == [],
            })
        finally:
            host.close()
    assert all(
        all(value for key, value in row.items() if key != 'item_done_channel')
        for row in observations
    ), (
        'I2/I3/I13/D3: both actual terminal-only and item-done partial snapshots remain '
        'bounded nonexecuting evidence without parsing unfinished executable JSON: '
        + str(observations)
    )


@pytest.mark.parametrize('kind', ['function_call', 'message'])
def test_contradictory_success_cannot_dispatch_an_explicit_incomplete_item(
    transport, signer, kind
):
    transport.authenticate(signer)
    index, request = services.start_inference(transport, tools=TOOLS)
    item = (
        call('incomplete', '{}')
        if kind == 'function_call'
        else {
            'id': 'partial-message',
            'type': 'message',
            'role': 'assistant',
            'status': 'incomplete',
            'content': [
                {
                    'type': 'output_text',
                    'text': 'Independent incomplete text',
                    'annotations': [],
                    'logprobs': [],
                }
            ],
        }
    )
    services.stream(
        transport,
        index,
        [
            {'type': 'response.output_item.done', 'output_index': 0, 'item': item},
            {
                'type': 'response.completed',
                'response': {
                    'id': 'contradictory-response',
                    'status': 'completed',
                    'output': [item],
                },
            },
        ],
    )
    terminal = [
        e
        for e in transport.last['events']
        if e.get('type') == 'turn_finished' and e.get('request_id') == request['request_id']
    ]
    assert terminal and all(e['status'] != 'completed' for e in terminal), (
        'I13/D3: enclosing completed status cannot override an explicit incomplete output item'
    )
    assert not any(e.get('type') == 'tool_call' for e in transport.last['events']), (
        'I2/I13/D3: syntactically valid partial tool arguments never authorize dispatch'
    )


def test_complete_function_control_remains_executable_parser_evidence():
    host = parser()
    try:
        item = call('completed', '{}')
        result = host.command(
            'stream_feed',
            bytes=list(
                sse([
                    opening(item),
                    {'type': 'response.output_item.done', 'output_index': 0, 'item': item},
                    final(item, 'completed'),
                ])
            ),
        )
        assert result['reply']['ok'] and host.command('stream_finish')['reply']['ok'], (
            'I13/D3: explicit completed valid object remains an accepted control'
        )
        calls = [e for e in result['stream_events'] if e['type'] == 'tool_call']
        assert (
            len(calls) == 1
            and calls[0]['arguments'] == {}
            and calls[0]['call_id'] == item['call_id']
        ), 'I3/I13/D3: valid complete control preserves exact original arguments and correlation'
    finally:
        host.close()


def test_complete_function_control_dispatches_only_after_successful_native_settlement(
    transport, signer
):
    transport.authenticate(signer)
    index, request = services.start_inference(transport, tools=TOOLS)
    item = call('completed', '{}')
    services.stream(
        transport,
        index,
        [
            opening(item),
            {'type': 'response.output_item.done', 'output_index': 0, 'item': item},
            final(item, 'completed'),
        ],
    )
    calls = [e for e in transport.last['events'] if e.get('type') == 'tool_call']
    assert len(calls) == 1 and calls[0]['arguments'] == {}, (
        'I3/I13/D3: normal complete function control dispatches once with its original object'
    )
    terminal = [
        e
        for e in transport.last['events']
        if e.get('type') == 'turn_finished' and e.get('request_id') == request['request_id']
    ]
    assert len(terminal) == 1 and terminal[0]['status'] == 'completed', (
        'I13/D3: ordinary valid completed item and response keep actual native success'
    )
