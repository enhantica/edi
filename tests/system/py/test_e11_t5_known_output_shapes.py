"""O1: validate known completed originals before replay/group authority.

Accident: newly allowed nonexecuting omissions bypass required known output shapes,
then poison replay or authorize a valid companion call. Official Responses output
union at openai-node85e528a and review79 provide required/optional field facts.
Unknown metadata remains opaque; this is not a universal provider-schema engine.
"""

from __future__ import annotations

import copy
import importlib.util
from pathlib import Path

import pytest


def load(name, filename):
    spec = importlib.util.spec_from_file_location(name, Path(__file__).with_name(filename))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


originals = load('shape_originals', 'test_e11_t5_stream_membership.py')
bridge = load('shape_native', 'test_e11_t5_native_completion_authority.py')
host = originals.host
native = bridge.native
signer = bridge.signer
FAULTS = [
    'message-role-missing',
    'message-role-user',
    'reasoning-summary-missing',
    'reasoning-summary-object',
    'reasoning-summary-entry',
    'reasoning-encrypted-object',
    'text-annotations-missing',
    'text-annotations-object',
    'refusal-missing',
    'refusal-nonstring',
]


def malformed(fault):
    kind = 'reasoning' if fault.startswith('reasoning-') else 'message'
    value = originals.original(kind, 'known-original-' + fault)
    if kind == 'reasoning':
        del value['status']  # Independently optional in the official output union.
    if fault == 'message-role-missing':
        del value['role']
    elif fault == 'message-role-user':
        value['role'] = 'user'
    elif fault == 'reasoning-summary-missing':
        del value['summary']
    elif fault == 'reasoning-summary-object':
        value['summary'] = {}
    elif fault == 'reasoning-summary-entry':
        value['summary'] = [{'type': 'summary_text', 'text': 17}]
    elif fault == 'reasoning-encrypted-object':
        value['encrypted_content'] = {'untrusted': 'not a nullable opaque string'}
    elif fault == 'text-annotations-missing':
        del value['content'][0]['annotations']
    elif fault == 'text-annotations-object':
        value['content'][0]['annotations'] = {}
    elif fault.startswith('refusal-'):
        value['content'] = [{'type': 'refusal'}]
        if fault == 'refusal-nonstring':
            value['content'][0]['refusal'] = 17
    return value


def events(value, delivery, *, offset=0):
    if delivery == 'terminal-only':
        return []
    done = originals.item_event(value, offset)
    if delivery == 'done-original':
        return [done]
    added = copy.deepcopy(value)
    added['status'] = 'in_progress'
    if added['type'] == 'message':
        added['content'] = []
    return [originals.item_event(added, offset, done=False), done]


@pytest.mark.parametrize('fault', FAULTS)
@pytest.mark.parametrize('delivery', ['done-original', 'live-added-done', 'terminal-only'])
def test_known_malformed_original_cannot_qualify_completed_replay_or_omission(
    host, fault, delivery
):
    host.command('stream_start')
    value = malformed(fault)
    prefix = events(value, delivery)
    terminal = originals.complete([value] if delivery == 'terminal-only' else [])
    rejected = originals.wire(host, [*prefix, terminal])
    assert not rejected['reply']['ok'], (
        'O1: known required role/part/summary/opaque-field types must validate before '
        'a completed original qualifies for successful final snapshot or omission'
    )
    assert not any(
        e.get('type') == 'tool_call'
        or (e.get('type') == 'turn_finished' and e.get('status') == 'completed')
        for e in rejected['stream_events']
    ), 'O1: malformed known nonexecuting originals cannot authorize completed group work'
    assert not host.command('stream_finish')['reply']['ok'], (
        'O1: rejected known-shape authority remains failed after physical input ends'
    )


@pytest.mark.parametrize('kind', ['message', 'reasoning'])
@pytest.mark.parametrize('delivery', ['done-original', 'live-added-done', 'terminal-only'])
def test_valid_known_original_preserves_optional_presence_and_unknown_opaque_metadata(
    host, kind, delivery
):
    host.command('stream_start')
    value = originals.original(kind, 'valid-known-' + kind)
    value['independent_extension'] = {'opaque': ['literal original metadata', 17]}
    if kind == 'reasoning':
        del value['status']
        value['encrypted_content'] = None
        value['summary'] = [{'type': 'summary_text', 'text': 'Opaque original summary'}]
    accepted = originals.wire(host, [*events(value, delivery), originals.complete([value])])
    assert accepted['reply']['ok'] and host.command('stream_finish')['reply']['ok'], (
        'O1: known-shape validation retains legal optional status/nullable encrypted content '
        'and does not reject uninterpreted provider extension metadata'
    )
    assert host.command('stream_output')['reply'] == [value], (
        'O1: exact original metadata and optional member presence survive once without synthesis'
    )


@pytest.mark.parametrize('fault', ['message-role-user', 'reasoning-summary-object'])
@pytest.mark.parametrize('delivery', ['done-original', 'live-added-done', 'terminal-only'])
def test_later_malformed_known_original_blocks_native_release_of_valid_companion_call(
    native, signer, fault, delivery
):
    native.authenticate(signer)
    index, request = bridge.services.start_inference(native, tools=bridge.TOOLS)
    call = originals.original('function_call', 'earlier-valid-shape-control')
    later = malformed(fault)
    incoming = [
        originals.item_event(call),
        *events(later, delivery, offset=1),
        originals.complete([call, later]),
    ]
    bridge.feed(native, index, incoming)
    settled = native.command('finish', index=index, failure=0)
    assert not bridge.bound(settled, request, 'tool_call'), (
        'O1: native physical finish cannot release an earlier valid call from a group '
        'containing a later malformed known message/reasoning original'
    )
    terminals = bridge.bound(settled, request, 'turn_finished')
    assert terminals and all(e['status'] != 'completed' for e in terminals), (
        'O1: malformed companion rejection remains one visible non-success native boundary'
    )
