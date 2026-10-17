"""V1-V3 finite public admission, settlement and synchronous callback siblings.

Actual optimizer outcomes are compared only for exact preservation/correlation;
this module supplies no scientific numeric oracle. The existing one-shot owner
allocator and ordinary Worker/provider dependency callbacks are reused unchanged.
"""

from __future__ import annotations

import importlib.util
import os
from functools import partial
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]


def module(name, path):
    spec = importlib.util.spec_from_file_location(name, ROOT / path)
    loaded = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(loaded)
    return loaded


lease = module('boundaries_lease', 'tests/system/py/test_e11_t5_terminal_retention.py')
trials, protocol, questions = lease.trials, lease.protocol, lease.questions


@pytest.fixture
def actors(monkeypatch):
    live = []

    def create(mode='accept'):
        monkeypatch.setenv('EDI_TEST_RETENTION_MODE', mode)
        path = Path(
            os.environ.get(
                'EDI_ASSISTANT_RECOVERY_PROBE',
                ROOT / 'build/assistant-core-tests/assistant_recovery_boundaries_probe',
            )
        )
        assert path.is_file(), 'I10/V1-V3: the separate consumer links real current core APIs'
        actor = protocol.Host(path, reply_timeout=5)
        live.append(actor)
        return actor

    yield create
    for actor in reversed(live):
        actor.close()


def fit_payload(actor):
    paths = trials.load_source(actor, baseline=False)
    plan = trials.approve(actor, paths, iterations=80)
    begun = actor.tool('begin_trial', {'group_id': 'workflow'}, plan_id=plan)
    assert begun['reply']['ok'], 'I8/V1: genuine isolated candidate precedes reservation failure'
    trial = begun['reply']['value']['trial_id']
    free = actor.tool(
        'set_free', {'flags': [{'path': p, 'free': True} for p in paths]}, plan_id=plan
    )
    assert free['reply']['ok'], (
        'I8/V1: declared candidate flags are legal before pre-start failure'
    )
    return protocol.envelope(
        'tool_call',
        **actor.binding(),
        call_id='boundary-fit',
        name='fit_trial',
        arguments={'trial_id': trial},
        project_id='project-A',
        revision=actor.last['state']['revision'],
        plan_id=plan,
    )


@pytest.mark.parametrize('door', ['control', 'ordinary-submission', 'bad_alloc', 'length_error'])
def test_provisional_lease_unwinds_after_every_reached_prestart_abort(actors, door):
    # Accident: an accepted provisional lease survives a later preparation failure.
    ordinal = 0
    if door in {'bad_alloc', 'length_error'}:
        positive = actors()
        payload = fit_payload(positive)
        qualified = positive.command('fault_provider', payload=payload, ordinal=0, length=False)
        marks = qualified['allocation_fault']['milestones']
        reserved = next(
            row['allocation_count'] for row in marks if row['type'] == 'reserve_returned'
        )
        published = next(row['allocation_count'] for row in marks if row['type'] == 'job_started')
        ordinal = int((reserved + published) // 2)
        assert reserved < ordinal < published, (
            'I3/V1: existing allocator selection follows successful reserve and '
            'precedes start publication'
        )
        trials.settle(positive)
    actor = actors()
    payload = fit_payload(actor)
    original = actor.last['snapshot']
    if door == 'ordinary-submission':
        actor.command('submission_failure', channel='assistant-baseline')
    result = actor.command(
        'fault_provider', payload=payload, ordinal=ordinal, length=door == 'length_error'
    )
    observed = result['retention']
    assert len(observed['prospective']) == 1, (
        'I10/V1: actual producer preflight obtains exactly one prospective host lease'
    )
    if door == 'control':
        assert result['reply']['ok'] and observed['started'] == 1, (
            'I10/V1: unarmed preparation reaches genuine accepted asynchronous work'
        )
        completed = trials.settle(actor)
        assert completed['retention']['held'] == 0 and completed['snapshot'] == original, (
            'I8/I10/V1: ordinary actual settlement preserves live state and releases its allowance'
        )
        return
    if door in {'bad_alloc', 'length_error'}:
        assert result['allocation_fault']['fired'] and result['worker_jobs'] == [], (
            'I3/V1: existing one-shot failure actually reaches post-reserve '
            'preparation before submission'
        )
    else:
        assert result['async_submission']['failures'] == 1, (
            'I10/V1: ordinary existing Submitted trace failure reaches the prequeue boundary'
        )
    assert not result['reply']['ok'] and observed['started'] == 0, (
        'I10/V1: failed preparation never publishes a successfully started lease'
    )
    assert not result['state']['active_job_id'] and result['snapshot'] == original, (
        'I8/I10/V1: pre-start refusal cannot start work or alter exact accepted scientific state'
    )
    assert observed['held'] == 0 and observed['destroyed'] == 1, (
        'I10/V1: every unpublished accepted provisional lease unwinds on preparation refusal'
    )


def question_setup(actor):
    questions.start(actor)
    asked = actor.tool('ask_question', questions.arguments(), call_id='boundary-question')
    assert asked['reply']['ok'], 'I3/V3: a genuine public question precedes answer settlement'
    question = asked['reply']['value']['question_id']
    actor.provider('turn_finished', **actor.binding(), status='completed')
    return question


def terminal_rows(result):
    return [
        event
        for event in result['events']
        if event.get('type') == 'tool_result'
        and event.get('call_id') in {'boundary-question', 'boundary-fit', 'boundary-read'}
        and event.get('pending') is False
    ]


def continuation(actor, route):
    question = None
    if route == 'initial':
        actor.command('attach', id='project-A')
        actor.connect()
        action = partial(
            actor.user,
            'message',
            text='Ordinary initial user',
            connection_id='connection-A',
            model=protocol.MODEL,
            effort='high',
        )
    elif route == 'answer':
        question = question_setup(actor)
        action = partial(actor.user, 'answer', question_id=question, answer='inspect')
    elif route == 'approval':
        actor.start()
        proposed = actor.tool(
            'propose_plan',
            {
                'summary': 'Only explicit cell scope',
                'groups': [{'id': 'cell', 'paths': ['structure.cell.length_a']}],
                'budget': {'max_trials': 2, 'max_iterations': 8, 'max_elapsed_ms': 5000},
                'objective': {'absolute_tolerance': 0.0, 'relative_tolerance': 0.0},
            },
        )
        assert proposed['reply']['ok'], (
            'I2/V3: trusted approval follows an actual current proposal'
        )
        plan = proposed['state']['pending_plan_id']
        actor.provider('turn_finished', **actor.binding(), status='completed')
        action = partial(
            actor.user,
            'approve_plan',
            plan_id=plan,
            project_id='project-A',
            revision=actor.last['state']['revision'],
        )
    elif route == 'turn-finished':
        actor.start()
        read = actor.tool('inspect_project', call_id='boundary-read')
        assert read['reply']['ok'], (
            'I3/V3: an actual complete tool precedes original response completion'
        )
        action = partial(actor.provider, 'turn_finished', **actor.binding(), status='completed')
    else:
        payload = fit_payload(actor)
        admitted = actor.command('provider', payload=payload)
        assert admitted['reply']['ok'], 'I8/V3: genuine native work precedes continuation failure'
        if route == 'fit-before-response':
            trials.settle(actor)
            assert terminal_rows(actor.last), (
                'I8/V3: actual complete optimizer result precedes original response completion'
            )
            action = partial(
                actor.provider, 'turn_finished', **actor.binding(), status='completed'
            )
        else:
            actor.provider('turn_finished', **actor.binding(), status='completed')
            action = partial(trials.settle, actor)
    return action, question


@pytest.mark.parametrize('armed', [False, True], ids=['delivered-control', 'callback-refusal'])
@pytest.mark.parametrize(
    'route',
    [
        'initial',
        'approval',
        'answer',
        'turn-finished',
        'fit-before-response',
        'fit-after-response',
    ],
)
def test_synchronous_request_failure_settles_every_reached_owner_continuation(
    actors, route, armed
):
    # Accident: a callback throws after IDs were installed, leaving an undelivered busy turn.
    actor = actors()
    action, question = continuation(actor, route)
    original = actor.last['snapshot']
    count = len(actor.last['requests'])
    attempts = actor.last['provider_callback']['attempts']
    actor.command('provider_request_failure', armed=armed)
    result = action()
    assert result['provider_callback']['attempts'] == attempts + 1, (
        'I13/V3: this public owner route actually attempts one fresh provider request'
    )
    assert result['provider_callback']['failures'] == int(armed), (
        'I13/V3: only the armed ordinary provider callback fails, without claiming dispatch'
    )
    assert len(result['requests']) == count + int(not armed), (
        'I13/V3: an undelivered callback never counts as a captured outgoing request'
    )
    actual = terminal_rows(result)
    if route == 'answer':
        expected = {'question_id': question, 'answer': 'inspect', 'selected_option_id': 'inspect'}
        assert len(actual) == 1 and actual[0]['result'] == expected, (
            'I3/V3: callback failure preserves the actual complete human answer exactly'
        )
    if route.startswith('fit-'):
        assert len(actual) == 1 and isinstance(actual[0]['result'].get('diagnostics'), list), (
            'I8/V3: callback failure preserves a complete actual correlated scientific outcome'
        )
    if not armed:
        # Only an actually delivered successful request can receive its real completion.
        actor.provider('turn_finished', **actor.binding(), status='completed')
        result = actor.last
    assert not result['state']['active_turn_id'], (
        'I10/I13/V3: failed synchronous dispatch revokes undelivered request and turn authority'
    )
    assert not result['state']['pending_plan_id'] or not armed, (
        'I2/V3: failed continuation cannot leave executable approved authority'
    )
    recovered = actor.user(
        'message',
        text='Continue after ordinary provider failure',
        connection_id='connection-A',
        model=protocol.MODEL,
        effort='high',
    )
    assert recovered['reply']['ok'] and recovered['snapshot'] == original, (
        'I8/I10/V3: every failed synchronous caller permits a fresh human '
        'without altering live state'
    )
    history = recovered['requests'][-1]['history']
    for terminal in actual:
        matching = [
            row
            for row in history
            if row.get('type') == 'tool_result'
            and row.get('call_id') == terminal['call_id']
            and row.get('pending') is False
        ]
        assert len(matching) == 1 and matching[0]['result'] == terminal['result'], (
            'I3/I8/V3: recovery wire preserves the complete original answer or '
            'real optimizer outcome'
        )


def test_pending_answer_recovery_preserves_answer_without_resuming_a_revoked_request(actors):
    # A real resource refusal revokes the original turn before pending-answer retry.
    actor = actors('settle-false')
    question = question_setup(actor)
    refused = actor.user('answer', question_id=question, answer='inspect')
    assert not refused['reply']['ok'] and refused['retention']['held'] == 1, (
        'I3/I10/V3: real failed host retention preserves the correlated pending answer'
    )
    assert not refused['state']['active_turn_id'], (
        'I2/I10/V3: genuine failed answer retention already revokes original request authority'
    )
    actor.command('retention_policy', mode='accept')
    count = len(actor.last['requests'])
    recovered = actor.user('answer', question_id=question, answer='inspect')
    expected = {'question_id': question, 'answer': 'inspect', 'selected_option_id': 'inspect'}
    assert recovered['reply']['ok'] and recovered['reply']['value'] == expected, (
        'I3/V3: pending-answer retry preserves the original complete real answer'
    )
    assert len(recovered['requests']) == count and recovered['retention']['held'] == 0, (
        'I2/I10/V3: actual recovery consumes the hold without dispatching a revoked continuation'
    )
    fresh = actor.user(
        'message',
        text='Continue after real answer recovery',
        connection_id='connection-A',
        model=protocol.MODEL,
        effort='high',
    )
    assert fresh['reply']['ok'], (
        'I10/V3: settled pending answer permits a fresh ordinary human turn'
    )
    rows = [
        row
        for row in fresh['requests'][-1]['history']
        if row.get('type') == 'tool_result'
        and row.get('call_id') == 'boundary-question'
        and row.get('pending') is False
    ]
    assert len(rows) == 1 and rows[0]['result'] == expected, (
        'I3/V3: next real outgoing history keeps exactly the original complete recovered answer'
    )


@pytest.mark.parametrize('operation', ['fit', 'question'])
@pytest.mark.parametrize('retirement', ['project-replacement', 'connection-retirement'])
def test_explicit_scope_retirement_releases_failed_retention_and_fences_late_delivery(
    actors, operation, retirement
):
    # Existing detach gates remain; these exercise the other actual owner retirement callers.
    actor = actors('settle-false')
    invoke = lease.prepare(actor, operation)
    original = actor.last['snapshot']
    admitted = invoke()
    assert admitted['reply']['ok'], (
        'I10/V2: genuine started work precedes permanent retention refusal'
    )
    old_binding = actor.binding()
    if operation == 'fit':
        actor.provider('turn_finished', **old_binding, status='completed')
        settled = trials.settle(actor)
    else:
        actor.provider('turn_finished', **old_binding, status='completed')
        settled = actor.user(
            'answer', question_id=admitted['reply']['value']['question_id'], answer='inspect'
        )
    terminal = settled['retention']['terminals'][0]
    stopped = actor.command('cancel')
    assert (
        stopped['retention']['held'] == 1 and stopped['retention']['terminals'][0] == terminal
    ), 'I8/I10/V2: ordinary Stop preserves the actual unretained outcome and its allowance'
    if retirement == 'project-replacement':
        retired = actor.command('attach', id='project-B')
    else:
        retired = actor.provider(
            'connection',
            connection_id='connection-B',
            status='ready',
            capabilities=[
                {
                    'id': protocol.MODEL,
                    'display_name': 'Independent new connection',
                    'efforts': ['high'],
                    'attachment_types': [],
                }
            ],
        )
    assert retired['reply']['ok'] and retired['retention']['held'] == 0, (
        'I10/V2: explicit project or account scope retirement releases its '
        'permanently refusing owner'
    )
    assert retired['retention']['destroyed'] == 1 and retired['snapshot'] == original, (
        'I8/I10/V2: explicit teardown destroys exactly its unique lease '
        'without changing live science'
    )
    late = actor.provider('text_delta', **old_binding, text='Late retired owner output')
    assert not late['reply']['ok'] and late['snapshot'] == original, (
        'I2/I10/V2: retired owner deliveries cannot revive the old '
        'conversation or alter accepted state'
    )
