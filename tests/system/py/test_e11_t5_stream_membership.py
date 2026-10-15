"""T2-T4: started parts, complete output membership and opaque reasoning compatibility.

Independent official Responses schema: content-lifecycle-reference.json. All original
items/text below are planted inputs, never parser-generated correctness values.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

_spec = importlib.util.spec_from_file_location(
    'membership_content', Path(__file__).with_name('test_e11_t5_stream_content_lifecycle.py')
)
content = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(content)
host = content.host
wire = content.wire
KINDS = ['message', 'function_call', 'reasoning']


def original(kind, identity='original-A', *, done=True):
    common = {'id': identity, 'type': kind, 'status': 'completed' if done else 'in_progress'}
    if kind == 'message':
        return {
            **common,
            'role': 'assistant',
            'content': [content.part('output_text', 'PUBLIC-Å')] if done else [],
        }
    if kind == 'function_call':
        return {
            **common,
            'call_id': 'call-' + identity,
            'name': 'inspect_project',
            'arguments': '{}' if done else '',
        }
    return {
        **common,
        'summary': [],
        'content': [{'type': 'reasoning_text', 'text': 'NONPUBLIC-Å'}] if done else [],
        'encrypted_content': 'opaque-fixture-' + identity,
    }


def item_event(value, index=0, *, done=True):
    return {
        'type': 'response.output_item.' + ('done' if done else 'added'),
        'output_index': index,
        'sequence_number': 1,
        'item': value,
    }


def complete(items):
    return {
        'type': 'response.completed',
        'sequence_number': 10,
        'response': {'id': 'independent-response', 'status': 'completed', 'output': items},
    }


@pytest.mark.parametrize('channel', ['output_text', 'refusal'])
@pytest.mark.parametrize('marker', ['delta', 'channel-done', 'part-done'])
@pytest.mark.parametrize('prior', ['first-part', 'next-part'])
def test_contiguous_but_unstarted_content_cannot_declare_its_own_live_identity(
    host, channel, marker, prior
):
    # Accident: an index equal to the current part count manufactures a live part.
    if prior == 'next-part':
        content.begin(host, channel)
        index, text = 1, 'UNSTARTED-NEXT-Å'
    else:
        host.command('stream_start')
        admitted = wire(host, [item_event(content.item(), done=False)])
        assert admitted['reply']['ok'], 'I3/T2: the real empty message is open before part input'
        index, text = 0, ''
    if marker == 'part-done':
        event = content.scoped('content_part.done', part=content.part(channel, text))
    elif marker == 'channel-done':
        event = content.scoped(
            channel + '.done', **{('refusal' if channel == 'refusal' else 'text'): text}
        )
    else:
        event = content.scoped(channel + '.delta', delta=text)
    event['content_index'] = index
    before = host.last['stream_events']
    refused = wire(host, [event])
    assert not refused['reply']['ok'], (
        'I3/T2: contiguous live delta/done events require a previously started content identity'
    )
    assert refused['stream_events'] == before, (
        'I3/T2: neither empty nor nonempty unstarted content can publish or settle a part'
    )


@pytest.mark.parametrize('channel', ['output_text', 'refusal'])
def test_a_later_message_cannot_inherit_the_previous_messages_started_part(host, channel):
    host.command('stream_start')
    first = original('message')
    second = original('message', 'later-message', done=False)
    admitted = wire(host, [item_event(first), item_event(second, 1, done=False)])
    assert admitted['reply']['ok'], 'I3/T2: a later real message opens after a completed message'
    before = admitted['stream_events']
    refused = wire(
        host,
        [content.scoped(channel + '.delta', item_id=second['id'], output_index=1, delta='LATE')],
    )
    assert not refused['reply']['ok'] and refused['stream_events'] == before, (
        'I3/T2: started content belongs to its own item and cannot migrate to a later message'
    )


@pytest.mark.parametrize(
    ('first_kind', 'second_kind'),
    [(kind, kind) for kind in KINDS]
    + [('message', 'function_call'), ('function_call', 'reasoning'), ('reasoning', 'message')],
)
def test_distinct_original_items_cannot_share_one_output_position(host, first_kind, second_kind):
    # Accident: ID-to-index checks omit the reverse index-to-ID ownership.
    host.command('stream_start')
    first = wire(host, [item_event(original(first_kind))])
    assert first['reply']['ok'], 'I3/T3: one independently planted original item is admitted'
    before = first['stream_events']
    refused = wire(host, [item_event(original(second_kind, 'other-B'))])
    assert not refused['reply']['ok'], (
        'I3/T3: a provider output position belongs to exactly one message, call or opaque item'
    )
    assert refused['stream_events'] == before, (
        'I3/T3: a conflicting second item produces no additional public text or tool dispatch'
    )


@pytest.mark.parametrize('ending', ['delta', 'done'])
@pytest.mark.parametrize(
    'index', [None, '0', 0.5, -1, 1], ids=['missing', 'string', 'fraction', 'negative', 'other']
)
def test_function_argument_events_require_their_actual_output_position(host, ending, index):
    host.command('stream_start')
    call = original('function_call', done=False)
    admitted = wire(host, [item_event(call, done=False)])
    assert admitted['reply']['ok'], 'I3/T3: a genuine open call precedes argument identity checks'
    event = {
        'type': 'response.function_call_arguments.' + ending,
        'item_id': call['id'],
        'sequence_number': 2,
        **({'delta': '{}'} if ending == 'delta' else {'arguments': '{}'}),
    }
    if index is not None:
        event['output_index'] = index
    before = admitted['stream_events']
    refused = wire(host, [event])
    assert not refused['reply']['ok'] and refused['stream_events'] == before, (
        'I3/T3: argument delta/done require a typed position bound to the same original call'
    )


@pytest.mark.parametrize('kind', KINDS)
@pytest.mark.parametrize('ending', ['omitted', 'replaced'])
def test_final_response_cannot_omit_or_replace_previously_completed_items(host, kind, ending):
    # Accident: every retained item is done, but final output membership disagrees.
    host.command('stream_start')
    first = wire(host, [item_event(original(kind))])
    assert first['reply']['ok'], 'I3/T3: the planted completed item reaches actual retention'
    final = [] if ending == 'omitted' else [original(kind, 'replacement-B')]
    refused = wire(host, [complete(final)])
    assert not refused['reply']['ok'], (
        'I3/T3: final response output must account for each completed item at its own position'
    )
    assert not any(
        event.get('type') == 'turn_finished' and event.get('status') == 'completed'
        for event in refused['stream_events']
    ), 'I3/T3: conflicting final membership cannot authorize normal completed continuation'


@pytest.mark.parametrize('kind', KINDS)
def test_repeating_an_item_at_a_changed_position_is_not_a_matching_duplicate(host, kind):
    host.command('stream_start')
    value = original(kind)
    admitted = wire(host, [item_event(value)])
    assert admitted['reply']['ok'], (
        'I3/T3: each supported original kind has a bound first position'
    )
    refused = wire(host, [item_event(value, 1)])
    assert not refused['reply']['ok'], (
        'I3/T3: identical IDs cannot migrate between output positions'
    )


@pytest.mark.parametrize('kind', KINDS)
@pytest.mark.parametrize('delivery', ['terminal-only', 'matching-duplicate'])
def test_complete_snapshots_and_matching_duplicates_preserve_original_output(host, kind, delivery):
    host.command('stream_start')
    value = original(kind)
    events = [complete([value])]
    if delivery == 'matching-duplicate':
        events = [item_event(value), item_event(value), *events]
    accepted = wire(host, events)
    assert accepted['reply']['ok'] and host.command('stream_finish')['reply']['ok'], (
        'I3/T3: genuine complete snapshots and equal item/position duplicates remain usable'
    )
    assert host.command('stream_output')['reply'] == [value], (
        'I3/T3: exact independently supplied original metadata is retained once for continuation'
    )
    text = [event for event in accepted['stream_events'] if event.get('type') == 'text_delta']
    calls = [event for event in accepted['stream_events'] if event.get('type') == 'tool_call']
    assert len(text) == (1 if kind == 'message' else 0), (
        'I3/T3/T4: only public message snapshots publish text, and a matching duplicate is inert'
    )
    assert len(calls) == (1 if kind == 'function_call' else 0), (
        'I3/T3: only function items dispatch their independently supplied call exactly once'
    )


def test_documented_reasoning_parts_remain_opaque_and_keep_exact_completed_original(host):
    # Accident: public part handling rejects the official reasoning_text union alternative.
    host.command('stream_start')
    reasoning = original('reasoning')
    events = [item_event(original('reasoning', done=False), done=False)]
    for marker, text in [('added', ''), ('done', 'NONPUBLIC-Å')]:
        events.append({
            'type': 'response.content_part.' + marker,
            'item_id': reasoning['id'],
            'output_index': 0,
            'content_index': 0,
            'sequence_number': len(events),
            'part': {'type': 'reasoning_text', 'text': text},
        })
    public = original('message', 'public-B')
    accepted = wire(
        host,
        [*events, item_event(reasoning), item_event(public, 1), complete([reasoning, public])],
        fragmented=True,
    )
    assert accepted['reply']['ok'] and host.command('stream_finish')['reply']['ok'], (
        'I3/T4: official reasoning part added/done and enclosing opaque completion remain valid'
    )
    assert host.command('stream_output')['reply'] == [reasoning, public], (
        'I3/T4: exact opaque content and encrypted continuation survive beside the public item'
    )
    assert ''.join(event.get('text', '') for event in accepted['stream_events']) == 'PUBLIC-Å', (
        'I3/T4: opaque reasoning never becomes public text while ordinary public output survives'
    )
