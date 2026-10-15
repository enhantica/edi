"""Completed originals versus compact final summaries: accepted packet710585daf.

Reachable accident: a normal completed text/reasoning original is absent from the
explicit final array, or its omission shifts the array offset of a known call.
Original fixtures use the published Responses streaming item schema (see the
existing content-lifecycle reference). Authority comes from review50/S-R2, never
the SDK accumulator or the decoder's own output. Core tool events are normalized
observations, not evidence of physical tool execution in the native adapter.
"""

from __future__ import annotations

import copy
import importlib.util
from pathlib import Path

import pytest

_spec = importlib.util.spec_from_file_location(
    'authority_membership', Path(__file__).with_name('test_e11_t5_stream_membership.py')
)
membership = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(membership)
host = membership.host
wire = membership.wire
original = membership.original
item_event = membership.item_event
complete = membership.complete


def completed(result):
    return [
        event
        for event in result['stream_events']
        if event.get('type') == 'turn_finished' and event.get('status') == 'completed'
    ]


@pytest.mark.parametrize('kind', ['message', 'reasoning'])
def test_explicit_empty_summary_preserves_exact_completed_nonexecuting_original(host, kind):
    host.command('stream_start')
    value = original(kind, 'original-opaque-Å')
    prefix = wire(host, [item_event(value), item_event(value)])
    assert prefix['reply']['ok'], 'S-R2: an immutable duplicate of a genuine done original admits'
    accepted = wire(host, [complete([])])
    assert accepted['reply']['ok'] and host.command('stream_finish')['reply']['ok'], (
        'S-R2: genuine completed response with an explicit empty summary may omit only '
        'completed nonexecuting originals'
    )
    assert host.command('stream_output')['reply'] == [value], (
        'S-R2: replay preserves the independently supplied original once, with exact opaque '
        'content, status and identity'
    )
    assert len(completed(accepted)) == 1, 'S-R2: a coherent successful exchange settles once'
    assert not any(e.get('type') == 'tool_call' for e in accepted['stream_events']), (
        'S-R2: message/reasoning originals create no normalized executable call'
    )


@pytest.mark.parametrize('summary', ['call-only', 'reasoning-and-call', 'all'])
def test_compact_summary_maps_known_ids_to_original_positions_without_rebinding(host, summary):
    host.command('stream_start')
    values = [
        original(kind, 'original-' + str(index))
        for index, kind in enumerate(['message', 'reasoning', 'function_call'])
    ]
    prefix = wire(host, [item_event(value, index) for index, value in enumerate(values)])
    assert prefix['reply']['ok'], 'S-R2: original positions are independently fixed before summary'
    selected = {'call-only': values[2:], 'reasoning-and-call': values[1:], 'all': values}[summary]
    accepted = wire(host, [complete(selected)])
    assert accepted['reply']['ok'] and host.command('stream_finish')['reply']['ok'], (
        'S-R2: compact final array offsets cannot rebind known identities to predecessor slots'
    )
    assert host.command('stream_output')['reply'] == values, (
        'S-R2: exact original positional order survives compact final membership'
    )
    calls = [e for e in accepted['stream_events'] if e.get('type') == 'tool_call']
    assert len(calls) == 1 and calls[0]['call_id'] == values[2]['call_id'], (
        'S-R2: the one completed final-member call retains its planted correlation exactly once'
    )


@pytest.mark.parametrize('shape', ['missing', 'null', 'object', 'string', 'number'])
def test_required_terminal_output_is_not_synthesized_from_retained_originals(host, shape):
    host.command('stream_start')
    prefix = wire(host, [item_event(original('message'))])
    assert prefix['reply']['ok'], 'S-R2: a genuine completed original precedes malformed summary'
    terminal = complete([])
    if shape == 'missing':
        del terminal['response']['output']
    else:
        shapes = {'null': None, 'object': {}, 'string': '', 'number': 0}
        terminal['response']['output'] = shapes[shape]
    refused = wire(host, [terminal])
    assert not refused['reply']['ok'] and not completed(refused), (
        'S-R2: only an explicit actual final array can authorize retained-original completion'
    )
    assert not host.command('stream_finish')['reply']['ok'], (
        'S-R2: EOF cannot repair a missing or wrongly typed required final array'
    )


@pytest.mark.parametrize('kind', ['message', 'reasoning'])
@pytest.mark.parametrize('prior', ['added-only', 'in-progress-done', 'incomplete-done'])
def test_omission_never_promotes_wire_or_semantically_unfinished_originals(host, kind, prior):
    host.command('stream_start')
    value = original(kind)
    if prior != 'added-only':
        value['status'] = 'in_progress' if prior == 'in-progress-done' else 'incomplete'
    prefix = wire(host, [item_event(value, done=prior != 'added-only')])
    refused = wire(host, [complete([])]) if prefix['reply']['ok'] else prefix
    assert not refused['reply']['ok'] and not completed(refused), (
        'S-R2: omission requires both genuine item.done and completed semantic original status'
    )
    assert not host.command('stream_finish')['reply']['ok'], (
        'S-R2: a partial original cannot become a successful exchange at EOF'
    )


@pytest.mark.parametrize('ending', ['eof', 'done-marker', 'failed', 'incomplete'])
def test_nonexecuting_original_still_requires_genuine_successful_response(host, ending):
    host.command('stream_start')
    prefix = wire(host, [item_event(original('reasoning'))])
    assert prefix['reply']['ok'], 'S-R2: completed opaque original precedes response-status checks'
    result = prefix
    if ending == 'done-marker':
        result = host.command('stream_feed', bytes=list(b'data: [DONE]\n\n'))
    elif ending != 'eof':
        result = wire(
            host,
            [
                {
                    'type': 'response.' + ending,
                    'response': {'id': 'independent-response', 'status': ending, 'output': []},
                }
            ],
        )
    assert not completed(result), (
        'S-R2: EOF/DONE/failed/incomplete never substitute for genuine completed response'
    )
    finished = host.command('stream_finish')['reply']
    if ending in {'failed', 'incomplete'}:
        # Packet727-730 and the existing D3 contract distinguish successful decoding
        # of a valid non-success terminal from a successful inference. Review79
        # adjudicates this boolean; the original EOF/DONE refusal stays strict.
        terminals = [e for e in result['stream_events'] if e.get('type') == 'turn_finished']
        assert len(terminals) == 1 and terminals[0]['status'] != 'completed', (
            'S-R2: a genuine failed/incomplete response publishes exactly one non-success terminal'
        )
        assert not any(e.get('type') == 'tool_call' for e in result['stream_events']), (
            'S-R2: decoding a failed/incomplete terminal cannot authorize executable work'
        )
        assert host.command('stream_output')['reply'] == [], (
            'S-R2: failed/incomplete exchanges contribute no completed originals to clean replay'
        )
        assert finished['ok'], (
            'S-R2/D3: a valid non-success terminal may settle decoding without inference success'
        )
    else:
        assert not finished['ok'], (
            'S-R2: EOF/DONE without a valid semantic terminal refuses finish'
        )


@pytest.mark.parametrize(
    'fault',
    [
        'omitted',
        'incomplete',
        'failed',
        'changed-call-id',
        'changed-arguments',
        'changed-content',
        'replacement',
    ],
)
def test_function_authority_and_immutable_originals_remain_strict(host, fault):
    host.command('stream_start')
    value = original('message' if fault == 'changed-content' else 'function_call')
    if fault in {'incomplete', 'failed'}:
        value['status'] = fault
    prefix = wire(host, [item_event(value)])
    final = copy.deepcopy(value)
    if fault == 'changed-call-id':
        final['call_id'] = 'different-call'
    elif fault == 'changed-arguments':
        final['arguments'] = '{"different":true}'
    elif fault == 'changed-content':
        final['content'][0]['text'] = 'CHANGED-PUBLIC'
    elif fault == 'replacement':
        final = original('function_call', 'replacement-at-held-position')
    refused = (
        wire(host, [complete([] if fault == 'omitted' else [final])])
        if prefix['reply']['ok']
        else prefix
    )
    assert not refused['reply']['ok'] and not completed(refused), (
        'S-R2: omitted/partial/failed calls and explicit identity/content contradictions '
        'cannot authorize successful continuation'
    )
    assert not host.command('stream_finish')['reply']['ok'], (
        'S-R2: terminal rejection remains failed after EOF; no repaired or unioned authority'
    )
