"""Reachable review-16 transitions on the real public core and Responses parser."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


protocol = load(
    'e11_transition_protocol', ROOT / 'tests/integration/py/test_e11_t5_assistant_protocol.py'
)
boundaries = load(
    'e11_transition_bounds', Path(__file__).with_name('test_e11_t5_assistant_boundaries.py')
)
questions = load(
    'e11_transition_questions', Path(__file__).with_name('test_e11_t5_assistant_questions.py')
)
host = protocol.host


def compact(value):
    return json.dumps(value, ensure_ascii=False, separators=(',', ':'))


@pytest.mark.parametrize('channel', ['output_text', 'refusal'])
@pytest.mark.parametrize('kind', ['completed-message', 'function-call'])
def test_completed_or_wrong_kind_item_cannot_receive_public_text_delta(host, channel, kind):
    # Accident: an item is already immutable, but a later delta bypasses that item's state.
    host.command('stream_start')
    item = {
        'id': 'immutable-item',
        'type': 'message',
        'role': 'assistant',
        'status': 'completed',
        'content': [{'type': 'output_text', 'text': 'ORIGINAL-Å'}],
    }
    if kind == 'function-call':
        item = {
            'id': 'immutable-item',
            'type': 'function_call',
            'call_id': 'call-one',
            'name': 'inspect_project',
            'arguments': '{}',
            'status': 'completed',
        }
    before = boundaries.chunks(
        host, [{'type': 'response.output_item.done', 'output_index': 0, 'item': item}]
    )
    assert before['reply']['last']['ok'], (
        'I3/S10: the independent completed item is admitted first'
    )
    emitted = before['stream_events']
    after = boundaries.chunks(
        host,
        [
            {
                'type': 'response.' + channel + '.delta',
                'item_id': item['id'],
                'output_index': 0,
                'content_index': 0,
                'delta': 'FORBIDDEN-LATE',
            }
        ],
    )
    assert not after['reply']['last']['ok'], (
        'I3/S10: completed or non-message items reject public text/refusal mutation'
    )
    assert after['stream_events'] == emitted, (
        'I3/S10: refused late text changes no emitted public outcome'
    )


def test_live_message_fragmentation_remains_usable_before_item_completion(host):
    host.command('stream_start')
    before = boundaries.chunks(
        host,
        [
            {
                'type': 'response.output_item.added',
                'output_index': 0,
                'item': {
                    'id': 'live-item',
                    'type': 'message',
                    'role': 'assistant',
                    'status': 'in_progress',
                    'content': [],
                },
            }
        ],
    )
    assert before['reply']['last']['ok'], (
        'I3/S10: a live message control precedes fragment admission'
    )
    result = boundaries.chunks(
        host,
        [
            {
                'type': 'response.output_text.delta',
                'item_id': 'live-item',
                'output_index': 0,
                'content_index': 0,
                'delta': text,
            }
            for text in ['Å', 'ngström 🧪']
        ],
    )
    assert result['reply']['last']['ok'], 'I3/S10: ordinary live message fragments remain accepted'
    assert ''.join(event.get('text', '') for event in result['stream_events']) == 'Ångström 🧪', (
        'I3/S10: live fragments retain exact non-ASCII public text'
    )


@pytest.mark.parametrize('hold', ['plan', 'question'])
def test_bound_output_exhaustion_revokes_existing_execution_scope(host, hold):
    # Accident: quota refusal returns a code while leaving an approved plan/human hold executable.
    host.start()
    original = host.last['snapshot']
    if hold == 'plan':
        plan = host.approve()
    else:
        questions.ask(host)
        plan = None
    binding = host.binding()
    result = host.command(
        'provider_repeat',
        count=34,
        payload=protocol.envelope('text_delta', **binding, text='x' * 65536),
    )
    boundaries.resource(result['reply']['last'])
    assert not result['state']['active_turn_id'] and not result['state']['pending_question_id'], (
        'I3/I10/S1: bound quota exhaustion retires the active turn and human hold'
    )
    assert not result['state']['can_cancel'], (
        'I10/S1: a refused bound stream cannot remain apparently running'
    )
    assert result['snapshot'] == original, (
        'I4/S1: stream exhaustion preserves the captured scientific project'
    )
    if plan:
        denied = host.tool(
            'set_parameters',
            {'values': [{'path': 'structure.cell.length_a', 'value': 4.61}]},
            plan_id=plan,
        )
        assert not denied['reply']['ok'] and denied['snapshot'] == original, (
            'I2/I4/S1: an exhausted stream cannot spend its old approval on a later live edit'
        )


def test_failed_new_human_history_admission_is_transactional(host):
    # Accident: a human row/turn is committed before its final history/request preflight fails.
    host.start()
    binding = host.binding()
    result = host.command(
        'provider_repeat',
        count=7,
        payload=protocol.envelope('text_delta', **binding, text='x' * 262144),
    )
    assert result['reply']['accepted'] == 7, (
        'I3/S2: independently bounded prior conversation fits before new-user pressure'
    )
    host.provider('turn_finished', **binding, status='completed')
    original = host.last['snapshot']
    failed = host.user(
        'message',
        text='FAILED-USER-' + 'y' * 400000,
        connection_id='connection-A',
        model=protocol.MODEL,
    )
    boundaries.resource(failed['reply'])
    assert not failed['state']['active_turn_id'], (
        'I3/S2: rejected new-user admission leaves no phantom active turn'
    )
    next_turn = host.user(
        'message', text='VALID-NEXT-USER', connection_id='connection-A', model=protocol.MODEL
    )
    assert next_turn['reply']['ok'], (
        'I3/S2: an independent valid message remains usable after transactional refusal'
    )
    history = compact(next_turn['requests'][-1]['history'])
    assert 'FAILED-USER-' not in history and 'VALID-NEXT-USER' in history, (
        'I3/S2: a refused user message never enters later outgoing conversation'
    )
    assert next_turn['snapshot'] == original, (
        'I4/S2: new-user quota failure writes no scientific state'
    )


@pytest.mark.parametrize('transition', ['different-account', 'same-account-reconnect'])
def test_connection_scope_replacement_does_not_forward_old_conversation(host, transition):
    # Accident: connection stop clears active IDs but leaves old-account text/tool receipts live.
    host.start()
    host.tool('inspect_project', call_id='OLD-ACCOUNT-CALL')
    host.provider('turn_finished', **host.binding(), status='completed')
    old = host.binding()
    if transition == 'same-account-reconnect':
        host.provider(
            'connection', connection_id='connection-A', status='disconnected', capabilities=[]
        )
        connection = 'connection-A'
    else:
        connection = 'connection-B'
    host.provider(
        'connection',
        connection_id=connection,
        status='ready',
        capabilities=[
            {
                'id': protocol.MODEL,
                'display_name': 'New account',
                'efforts': ['high'],
                'attachment_types': [],
            }
        ],
    )
    sent = host.user(
        'message', text='NEW-ACCOUNT-ONLY', connection_id=connection, model=protocol.MODEL
    )
    assert sent['reply']['ok'], (
        'I3/I13/S3: a valid replacement connection starts its own ordinary conversation'
    )
    history = compact(sent['requests'][-1]['history'])
    assert 'OLD-ACCOUNT-CALL' not in history and 'Inspect PbSO' not in history, (
        'I3/I12/S3: old account text and receipts never enter the replacement wire'
    )
    assert sent['requests'][-1]['turn_id'] != old['turn_id'], (
        'I3/S3: reconnect issues a fresh nonreused user turn identity'
    )


def test_duplicate_user_approval_cannot_renew_original_deadline(host):
    # Accident: repeated real approval writes plan.started again without a new displayed scope.
    host.start()
    plan = host.approve()
    before_duplicate = host.command('poll', now=4107)['snapshot']
    duplicate = host.user(
        'approve_plan',
        plan_id=plan,
        project_id='project-A',
        revision=host.last['state']['revision'],
    )
    assert duplicate['snapshot'] == before_duplicate, (
        'I4/S4: repeated approval itself writes no scientific project data'
    )
    host.command('poll', now=5108)
    original = host.last['snapshot']
    edited = host.tool(
        'set_parameters',
        {'values': [{'path': 'structure.cell.length_a', 'value': 4.61}]},
        plan_id=plan,
    )
    assert not edited['reply']['ok'], (
        'I2/I10/S4: duplicate approval cannot extend the original inclusive elapsed budget'
    )
    assert edited['snapshot'] == original, (
        'I4/S4: renewed-approval escape cannot publish a late edit'
    )


@pytest.mark.parametrize('efforts', [[], ['high']])
def test_unknown_core_capability_cannot_gain_default_or_explicit_effort_authority(host, efforts):
    host.command('attach', id='project-A')
    connected = host.provider(
        'connection',
        connection_id='unknown-account',
        status='ready',
        capabilities=[
            {
                'id': 'unknown-independent-model',
                'display_name': 'Unknown',
                'efforts': efforts,
                'attachment_types': [],
            }
        ],
    )
    before = len(connected['requests'])
    sent = host.user(
        'message',
        text='Do not guess model capability',
        connection_id='unknown-account',
        model='unknown-independent-model',
        **({'effort': 'high'} if efforts else {}),
    )
    assert not sent['reply']['ok'] and len(sent['requests']) == before, (
        'I15/S9: default and explicit effort both require mapping and account membership'
    )
