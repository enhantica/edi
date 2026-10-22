"""T1: existing-question Stop uses the existing local exception-regression host.

No new observer or fault mechanism: successful public terminal milestones qualify
the same one-shot core-only regression control used by interruption_atomicity.
"""

from __future__ import annotations

import importlib.util
import os
from pathlib import Path

import pytest

_spec = importlib.util.spec_from_file_location(
    'stop_regression', Path(__file__).with_name('test_e11_t5_interruption_atomicity.py')
)
regression = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(regression)
protocol, questions = regression.protocol, regression.questions


def held_question():
    binary = Path(
        os.environ.get(
            'EDI_ASSISTANT_INTERRUPTION_PROBE',
            protocol.ROOT / 'build/assistant-core-tests/assistant_interruption_probe',
        )
    )
    assert binary.is_file(), 'I3/T1: the existing local regression host links the real controller'
    actor = protocol.Host(binary, reply_timeout=5)
    actor.start()
    questions.ask(actor)
    return actor


def stop(actor, ordinal=0, *, length=False):
    return actor.command(
        'fault_user', payload=protocol.envelope('cancel'), ordinal=ordinal, length=length
    )


def terminal_rows(result):
    return [
        event
        for event in result['events']
        if event.get('type') == 'tool_result'
        and event.get('call_id') == 'question-call'
        and not event.get('pending')
    ]


def test_ordinary_stop_settles_exactly_one_existing_question_without_continuation():
    actor = held_question()
    try:
        original = actor.last['snapshot']
        requests = len(actor.last['requests'])
        result = stop(actor)
        assert result['reply']['ok'], 'I3/T1: ordinary trusted Stop has a successful local control'
        rows = terminal_rows(result)
        assert len(rows) == 1 and rows[0].get('ok') is False, (
            'I3/T1: ordinary Stop publishes one correlated interrupted question outcome'
        )
        assert (
            not result['state']['pending_question_id'] and not result['state']['active_turn_id']
        ), 'I3/I10/T1: ordinary Stop retires the actual question and request authority'
        assert len(result['requests']) == requests and result['snapshot'] == original, (
            'I3/I4/T1: cancelling a question performs no provider continuation or project edit'
        )
    finally:
        actor.close()


@pytest.mark.parametrize('exception', ['bad_alloc', 'length_error'])
@pytest.mark.parametrize('stage', ['preparation', 'publication'])
def test_question_stop_publication_failure_has_typed_outcome_and_settlement_or_recovery(
    exception, stage
):
    # Accident: Stop clears the live question, swallows settlement failure, then reports success.
    positive = held_question()
    try:
        control = stop(positive)
        assert control['reply']['ok'] and len(terminal_rows(control)) == 1, (
            'I3/T1: the existing successful Stop reaches its actual correlated terminal'
        )
        milestones = control['allocation_fault']['milestones']
        terminal = next(row for row in milestones if row['type'] == 'tool_result')
        measured = int(terminal['allocation_count'])
        assert measured > 1, 'I3/T1: actual Stop terminal preparation has observable core work'
        ordinal = measured if stage == 'publication' else max(1, measured // 2)
    finally:
        positive.close()
    actor = held_question()
    try:
        original = actor.last['snapshot']
        requests = len(actor.last['requests'])
        failed = stop(actor, ordinal, length=exception == 'length_error')
        assert failed['allocation_fault']['fired'], (
            'I3/T1: the already-existing one-shot local regression control is actually reached'
        )
        assert (
            not failed['reply']['ok']
            and failed['reply']['code'] == 'edi.assistant.resource_exhausted'
        ), 'I3/T1: failed question settlement cannot be swallowed as a normal Stop acknowledgement'
        assert (
            not failed['state']['active_turn_id'] and not failed['state']['pending_question_id']
        ), 'I3/I10/T1: failed settlement still immediately retires request and human authority'
        assert len(failed['requests']) == requests and failed['snapshot'] == original, (
            'I3/I4/T1: interrupted Stop starts no continuation and preserves captured live state'
        )
        rows = terminal_rows(failed)
        if rows:
            assert len(rows) == 1 and rows[0].get('ok') is False, (
                'I3/T1: recoverable Stop keeps exactly one correlated failure outcome'
            )
        else:
            retry = actor.user(
                'message',
                text='Continue only after the interrupted question is recoverable',
                connection_id='connection-A',
                model=protocol.MODEL,
                effort='high',
            )
            if retry['reply']['ok']:
                outcomes = [
                    row
                    for row in retry['requests'][-1]['history']
                    if row.get('type') == 'tool_result' and row.get('call_id') == 'question-call'
                ]
                assert (
                    outcomes
                    and not outcomes[-1].get('pending')
                    and outcomes[-1].get('ok') is False
                ), (
                    'I3/T1: resumed conversation contains a complete question failure, '
                    'never an orphan hold'
                )
            else:
                assert len(retry['requests']) == requests, (
                    'I3/T1: unavailable question recovery refuses before any new provider request'
                )
    finally:
        actor.close()
