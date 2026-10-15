"""Safe missing-member facts, retaining refusal and execution semantics.

Official event/item schema:
https://developers.openai.com/api/reference/resources/responses/streaming-events
Diagnostics are independently counted structural facts, never raw provider contents.
This does not authorize accepting an omitted output item or executing its tool call.
"""

from __future__ import annotations

import importlib.util
import os
import re
from pathlib import Path

import pytest

from tests.fixtures.assistant.diagnostic_streams import sse
from tests.fixtures.assistant.response_events import message_complete, message_start, text_fragment

ROOT = Path(__file__).resolve().parents[3]
_spec = importlib.util.spec_from_file_location(
    'structural_stream_protocol', ROOT / 'tests/integration/py/test_e11_t5_assistant_protocol.py'
)
protocol = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(protocol)
PRIVATE = 'UNRECOGNIZED_PRIVATE_CONTENT_' + 'Å' * 80


@pytest.fixture
def parser():
    binary = Path(
        os.environ.get(
            'EDI_ASSISTANT_CORE_PROBE', ROOT / 'build/app/core/assistant_contract_probe'
        )
    )
    assert binary.is_file(), 'I13: structural diagnostics exercise the real public stream parser'
    host = protocol.Host(binary)
    host.command('stream_start')
    try:
        yield host
    finally:
        host.close()


def snapshot(kind, status='completed', index=0):
    item = {'id': PRIVATE + str(index), 'type': kind, 'status': status}
    if kind == 'message':
        item.update(
            role='assistant',
            content=[{'type': 'output_text', 'text': PRIVATE, 'annotations': [], 'logprobs': []}],
        )
    elif kind == 'reasoning':
        item.update(summary=[], encrypted_content=PRIVATE)
    elif kind == 'function_call':
        item.update(call_id=PRIVATE + '-call', name='inspect_project', arguments='{}')
    return item


def facts(message, aliases):
    """Accept equivalent named-value punctuation, without fixing English prose."""
    keys = '|'.join(re.escape(key) for key in aliases)
    values = re.findall(r'(?<![\w])(?:' + keys + r')[\s\"\']*[:=][\s\"\']*([\w.-]+)', message)
    # Closed equivalent display labels; arbitrary category strings remain forbidden.
    labels = {'yes': 'true', 'no': 'false', 'other': 'unknown'}
    return [labels.get(value, value) for value in values]


@pytest.mark.parametrize(
    ('kind', 'status', 'wire_done', 'count'),
    [
        ('message', 'completed', True, 1),
        ('message', 'in_progress', False, 1),
        ('reasoning', 'completed', True, 1),
        ('function_call', 'completed', True, 1),
        (PRIVATE, 'completed', True, 1),
        ('reasoning', PRIVATE, True, 1),
        ('reasoning', 'completed', True, 12),
    ],
    ids=[
        'message-done',
        'message-unfinished',
        'reasoning-done',
        'function-done',
        'unknown-kind',
        'unknown-status',
        'multiple-missing',
    ],
)
def test_missing_terminal_member_has_bounded_allowlisted_structural_facts(
    parser, kind, status, wire_done, count
):
    events = []
    for index in range(count):
        item = snapshot(kind, status, index)
        events.append({
            'type': 'response.output_item.' + ('done' if wire_done else 'added'),
            'output_index': index,
            'item': item,
        })
    prefix = parser.command('stream_feed', bytes=list(sse(events)))
    assert prefix['reply']['ok'], (
        'I13: independently planted retained-item prefix reaches terminal membership refusal'
    )
    terminal = {
        'type': 'response.completed',
        'response': {'id': PRIVATE + '-response', 'status': 'completed', 'output': []},
    }
    result = parser.command('stream_feed', bytes=list(sse([terminal])))
    reply = result['reply']
    assert not reply['ok'] and reply['code'] == 'edi.assistant.invalid_argument', (
        'I3/I13: diagnostics preserve the original missing-member refusal and stable code'
    )
    assert not any(
        e.get('type') == 'tool_call'
        for e in result['stream_events'][len(prefix['stream_events']) :]
    ), (
        'I3/I13: terminal refusal emits no new executable call; '
        'earlier parser events remain native-buffered'
    )
    message = reply['value']['message']
    assert 0 < len(message.encode()) <= 512 and PRIVATE not in message and 'Å' not in message, (
        'I3/I13: structural diagnostics remain within error_bytes and never echo raw IDs, '
        'text, arguments, reasoning or unknown category/status strings'
    )
    expected = {
        ('missing_kind', 'first_kind', 'kind', 'type'): kind if kind != PRIVATE else 'unknown',
        ('missing_status', 'first_status', 'status'): status if status != PRIVATE else 'unknown',
        ('missing_wire_done', 'wire_done', 'done'): 'true' if wire_done else 'false',
        ('missing_count', 'missing'): str(count),
        ('retained_count', 'retained'): str(count),
        ('final_count', 'terminal_count', 'final', 'terminal'): '0',
        ('unfinished_count', 'unfinished'): '0' if wire_done else str(count),
    }
    observed = {names[0]: facts(message.lower(), names) for names in expected}
    assert all(value in observed[names[0]] for names, value in expected.items()), (
        'I13: the same rejection exposes only allowlisted missing kind/status/wire-done '
        'and independently known aggregate counts: ' + str(observed)
    )
    finished = parser.command('stream_finish')['reply']
    assert finished['code'] == reply['code'] and finished['value']['message'] == message, (
        'I13: finish preserves the first bounded structural refusal rather than replacing it'
    )


def test_matching_complete_message_remains_successful_with_exact_public_text(parser):
    text = 'Hello — independent control'
    result = parser.command(
        'stream_feed',
        bytes=list(sse([*message_start(), text_fragment(text), *message_complete(text)])),
    )
    assert result['reply']['ok'] and parser.command('stream_finish')['reply']['ok'], (
        'I13: safe structural diagnostics preserve a genuine matching completed response'
    )
    assert (
        ''.join(e['text'] for e in result['stream_events'] if e['type'] == 'text_delta') == text
    ), 'I3/I13: the valid matching-message control preserves its complete public text'
