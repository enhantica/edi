"""Actual single-thread worker kit: scientific deadlines must progress inside optimizer work."""

from __future__ import annotations

import importlib.util
import os
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
_spec = importlib.util.spec_from_file_location(
    'e11_t5_owner_trials', Path(__file__).with_name('test_e11_t5_assistant_trials.py')
)
trials = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(trials)


@pytest.fixture
def owner():
    override = os.environ.get('EDI_ASSISTANT_OWNER_CORE_PROBE')
    binary = (
        Path(override)
        if override
        else ROOT / 'build/assistant-owner-tests/edi/core/assistant_contract_probe'
    )
    assert binary.is_file(), (
        'I10: the real core must also qualify with EDI_WORKER_OWNER_THREAD enabled'
    )
    actor = trials.protocol.Host(binary, reply_timeout=5)
    try:
        yield actor
    finally:
        actor.close()


@pytest.mark.parametrize(
    'elapsed', [25, 5000], ids=['deadline-inside-work', 'positive-useful-work']
)
def test_owner_thread_optimizer_enforces_deadline_without_waiting_for_owner_poll(owner, elapsed):
    trials.load_source(owner)
    assert owner.last['owner_thread_kit'], (
        'I10: this case executes the actual owner-thread worker build'
    )
    paths = trials.useful_paths(owner)
    plan = trials.approve(owner, paths, elapsed=elapsed)
    begun = owner.tool('begin_trial', {'group_id': 'workflow'}, plan_id=plan)
    assert begun['reply']['ok'], (
        'I8/I10: the real positive source admits a trial before its budget expires'
    )
    trial = begun['reply']['value']['trial_id']
    free = owner.tool(
        'set_free', {'flags': [{'path': path, 'free': True} for path in paths]}, plan_id=plan
    )
    assert free['reply']['ok'], 'I8: the real candidate has an explicit useful fittable free set'
    protected = free['snapshot']
    owner.command('clock', steady=True)
    started = owner.tool('fit_trial', {'trial_id': trial}, plan_id=plan)
    assert started['reply']['ok'], (
        'I10: elapsed enforcement must be exercised inside an admitted optimizer job'
    )
    result = trials.settle(owner)
    terminal = [event for event in result['events'] if event.get('type') == 'job_finished']
    assert terminal, 'I10: actual owner-thread work settles before its evidence is examined'
    assert result['owner_clock_violations'] == 0, (
        'I10: scientific deadline checks preserve the owner-only public clock contract'
    )
    assert result['snapshot'] == protected, (
        'I8/I10: optimizer work never publishes into accepted live state before evaluation'
    )
    if elapsed == 25 and result['owner_work_max_ms'] >= elapsed:
        assert not terminal[-1].get('converged'), (
            'I10: an optimizer exceeding its approved elapsed budget cannot '
            'claim ordinary convergence while the owner event loop is occupied'
        )
        evaluated = owner.tool('evaluate_trial', {'trial_id': trial}, plan_id=plan)
        assert not (evaluated['reply']['ok'] and evaluated['reply']['value'].get('accepted')), (
            'I8/I10: deadline-stopped work cannot be accepted as an ordinary completed improvement'
        )
        assert evaluated['snapshot'] == protected, (
            'I10: budget exhaustion preserves the exact accepted state through late evaluation'
        )
    else:
        assert terminal[-1].get('converged'), (
            'I8/I10: the same real source makes useful progress with a sufficient finite budget'
        )
        evaluated = owner.tool('evaluate_trial', {'trial_id': trial}, plan_id=plan)
        assert evaluated['reply']['ok'] and evaluated['reply']['value'].get('accepted'), (
            'I8/I10: deadline enforcement retains the useful real owner-thread fit/adoption path'
        )
