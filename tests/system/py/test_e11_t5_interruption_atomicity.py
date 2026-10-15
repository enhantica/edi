"""N2: fail production allocation immediately before an observed public publication.

The positive control measures allocation milestones; it supplies no scientific oracle.
Host hooks are excluded from injection, so they keep their nonthrowing contract.
"""

from __future__ import annotations

import importlib.util
import os
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]


def load(name, relative):
    spec = importlib.util.spec_from_file_location(name, ROOT / relative)
    loaded = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(loaded)
    return loaded


protocol = load('fault_protocol', 'tests/integration/py/test_e11_t5_assistant_protocol.py')
trials = load('fault_trials', 'tests/system/py/test_e11_t5_assistant_trials.py')
questions = load('fault_questions', 'tests/system/py/test_e11_t5_assistant_questions.py')


def prepare(operation):
    binary = Path(
        os.environ.get(
            'EDI_ASSISTANT_INTERRUPTION_PROBE',
            ROOT / 'build/assistant-core-tests/assistant_interruption_probe',
        )
    )
    assert binary.is_file(), 'I3/N2: the allocator witness links the actual public core'
    actor = protocol.Host(binary, reply_timeout=5)
    plan = None
    if operation == 'new-message':
        actor.command('attach', id='project-A')
        actor.connect()
        return (
            actor,
            'fault_user',
            protocol.envelope(
                'message',
                text='Independent new human input',
                connection_id='connection-A',
                model=protocol.MODEL,
                effort='high',
            ),
        )
    if operation == 'fit-start':
        paths = trials.load_source(actor, baseline=False)
        plan = trials.approve(actor, paths)
        begun = actor.tool('begin_trial', {'group_id': 'workflow'}, plan_id=plan)
        assert begun['reply']['ok'], 'I8/N2: real candidate admission precedes publication fault'
        trial = begun['reply']['value']['trial_id']
        changed = actor.tool(
            'set_free', {'flags': [{'path': path, 'free': True} for path in paths]}, plan_id=plan
        )
        assert changed['reply']['ok'], 'I8/N2: a legal native free group reaches actual fit start'
        name, arguments = 'fit_trial', {'trial_id': trial}
    else:
        actor.start()
        if operation == 'continuation':
            inspected = actor.tool('inspect_project')
            assert inspected['reply']['ok'], (
                'I3/N2: a complete real tool result precedes continuation'
            )
            return (
                actor,
                'fault_provider',
                protocol.envelope('turn_finished', **actor.binding(), status='completed'),
            )
        if operation == 'approval':
            proposed = actor.tool(
                'propose_plan',
                {
                    'summary': 'Only explicit cell values',
                    'groups': [{'id': 'cell', 'paths': ['structure.cell.length_a']}],
                    'budget': {'max_trials': 2, 'max_iterations': 8, 'max_elapsed_ms': 5000},
                    'objective': {'absolute_tolerance': 0.0, 'relative_tolerance': 0.0},
                },
            )
            assert proposed['reply']['ok'], 'I2/N2: the genuine proposal precedes trusted approval'
            plan = proposed['state']['pending_plan_id']
            actor.provider('turn_finished', **actor.binding(), status='completed')
            return (
                actor,
                'fault_user',
                protocol.envelope(
                    'approve_plan',
                    plan_id=plan,
                    project_id='project-A',
                    revision=actor.last['state']['revision'],
                ),
            )
        if operation == 'proposal':
            name, arguments = (
                'propose_plan',
                {
                    'summary': 'Only the declared group',
                    'groups': [{'id': 'cell', 'paths': ['structure.cell.length_a']}],
                    'budget': {'max_trials': 2, 'max_iterations': 8, 'max_elapsed_ms': 5000},
                    'objective': {'absolute_tolerance': 0.0, 'relative_tolerance': 0.0},
                },
            )
        elif operation == 'question':
            name, arguments = 'ask_question', questions.arguments()
        else:
            # Approved scope makes erroneous inner resource handling observable as authority.
            plan = actor.approve()
            name, arguments = 'inspect_project', {}
    payload = protocol.envelope(
        'tool_call',
        **actor.binding(),
        call_id='independent-fault-call',
        name=name,
        project_id='project-A',
        revision=actor.last['state']['revision'],
        arguments=arguments,
    )
    if plan:
        payload['plan_id'] = plan
    return actor, 'fault_provider', payload


@pytest.mark.parametrize('exception', ['bad_alloc', 'length_error'])
@pytest.mark.parametrize(
    ('operation', 'milestone'),
    [
        ('new-message', 'state_changed'),
        ('continuation', 'state_changed'),
        ('proposal', 'plan_proposed'),
        ('approval', 'plan_approved'),
        ('question', 'question'),
        ('fit-start', 'job_started'),
        ('read-result', 'tool_result'),
        ('inner-tool', 'inner-preparation'),
    ],
)
def test_one_shot_core_exhaustion_cannot_fall_through_publication_or_dispatch(
    operation, milestone, exception
):
    # Accident: safe publication catches exhaustion but its caller still commits normal work.
    positive, command, payload = prepare(operation)
    try:
        result = positive.command(command, payload=payload, ordinal=0, length=False)
        assert result['reply']['ok'], (
            'I3/N2: fault selection is qualified by the actual successful operation'
        )
        observed = result['allocation_fault']['milestones']
        selected = [
            row
            for row in observed
            if row['type'] == ('tool_result' if milestone == 'inner-preparation' else milestone)
        ]
        assert selected and selected[0]['allocation_count'] > 0, (
            'I3/N2: positive public publication has reached core allocations'
        )
        ordinal = int(selected[0]['allocation_count'])
        if milestone == 'inner-preparation':
            ordinal = max(1, ordinal // 2)
        if operation == 'fit-start':
            trials.settle(positive)
    finally:
        positive.close()
    actor, command, payload = prepare(operation)
    try:
        original = actor.last['snapshot']
        requests = len(actor.last['requests'])
        failed = actor.command(
            command, payload=payload, ordinal=ordinal, length=exception == 'length_error'
        )
        assert failed['allocation_fault']['fired'], (
            'I3/N2: the one-shot allocation fault actually fires inside the real core call'
        )
        if operation == 'fit-start':
            assert failed['state']['state'] not in {'executing', 'streaming'}, (
                'I10/N2: failed start publication stays interrupted or cancelling before delivery'
            )
            failed = trials.settle(actor)
            assert not failed['state']['active_job_id'], (
                'I10/N2: admitted work cancels and settles after publication failure'
            )
        else:
            assert not failed['reply']['ok'], (
                'I3/N2: failed core publication cannot return a normal successful acknowledgement'
            )
            assert failed['reply']['code'] == 'edi.assistant.resource_exhausted', (
                'I3/N2: inner allocation/length failure retains its resource category'
            )
        assert len(failed['requests']) == requests, (
            'I3/N2: interrupted admission cannot dispatch captured stale work'
        )
        assert (
            not failed['state']['active_turn_id'] and not failed['state']['pending_question_id']
        ), 'I2/I10/N2: failed publication revokes turn and human-hold authority'
        assert failed['state']['state'] not in {
            'streaming',
            'executing',
            'awaiting_answer',
            'awaiting_approval',
        }, 'I10/N2: a caught interruption cannot be overwritten by a later normal phase'
        assert failed['snapshot'] == original, (
            'I4/N2: interruption preserves the exact captured live scientific state'
        )
    finally:
        actor.close()
