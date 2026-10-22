"""Known published field classification and first-error preservation, no raw payload echo."""

from __future__ import annotations

import importlib.util
import os
from pathlib import Path

import pytest

from tests.fixtures.assistant.diagnostic_streams import PRIVATE_MARKER, diagnostic_wire, sse
from tests.fixtures.assistant.response_events import message_complete, message_start, text_fragment

ROOT = Path(__file__).resolve().parents[3]
_spec = importlib.util.spec_from_file_location(
    'safe_parser_protocol', ROOT / 'tests/integration/py/test_e11_t5_assistant_protocol.py'
)
protocol = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(protocol)


@pytest.fixture
def parser():
    binary = Path(
        os.environ.get(
            'EDI_ASSISTANT_CORE_PROBE', ROOT / 'build/app/core/assistant_contract_probe'
        )
    )
    assert binary.is_file(), 'I13: safe diagnostics exercise the actual public stream parser'
    value = protocol.Host(binary)
    value.command('stream_start')
    try:
        yield value
    finally:
        value.close()


@pytest.mark.parametrize('field', ['item_id', 'output_index', 'delta'])
def test_known_invalid_field_reports_safe_event_and_field_without_echoing_values(parser, field):
    parser.command('stream_feed', bytes=list(sse(message_start(item_id='safe-message'))))
    event = text_fragment(PRIVATE_MARKER, item_id='safe-message')
    event['unrecognized_private_key_' + PRIVATE_MARKER] = PRIVATE_MARKER
    if field == 'item_id':
        del event['item_id']
    elif field == 'output_index':
        event[field] = PRIVATE_MARKER
    else:
        event[field] = {'private_note': PRIVATE_MARKER}
    result = parser.command('stream_feed', bytes=list(sse([event])))['reply']
    assert not result['ok'], 'I3/I13: invalid required fields remain decoder refusals'
    message = result['value']['message']
    assert 'response.output_text.delta' in message and field in message.replace(
        'response.output_text.delta', ''
    ), 'I13: safe known schema event and field identify the actual refusal stage'
    assert PRIVATE_MARKER not in message and len(message.encode()) <= 512, (
        'I3/I13: known-field context never echoes private values or unrecognized JSON keys'
    )


@pytest.mark.parametrize('case', ['malformed-json', 'changed-completed-item'])
def test_first_public_parser_reason_survives_repeated_feed_and_finish(parser, case):
    first = parser.command('stream_feed', bytes=list(diagnostic_wire(case)))['reply']
    assert not first['ok'] and first['value']['message'], (
        'I13: actual first refusal precedes repeated-feed and finish diagnostic preservation'
    )
    repeated = parser.command('stream_feed', bytes=list(b'data: {}\n\n'))['reply']
    finished = parser.command('stream_finish')['reply']
    assert all(
        not r['ok']
        and r['code'] == first['code']
        and r['value']['message'] == first['value']['message']
        for r in [repeated, finished]
    ), (
        'I13: later failed-state operations preserve the original bounded safe cause '
        'instead of erasing it with an already-failed placeholder'
    )


def test_malformed_unknown_payload_has_only_bounded_safe_json_diagnostic(parser):
    reply = parser.command('stream_feed', bytes=list(diagnostic_wire('malformed-json')))['reply']
    assert not reply['ok'] and PRIVATE_MARKER not in reply['value']['message'], (
        'I3/I13: malformed unknown JSON never leaks fixture secrets into the public diagnostic'
    )
    assert 0 < len(reply['value']['message'].encode()) <= 512, (
        'I13: malformed JSON produces a concrete bounded diagnostic rather than raw payload'
    )


def test_official_text_lifecycle_remains_a_successful_control(parser):
    text = 'Ordinary independent text — Å'
    result = parser.command(
        'stream_feed',
        bytes=list(sse([*message_start(), text_fragment(text), *message_complete(text)])),
    )
    assert result['reply']['ok'] and parser.command('stream_finish')['reply']['ok'], (
        'I13: diagnostic improvements do not weaken or reject a complete official text lifecycle'
    )
    deltas = [e['text'] for e in result['stream_events'] if e['type'] == 'text_delta']
    assert ''.join(deltas) == text, (
        'I3/I13: ordinary complete text preserves its exact public content'
    )


def test_official_opaque_reasoning_and_complete_tool_are_preserved_without_public_reasoning(
    parser,
):
    reasoning = {
        'id': 'safe-reasoning',
        'type': 'reasoning',
        'summary': [],
        'encrypted_content': PRIVATE_MARKER,
    }
    call = {
        'id': 'safe-function',
        'type': 'function_call',
        'call_id': 'safe-call',
        'name': 'inspect_project',
        'arguments': '{}',
        'status': 'completed',
    }
    events = [
        {
            'type': 'response.output_item.added',
            'output_index': 0,
            'item': {
                **reasoning,
                'encrypted_content': 'unfinished-prefix',
                'status': 'in_progress',
            },
        },
        {'type': 'response.output_item.done', 'output_index': 0, 'item': reasoning},
        {
            'type': 'response.output_item.added',
            'output_index': 1,
            'item': {**call, 'arguments': '', 'status': 'in_progress'},
        },
        {
            'type': 'response.function_call_arguments.done',
            'item_id': call['id'],
            'output_index': 1,
            'arguments': '{}',
        },
        {'type': 'response.output_item.done', 'output_index': 1, 'item': call},
        {
            'type': 'response.completed',
            'response': {
                'id': 'safe-response',
                'status': 'completed',
                'output': [reasoning, call],
            },
        },
    ]
    result = parser.command('stream_feed', bytes=list(sse(events)))
    assert result['reply']['ok'] and parser.command('stream_finish')['reply']['ok'], (
        'I13: published complete reasoning/function envelopes remain successful after diagnostics'
    )
    assert parser.command('stream_output')['reply'] == [reasoning, call], (
        'I3/I13: opaque completed reasoning and original tool arguments '
        'remain exact replay objects'
    )
    assert not any(
        e['type'] == 'text_delta' and PRIVATE_MARKER in e.get('text', '')
        for e in result['stream_events']
    ), 'I3/I13: opaque provider reasoning never becomes public text or a diagnostic payload'
