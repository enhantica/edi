"""Literal e0a1a7799 host lease, using real Controller/Worker/science and human holds.

This host is a retaining role over the public hook. It does not claim the actual VM
installs the hook or prove the real QML archive's full byte/count reservation.
"""

from __future__ import annotations

import importlib.util
import os
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]


def module(name, path):
    spec = importlib.util.spec_from_file_location(name, ROOT / path)
    loaded = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(loaded)
    return loaded


protocol = module('retention_protocol', 'tests/integration/py/test_e11_t5_assistant_protocol.py')
trials = module('retention_trials', 'tests/system/py/test_e11_t5_assistant_trials.py')
questions = module('retention_questions', 'tests/system/py/test_e11_t5_assistant_questions.py')


@pytest.fixture
def role(request, monkeypatch):
    monkeypatch.setenv('EDI_TEST_RETENTION_MODE', request.param)
    binary = Path(
        os.environ.get(
            'EDI_ASSISTANT_RETENTION_PROBE',
            ROOT / 'build/assistant-core-tests/assistant_terminal_retention_probe',
        )
    )
    assert binary.is_file(), (
        'I10/S6: the literal accepted TerminalRetention interface links a separate real-core host'
    )
    actor = protocol.Host(binary, reply_timeout=5)
    actor.retention_mode = request.param
    try:
        yield actor
    finally:
        actor.close()


def prepare(actor, operation):
    if operation == 'question':
        questions.start(actor)
        return lambda: actor.tool('ask_question', questions.arguments(), call_id='retained-call')
    paths = trials.load_source(actor, baseline=False)
    plan = trials.approve(actor, paths, iterations=80)
    begun = actor.tool('begin_trial', {'group_id': 'workflow'}, plan_id=plan)
    assert begun['reply']['ok'], 'I8/S6: retention admission follows a real isolated candidate'
    trial = begun['reply']['value']['trial_id']
    changed = actor.tool(
        'set_free', {'flags': [{'path': path, 'free': True} for path in paths]}, plan_id=plan
    )
    assert changed['reply']['ok'], 'I8/S6: real legal free flags precede the lease admission door'
    return lambda: actor.tool(
        'fit_trial', {'trial_id': trial}, plan_id=plan, call_id='retained-call'
    )


def complete(actor, operation):
    if operation == 'fit':
        return trials.settle(actor)
    question = actor.last['reply']['value']['question_id']
    actor.provider('turn_finished', **actor.binding(), status='completed')
    return actor.user('answer', question_id=question, answer='inspect')


@pytest.mark.parametrize('operation', ['fit', 'question'])
@pytest.mark.parametrize('role', ['null', 'throw'], indirect=True)
def test_retaining_role_prestart_refusal_is_atomic_and_sanitized(role, operation):
    # Accident: producer starts/clamps a candidate or publishes a question before UI admission.
    invoke = prepare(role, operation)
    original = role.last['snapshot']
    result = invoke()
    protocol.refused(result, 'resource_exhausted')
    observed = result['retention']
    assert len(observed['prospective']) == 1 and observed['started'] == 0, (
        'I4/I10/S6: the reached reservation refusal occurs before any async start publication'
    )
    assert result['snapshot'] == original and observed['archive'] == [], (
        'I4/S6: failed prospective admission preserves original live state and public archive'
    )
    assert not result['state']['active_job_id'] and not result['state']['pending_question_id'], (
        'I10/S6: refused capacity does not create an optimizer or human-answer hold'
    )
    assert 'synthetic-sensitive' not in str(result), (
        'I3/S6: thrown capacity dependency text never becomes public error content'
    )


@pytest.mark.parametrize('operation', ['fit', 'question'])
@pytest.mark.parametrize('role', ['accept', 'headless'], indirect=True)
def test_real_settlement_retains_exact_correlated_outcome_before_continuation(role, operation):
    invoke = prepare(role, operation)
    admitted = invoke()
    assert admitted['reply']['ok'], 'I10/S6: valid host capacity admits the actual async operation'
    settled = complete(role, operation)
    observed = settled['retention']
    assert not settled['state']['active_job_id'] and not settled['state']['pending_question_id'], (
        'I10/S6: actual fit or human settlement retires its async hold'
    )
    if role.retention_mode == 'accept':
        assert len(observed['prospective']) == 1, (
            'I10/S6: an installed accepting retaining role cannot be silently bypassed'
        )
        assert observed['started'] == 1 and observed['settled'] == 1, (
            'I10/S6: one real accepted call starts and settles its unique lease once'
        )
        prospective = observed['prospective'][0]
        terminal = observed['terminals'][0]
        assert set(prospective) == {'schema', 'call', 'pending_result', 'activity'}, (
            'I3/S6: prospective input is the exact approved producer-fact envelope'
        )
        assert prospective['schema'] == 'edi.assistant.terminal-retention/1', (
            'I3/S6: the retained role receives the declared exact interface schema'
        )
        assert prospective['pending_result']['pending'] is True and terminal['pending'] is False, (
            'I3/S6: pending receipt cannot substitute for complete actual settlement'
        )
        for key in ('connection_id', 'turn_id', 'request_id', 'project_id', 'revision', 'call_id'):
            assert terminal[key] == prospective['pending_result'][key], (
                'I3/S6: terminal retention preserves every original invocation correlation field'
            )
        assert terminal['call_id'] == 'retained-call' and isinstance(terminal['result'], dict), (
            'I3/S6: the real complete correlated outcome is retained as an object'
        )
        assert observed['held'] == 0 and observed['quarantined'] == 0, (
            'I10/S6: successful complete retention consumes its hold without quarantine'
        )
        assert observed['trace'].index('started') < observed['trace'].index('settle'), (
            'I10/S6: real start publication precedes actual complete settlement'
        )
    else:
        assert observed['trace'] == [], (
            'I10/S6: true headless absence needs no invented UI retaining role'
        )
    assert observed['owner_violations'] == 0, (
        'I10/S6: lease construction, methods and destruction stay on their real owner thread'
    )


@pytest.mark.parametrize('operation', ['fit', 'question'])
@pytest.mark.parametrize('role', ['started-false', 'settle-false'], indirect=True)
def test_started_failure_and_quarantine_preserve_recovery_until_explicit_teardown(role, operation):
    invoke = prepare(role, operation)
    admitted = invoke()
    assert admitted['retention']['started'] == 1, (
        'I10/S6: failure injection reaches the actual started lease method'
    )
    before_requests = len(admitted['requests'])
    if admitted['retention']['held']:
        cancelled = role.command('cancel')
        assert cancelled['retention']['held'] == 1, (
            'I10/S6: Stop cannot destroy a running or quarantined terminal allowance'
        )
    if operation == 'fit':
        settled = trials.settle(role)
    elif role.last['state']['pending_question_id']:
        settled = role.user(
            'answer', question_id=role.last['state']['pending_question_id'], answer='inspect'
        )
    else:
        settled = role.command('inspect')
    observed = settled['retention']
    assert len(settled['requests']) == before_requests, (
        'I10/S6: unsuccessful start/retention never continues past an unretained terminal'
    )
    if role.retention_mode == 'settle-false':
        assert observed['quarantined'] == 1 and observed['held'] == 1, (
            'I10/S6: failed complete retention quarantines exactly once without spending its hold'
        )
    assert observed['settled'] or observed['quarantined'], (
        'I10/S6: admitted failure reaches complete actual settlement or explicit quarantine'
    )
    detached = role.command('detach')
    assert detached['retention']['held'] == 0 and detached['retention']['destroyed'] == 1, (
        'I10/S6: explicit project-owner teardown releases exactly its remaining unique lease'
    )
    assert detached['retention']['owner_violations'] == 0, (
        'I10/S6: recovery and teardown never invoke a lease on a dead or foreign owner'
    )
