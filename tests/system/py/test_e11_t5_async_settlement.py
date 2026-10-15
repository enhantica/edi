"""S5 missing async failure paths over real Controller/Worker and captured accepted state.

No simulated optimizer results: baseline refusal, real cancellation and real candidate
submission are observed; complete retained results use preservation/correlation invariants.
"""

from __future__ import annotations

import importlib.util
import os
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
_spec = importlib.util.spec_from_file_location(
    'async_trials', ROOT / 'tests/system/py/test_e11_t5_assistant_trials.py'
)
trials = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(trials)
protocol = trials.protocol


@pytest.fixture
def host():
    binary = Path(
        os.environ.get(
            'EDI_ASSISTANT_ASYNC_PROBE',
            ROOT / 'build/assistant-core-tests/assistant_async_settlement_probe',
        )
    )
    assert binary.is_file(), (
        'I10/S5: async settlement consumer links the real public core and worker'
    )
    actor = protocol.Host(binary, reply_timeout=5)
    try:
        yield actor
    finally:
        actor.close()


def candidate(actor, *, unavailable=False):
    if unavailable:
        actor.start()
        paths = ['structure.cell.length_a']
    else:
        paths = trials.load_source(actor, baseline=False)
    plan = trials.approve(actor, paths, iterations=80)
    begun = actor.tool('begin_trial', {'group_id': 'workflow'}, plan_id=plan)
    assert begun['reply']['ok'], 'I8/S5: actual isolated candidate precedes async failure exercise'
    trial = begun['reply']['value']['trial_id']
    return plan, trial


def start(actor, plan, trial):
    original = actor.last['snapshot']
    result = actor.tool('fit_trial', {'trial_id': trial}, plan_id=plan, call_id='async-real-fit')
    assert result['reply']['ok'] and result['state']['active_job_id'], (
        'I8/I10/S5: real scientific work is admitted before its failure or cancellation'
    )
    job = result['state']['active_job_id']
    binding = actor.binding()
    finished = actor.provider('turn_finished', **binding, status='completed')
    assert finished['reply']['ok'], (
        'I13/S5: real provider response completes while scientific work is pending'
    )
    return original, job


def terminals(observed, job):
    results = [
        event
        for event in observed['events']
        if event.get('type') == 'tool_result'
        and event.get('call_id') == 'async-real-fit'
        and not event.get('pending')
    ]
    return [event for event in results if event.get('result', {}).get('job_id') == job]


def finish_dispatched_continuation(actor):
    """Complete only a request actually delivered to the provider hook."""
    state = actor.last['state']
    if state['state'] == 'streaming' and state['active_turn_id'] and actor.last['requests']:
        request = actor.last['requests'][-1]
        if request['turn_id'] == state['active_turn_id']:
            return actor.provider('turn_finished', **actor.binding(), status='completed')
    return actor.last


def retry(actor):
    return actor.user(
        'message',
        text='Continue after the visible interruption',
        connection_id='connection-A',
        model=protocol.MODEL,
        effort='high',
    )


@pytest.mark.parametrize('failure', ['unavailable-baseline', 'cancelled-baseline'])
def test_failed_baseline_settles_with_complete_refusal_and_recoverable_conversation(host, failure):
    # Accident: baseline delivery emits a shortened result but strands the old turn busy.
    plan, trial = candidate(host, unavailable=failure == 'unavailable-baseline')
    if failure == 'cancelled-baseline':
        host.command('queue_hold')
    original, job = start(host, plan, trial)
    if failure == 'cancelled-baseline':
        host.command('cancel')
        host.command('queue_release')
    settled = trials.settle(host)
    terminal = terminals(settled, job)
    finished = [
        event
        for event in settled['events']
        if event.get('type') == 'job_finished' and event.get('job_id') == job
    ]
    finish_dispatched_continuation(host)
    new_turn = retry(host)
    checks = {
        'one_complete_tool_refusal': len(terminal) == 1 and terminal[0]['ok'] is False,
        'one_scientific_settlement': len(finished) == 1,
        'complete_diagnostic_outcome': len(finished) == 1
        and isinstance(finished[0].get('result'), dict)
        and isinstance(finished[0]['result'].get('diagnostics'), list),
        'accepted_state_preserved': settled['snapshot'] == original,
        'job_retired': not settled['state']['active_job_id'],
        'fresh_human_admitted': new_turn['reply']['ok'],
    }
    assert all(checks.values()), (
        'I8/I10/S5: baseline failure settles complete diagnostics, preserves exact accepted state '
        'and permits explicit human recovery: ' + str(checks)
    )


@pytest.mark.parametrize('armed', [False, True], ids=['actual-fit-control', 'submission-refusal'])
def test_candidate_start_submission_failure_is_contained_and_settled(host, armed):
    # Existing Worker::Seams observes Submitted synchronously before queue insertion.
    plan, trial = candidate(host)
    host.command('candidate_submit_failure', armed=armed)
    original, job = start(host, plan, trial)
    settled = trials.settle(host)
    receipt = settled['async_submission']
    assert receipt['fit_submissions'] == 1 and receipt['failures'] == int(armed), (
        'I10/S5: actual candidate submission reaches the ordinary '
        'dependency failure or its control'
    )
    assert not settled['state']['active_job_id'] and settled['snapshot'] == original, (
        'I8/I10/S5: candidate start failure cannot escape owner delivery, '
        'strand work or mutate live state'
    )
    assert len(terminals(settled, job)) == 1, (
        'I10/S5: every admitted real candidate receives exactly one complete terminal'
    )
    if armed:
        settled = finish_dispatched_continuation(host)
        assert (
            not settled['state']['active_turn_id'] or settled['state']['state'] == 'interrupted'
        ), 'I10/S5: failed submission visibly interrupts rather than resuming a successful phase'
        assert retry(host)['reply']['ok'], (
            'I10/S5: ordinary candidate-start failure permits explicit recovery'
        )


def test_continuation_failure_preserves_the_actual_complete_terminal_in_next_human_history(host):
    plan, trial = candidate(host)
    original, job = start(host, plan, trial)
    settled = trials.settle(host)
    actual = terminals(settled, job)
    assert len(actual) == 1, 'I8/I13/S5: actual optimizer settles before the continuation failure'
    assert settled['requests'][-1]['request_id'] != actual[0]['request_id'], (
        'I13/S5: the real settled call reaches its fresh provider continuation'
    )
    failed = host.provider(
        'turn_finished',
        **host.binding(),
        status='failed',
        message='Ordinary mock continuation unavailable',
    )
    assert not failed['reply']['ok'] and not failed['state']['active_turn_id'], (
        'I10/I13/S5: ordinary continuation failure is visible and retires execution authority'
    )
    retried = retry(host)
    assert retried['reply']['ok'] and retried['snapshot'] == original, (
        'I8/I10/S5: continuation failure preserves exact accepted state '
        'and permits a fresh human message'
    )
    history = retried['requests'][-1]['history']
    rows = [
        row
        for row in history
        if row.get('type') == 'tool_result'
        and row.get('call_id') == 'async-real-fit'
        and not row.get('pending')
    ]
    assert len(rows) == 1 and rows[0]['result'] == actual[0]['result'], (
        'I8/I13/S5: failed continuation never replaces or truncates the actual scientific terminal'
    )


@pytest.mark.parametrize('armed', [False, True], ids=['direct-control', 'direct-submit-refusal'])
def test_shared_fitjob_start_failure_retains_prior_finished_state_without_false_running(
    host, armed
):
    paths = trials.load_source(host, baseline=False)
    host.command('prepare_free_group', paths=paths)
    result = host.command('direct_submission', armed=armed)
    observed = result['reply']
    assert observed['before_finished'] == 1, (
        'I8/S5: direct shared FitJob first completes a real native report before retry admission'
    )
    assert result['async_submission']['fit_submissions'] == 2, (
        'I10/S5: both original and retry reach the actual public worker submission boundary'
    )
    if armed:
        assert result['async_submission']['failures'] == 1 and observed['threw'], (
            'I10/S5: ordinary direct submission dependency failure reaches '
            'its existing public seam'
        )
        assert not observed['running_at_reply'] and observed['ticket_at_reply'] == 0, (
            'I10/S5: an unqueued failed direct start cannot leave a falsely running FitJob'
        )
        assert (
            observed['finished'] == 1 and observed['previous_report'] == observed['current_report']
        ), (
            'I8/I10/S5: failed retry neither replaces nor duplicates the '
            'prior complete callback report'
        )
        assert observed['before'] == observed['after'], (
            'I4/I8/S5: failed retry leaves exact prior finished scientific state intact'
        )
    else:
        assert observed['admitted'] and not observed['threw'] and observed['finished'] == 2, (
            'I8/I10/S5: ordinary shared FitJob retry actually runs and settles another real report'
        )
