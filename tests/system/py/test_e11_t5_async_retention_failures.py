"""Missing S5 failure witnesses through the exact accepted future host lease.

These remain API setup holes until the public TerminalRetention implementation links.
They neither replace actual VM pressure proof nor simulate fitted scientific values.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
_spec = importlib.util.spec_from_file_location(
    'async_role_contract', ROOT / 'tests/system/py/test_e11_t5_terminal_retention.py'
)
lease = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(lease)
role = lease.role
trials = lease.trials


def outcomes(observed):
    return [
        event
        for event in observed['events']
        if event.get('type') == 'tool_result'
        and event.get('call_id') == 'retained-call'
        and not event.get('pending')
    ]


@pytest.mark.parametrize('role', ['accept'], indirect=True)
@pytest.mark.parametrize('operation', ['fit', 'question'])
def test_accepted_stop_keeps_its_lease_until_actual_worker_or_human_settlement(role, operation):
    # Existing twelve gates inject start/settle refusal; this starts with accepted capacity.
    invoke = lease.prepare(role, operation)
    original = role.last['snapshot']
    if operation == 'fit':
        role.command('queue_hold')
    admitted = invoke()
    assert admitted['reply']['ok'] and admitted['retention']['started'] == 1, (
        'I10/S5/S6: real accepted work starts its installed unique retaining role'
    )
    stopped = role.command('cancel')
    if operation == 'fit':
        assert stopped['retention']['held'] == 1 and stopped['retention']['destroyed'] == 0, (
            'I10/S5/S6: Stop before queued baseline delivery cannot release '
            'its running terminal hold'
        )
        role.command('queue_release')
        settled = trials.settle(role)
    else:
        settled = stopped
    observed = settled['retention']
    terminal = outcomes(settled)
    assert observed['settled'] == 1 and len(terminal) == 1 and terminal[0]['ok'] is False, (
        'I10/S5/S6: actual cancellation consumes its hold only into one full correlated refusal'
    )
    assert observed['terminals'][0]['result'] == terminal[0]['result'], (
        'I3/S5/S6: retained cancellation is exactly the actual complete controller outcome'
    )
    assert observed['held'] == 0 and settled['snapshot'] == original, (
        'I8/I10/S5/S6: actual cancellation settles capacity without '
        'modifying captured accepted state'
    )


@pytest.mark.parametrize('role', ['settle-false'], indirect=True)
def test_complete_real_fit_is_quarantined_without_stop_or_partial_success(role):
    # The older settle-false case requested Stop first; retain a genuine noncancelled result here.
    invoke = lease.prepare(role, 'fit')
    original = role.last['snapshot']
    admitted = invoke()
    assert admitted['reply']['ok'], (
        'I8/S5: genuine supported optimizer work precedes failed UI retention'
    )
    role.provider('turn_finished', **role.binding(), status='completed')
    before_requests = len(role.last['requests'])
    settled = trials.settle(role)
    observed = settled['retention']
    assert observed['settled'] == 1 and len(observed['terminals']) == 1, (
        'I10/S5/S6: failed UI settlement receives the one actual complete scientific result'
    )
    complete = observed['terminals'][0]
    assert complete['pending'] is False and isinstance(complete['result'], dict), (
        'I3/S5/S6: quarantine retains the full bound terminal object, '
        'never its start acknowledgement'
    )
    assert complete['result']['status'] in {'done', 'max_iter', 'no_step'}, (
        'I8/S5: ordinary noncancelled real scientific settlement reaches '
        'retention before quarantine'
    )
    assert observed['held'] == 1 and observed['quarantined'] == 1, (
        'I10/S5/S6: failed complete retention preserves the actual result '
        'and its allowance for recovery'
    )
    assert len(settled['requests']) == before_requests and settled['snapshot'] == original, (
        'I8/I10/S5/S6: unretained terminal neither continues nor '
        'overwrites accepted scientific state'
    )
    before_terminal = complete
    role.command('cancel')
    still = role.command('inspect')
    assert (
        still['retention']['held'] == 1 and still['retention']['terminals'][0] == before_terminal
    ), 'I8/I10/S5/S6: subsequent Stop cannot discard or replace a quarantined complete real result'
    detached = role.command('detach')
    assert detached['retention']['held'] == 0 and detached['retention']['destroyed'] == 1, (
        'I10/S5/S6: explicit owner teardown alone releases the quarantined remaining lease'
    )


@pytest.mark.parametrize('role', ['accept'], indirect=True)
def test_unavailable_baseline_uses_the_same_complete_retaining_role_before_recovery(role):
    role.start()
    plan = trials.approve(role, ['structure.cell.length_a'])
    begun = role.tool('begin_trial', {'group_id': 'workflow'}, plan_id=plan)
    assert begun['reply']['ok'], (
        'I8/S5: real partial-project baseline attempt has an isolated candidate'
    )
    original = begun['snapshot']
    admitted = role.tool(
        'fit_trial',
        {'trial_id': begun['reply']['value']['trial_id']},
        plan_id=plan,
        call_id='retained-call',
    )
    assert admitted['reply']['ok'], (
        'I10/S5: actual baseline evaluation receives its pending real lease'
    )
    role.provider('turn_finished', **role.binding(), status='completed')
    settled = trials.settle(role)
    observed = settled['retention']
    assert observed['started'] == 1 and observed['settled'] == 1 and observed['held'] == 0, (
        'I10/S5/S6: unavailable baseline settles through the same admitted terminal hold'
    )
    terminal = observed['terminals'][0]
    assert terminal['ok'] is False and isinstance(terminal['result'].get('diagnostics'), list), (
        'I8/S5/S6: unavailable scientific work retains complete '
        'diagnostic refusal without invented fit truth'
    )
    assert settled['snapshot'] == original and not settled['state']['active_job_id'], (
        'I8/I10/S5: unavailable baseline preserves exact accepted state and retires actual work'
    )
