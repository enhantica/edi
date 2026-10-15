"""Independent human-hold protocol from the accepted question contract at relay 9f635ee09."""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
_spec = importlib.util.spec_from_file_location(
    'e11_t5_question_protocol', ROOT / 'tests/integration/py/test_e11_t5_assistant_protocol.py'
)
protocol = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(protocol)
host = protocol.host


def arguments(**patch):
    return {
        'text': 'Choose the next public check — Ångström 🧪',
        'options': [
            {'id': 'inspect', 'label': 'Inspect', 'description': 'Read current state'},
            {'id': 'wait', 'label': 'Wait', 'description': 'Leave current state unchanged'},
        ],
        'recommended': 'inspect',
        'allow_free_text': True,
        **patch,
    }


def start(host):
    host.start()
    assert any(tool['name'] == 'ask_question' for tool in host.last['requests'][-1]['tools']), (
        'I3/I13: the real request manifest declares the implemented human-question boundary'
    )


def ask(host, **patch):
    result = host.tool('ask_question', arguments(**patch), call_id='question-call')
    assert result['reply']['ok'], (
        'I3/I13: a valid explicit question enters a real nonmutating human hold'
    )
    question = result['reply']['value']['question_id']
    assert (
        result['reply']['value']['pending'] is True
        and result['state']['pending_question_id'] == question
    ), 'I3: the pending acknowledgement and state identify the same fresh question'
    assert result['state']['state'] == 'awaiting_answer', (
        'I3/I13: human input holds the real user turn instead of completing a function output'
    )
    return question


def test_question_terminal_waits_for_human_answer_and_continues_once_with_full_outcome(host):
    start(host)
    original = host.last['snapshot']
    binding = host.binding()
    question = ask(host)
    count = len(host.last['requests'])
    host.provider('turn_finished', **binding, status='completed')
    assert len(host.last['requests']) == count, (
        'I3/I13: provider completion does not bypass the live human-answer hold'
    )
    answered = host.user('answer', question_id=question, answer='inspect')
    assert answered['reply']['ok'] and not answered['state']['pending_question_id'], (
        'I3: the real trusted answer settles exactly its pending question'
    )
    assert len(answered['requests']) == count + 1, (
        'I3/I13: one complete answer resumes the same turn once with a fresh request'
    )
    request = answered['requests'][-1]
    assert (
        request['turn_id'] == binding['turn_id'] and request['request_id'] != binding['request_id']
    ), 'I3: human continuation preserves turn identity while replacing the settled response scope'
    outcomes = [
        row
        for row in request['history']
        if row.get('type') == 'tool_result' and row.get('call_id') == 'question-call'
    ]
    assert outcomes and outcomes[-1]['result'] == {
        'question_id': question,
        'answer': 'inspect',
        'selected_option_id': 'inspect',
    }, (
        'I3/I13: provider continuation contains the full correlated human '
        'outcome rather than its pending acknowledgement'
    )
    assert answered['snapshot'] == original, (
        'I2/I4: supplying an answer grants no project mutation or approval'
    )
    replay = host.user('answer', question_id=question, answer='inspect')
    assert replay['reply'] == answered['reply'] and len(replay['requests']) == count + 1, (
        'I3: an identical human-answer replay returns the cached receipt without continuing twice'
    )
    conflict = host.user('answer', question_id=question, answer='wait')
    protocol.refused(conflict, 'invalid_argument')


@pytest.mark.parametrize(
    'patch',
    [
        {
            'options': [{'id': 'only', 'label': 'Only', 'description': 'One'}],
            'recommended': 'only',
        },
        {'recommended': 'foreign'},
        {'recommended': 1},
        {'allow_free_text': 1},
        {'text': '   '},
        {'options': [], 'recommended': None, 'allow_free_text': False},
        {
            'options': [
                {'id': 'bad-id', 'label': 'One', 'description': 'One'},
                {'id': 'two', 'label': 'Two', 'description': 'Two'},
            ],
            'recommended': 'two',
        },
        {
            'options': [
                {'id': 'same', 'label': 'One', 'description': 'One'},
                {'id': 'same', 'label': 'Two', 'description': 'Two'},
            ],
            'recommended': 'same',
        },
        {'unexpected': True},
    ],
    ids=[
        'one-option',
        'foreign-recommendation',
        'numeric-recommendation',
        'numeric-boolean',
        'blank-text',
        'unanswerable',
        'invalid-id',
        'duplicate-id',
        'unknown-field',
    ],
)
def test_invalid_question_shapes_refuse_atomically_before_display_or_authority(host, patch):
    start(host)
    before = host.last
    result = host.tool('ask_question', arguments(**patch))
    protocol.refused(result, 'invalid_argument', before)
    assert not result['state']['pending_question_id'], (
        'I3: invalid question arguments expose no partially admitted human hold'
    )


@pytest.mark.parametrize(
    ('text', 'accepted'),
    [('x' * 4096, True), ('é' * 2048, True), ('x' * 4097, False), ('é' * 2049, False)],
    ids=['ascii-at', 'unicode-at', 'ascii-over', 'unicode-over'],
)
def test_question_text_limit_counts_decoded_utf8_bytes(host, text, accepted):
    start(host)
    before = host.last['snapshot']
    result = host.tool('ask_question', arguments(text=text))
    assert result['reply']['ok'] is accepted, (
        'I3: question text uses the declared inclusive decoded UTF-8 byte bound'
    )
    assert result['snapshot'] == before, (
        'I2/I4: question admission or size refusal changes no scientific state'
    )


@pytest.mark.parametrize(
    'ending', ['cancel', 'manual-edit', 'connection-expiry', 'project-rebind']
)
def test_human_answer_cannot_resume_a_retired_project_or_connection_scope(host, ending):
    start(host)
    question = ask(host)
    if ending == 'cancel':
        host.command('cancel')
    elif ending == 'manual-edit':
        host.command('external', path='structure.cell.length_a', value=4.83, notify=True)
    elif ending == 'project-rebind':
        host.command('attach', id='replacement-project')
    else:
        host.provider(
            'connection', connection_id='connection-A', status='expired', capabilities=[]
        )
    protected = host.last['snapshot']
    count = len(host.last['requests'])
    answer = host.user('answer', question_id=question, answer='inspect')
    protocol.refused(answer, 'invalid_argument')
    assert not answer['state']['pending_question_id'] and len(answer['requests']) == count, (
        'I3/I7/I10: stale human input cannot recreate a retired hold or dispatch continuation'
    )
    assert answer['snapshot'] == protected, (
        'I7/I10: retired answers preserve complete accepted or manual state'
    )


def test_pending_question_rejects_other_tool_dispatch_and_provider_answer_authority(host):
    start(host)
    question = ask(host)
    before = host.last['snapshot']
    busy = host.tool('diagnostics')
    protocol.refused(busy, 'busy')
    forged = host.provider('answer', **host.binding(), question_id=question, answer='inspect')
    assert not forged['reply']['ok'] and forged['state']['pending_question_id'] == question, (
        'I2/I3: provider traffic cannot answer a human hold or bypass its trusted UI boundary'
    )
    assert forged['snapshot'] == before, (
        'I2/I4: held-work/provider-answer refusals change no accepted state'
    )


def test_question_without_a_project_is_nonmutating_and_attachment_retires_it(host):
    host.command('detach')
    host.connect()
    result = host.user(
        'message',
        text='Ask me about the workflow',
        connection_id='connection-A',
        model=protocol.MODEL,
        effort='high',
    )
    assert result['reply']['ok'], 'I13: the real assistant can converse without an open project'
    question = ask(host, options=[], recommended=None, allow_free_text=True)
    host.command('attach', id='project-A')
    result = host.user('answer', question_id=question, answer='A public answer')
    protocol.refused(result, 'invalid_argument')
    assert not result['state']['pending_question_id'], (
        'I3/I7: attaching a project cannot inherit a detached human question binding'
    )
