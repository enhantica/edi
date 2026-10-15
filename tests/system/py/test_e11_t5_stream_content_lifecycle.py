"""N4: official Responses identity and content completion, independent of controller text.

Primary source: https://developers.openai.com/api/reference/resources/responses/streaming-events
retrieved 2026-10-15. Required item_id/content_index and the text/refusal/part done
semantics define the oracle. Literal planted payloads, never producer-generated expected text.
"""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
_spec = importlib.util.spec_from_file_location(
    'content_protocol', ROOT / 'tests/integration/py/test_e11_t5_assistant_protocol.py'
)
protocol = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(protocol)
host = protocol.host


def wire(host, events, *, fragmented=False):
    raw = ''.join(
        'data: ' + json.dumps(event, ensure_ascii=False, separators=(',', ':')) + '\n\n'
        for event in events
    ).encode()
    if fragmented:
        result = None
        for offset in range(0, len(raw), 7):
            result = host.command('stream_feed', bytes=list(raw[offset : offset + 7]))
            if not result['reply']['ok']:
                return result
        return result
    return host.command('stream_feed', bytes=list(raw))


def item(*, state='in_progress', kind='message'):
    if kind == 'function_call':
        return {
            'id': 'item-one',
            'type': kind,
            'status': 'completed',
            'call_id': 'independent-call',
            'name': 'inspect_project',
            'arguments': '{}',
        }
    return {
        'id': 'item-one',
        'type': kind,
        'role': 'assistant',
        'status': state,
        'content': [] if state == 'in_progress' else [part('output_text', 'ORIGINAL-Å')],
    }


def part(channel, text=''):
    if channel == 'refusal':
        return {'type': 'refusal', 'refusal': text}
    return {'type': 'output_text', 'text': text, 'annotations': [], 'logprobs': []}


def scoped(kind, **fields):
    if kind in {'output_text.delta', 'output_text.done'}:
        fields.setdefault('logprobs', [])
    return {
        'type': 'response.' + kind,
        'item_id': 'item-one',
        'output_index': 0,
        'content_index': 0,
        'sequence_number': 2,
        **fields,
    }


def begin(host, channel='output_text'):
    host.command('stream_start')
    result = wire(
        host,
        [
            {
                'type': 'response.output_item.added',
                'output_index': 0,
                'sequence_number': 0,
                'item': item(),
            },
            scoped('content_part.added', sequence_number=1, part=part(channel)),
        ],
    )
    assert result['reply']['ok'], (
        'I3/N4: an official open message and matching declared content part admit valid deltas'
    )
    return result


@pytest.mark.parametrize('channel', ['output_text', 'refusal'])
@pytest.mark.parametrize('prior', ['unstarted', 'open', 'completed', 'wrong-kind'])
def test_missing_item_identity_cannot_bypass_message_state(host, channel, prior):
    # Accident: omitting identity skips the completed/wrong-kind/unknown-item guard.
    host.command('stream_start')
    if prior == 'open':
        begin(host, channel)
    elif prior != 'unstarted':
        started = wire(
            host,
            [
                {
                    'type': 'response.output_item.done',
                    'output_index': 0,
                    'sequence_number': 0,
                    'item': item(
                        state='completed',
                        kind='function_call' if prior == 'wrong-kind' else 'message',
                    ),
                }
            ],
        )
        assert started['reply']['ok'], (
            'I3/N4: the independently planted prior item reaches admission'
        )
    before = host.last['stream_events']
    delta = scoped(channel + '.delta', delta='FORBIDDEN-IDENTITY-FREE')
    del delta['item_id']
    refused = wire(host, [delta])
    assert not refused['reply']['ok'], (
        'I3/N4: provider text/refusal deltas require their actual item identity in every state'
    )
    assert refused['stream_events'] == before, (
        'I3/N4: missing provider identity cannot append public text absent from original replay'
    )


@pytest.mark.parametrize('channel', ['output_text', 'refusal'])
@pytest.mark.parametrize(
    'index',
    [None, -1, 0.5, '0', 7],
    ids=['missing', 'negative', 'fractional', 'string', 'unstarted-part'],
)
def test_invalid_content_identity_cannot_append_to_a_live_message(host, channel, index):
    begin(host, channel)
    before = host.last['stream_events']
    delta = scoped(channel + '.delta', delta='FORBIDDEN-CONTENT')
    if index is None:
        del delta['content_index']
    else:
        delta['content_index'] = index
    refused = wire(host, [delta])
    assert not refused['reply']['ok'], (
        'I3/N4: content identity is a required nonnegative integer naming an actual live part'
    )
    assert refused['stream_events'] == before, (
        'I3/N4: malformed or unknown content identity changes no previously emitted text'
    )


@pytest.mark.parametrize('channel', ['output_text', 'refusal'])
@pytest.mark.parametrize('closure', ['channel-done', 'part-done'])
def test_finalized_content_is_immutable_before_output_item_completion(host, channel, closure):
    # Accident: a final part remains mutable while its containing message is still open.
    begin(host, channel)
    original = 'ORIGINAL-PbSO₄-🧪'
    delta = wire(host, [scoped(channel + '.delta', delta=original)])
    assert delta['reply']['ok'], 'I3/N4: complete original public text is admitted before closure'
    marker = (
        scoped(channel + '.done', **{('refusal' if channel == 'refusal' else 'text'): original})
        if closure == 'channel-done'
        else scoped('content_part.done', part=part(channel, original))
    )
    marker['sequence_number'] = 3
    closed = wire(host, [marker])
    assert closed['reply']['ok'], 'I3/N4: the official content-finalization marker is admitted'
    before = closed['stream_events']
    late = wire(
        host, [scoped(channel + '.delta', sequence_number=4, delta='FORBIDDEN-AFTER-PART-DONE')]
    )
    assert not late['reply']['ok'], (
        'I3/N4: text/refusal and part-done each close their actual content before item-done'
    )
    assert late['stream_events'] == before, (
        'I3/N4: late content cannot alter a completed public part or diverge from original replay'
    )


@pytest.mark.parametrize('channel', ['output_text', 'refusal'])
def test_two_distinct_content_parts_retain_exact_fragmented_unicode_without_cross_closing(
    host, channel
):
    begin(host, channel)
    first, second = 'Ångström ', 'PbSO₄ 🧪'
    final_item = {
        **item(state='completed'),
        'content': [part(channel, first), part(channel, second)],
    }
    events = [
        scoped(channel + '.delta', delta=first),
        scoped(channel + '.done', **{('refusal' if channel == 'refusal' else 'text'): first}),
        scoped('content_part.done', part=part(channel, first)),
        scoped('content_part.added', content_index=1, part=part(channel)),
        scoped(channel + '.delta', content_index=1, delta=second),
        scoped(
            channel + '.done',
            content_index=1,
            **{('refusal' if channel == 'refusal' else 'text'): second},
        ),
        scoped('content_part.done', content_index=1, part=part(channel, second)),
        {
            'type': 'response.output_item.done',
            'output_index': 0,
            'sequence_number': 8,
            'item': final_item,
        },
        {
            'type': 'response.completed',
            'sequence_number': 9,
            'response': {
                'id': 'independent-response',
                'status': 'completed',
                'output': [final_item],
            },
        },
    ]
    for sequence, event in enumerate(events, start=2):
        event['sequence_number'] = sequence
    completed = wire(host, events, fragmented=True)
    assert completed['reply']['ok'], (
        'I3/N4: closing one valid part does not close another declared part of the same message'
    )
    assert ''.join(e.get('text', '') for e in completed['stream_events']) == first + second, (
        'I3/N4: actual arbitrary UTF-8 byte fragmentation preserves both literal public parts once'
    )
    finished = host.command('stream_finish')
    assert finished['reply']['ok'], 'I3/N4: valid complete multi-part provider output finishes'
