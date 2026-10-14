"""Real-worker authorization, fit evidence and accepted-state preservation invariants."""

from __future__ import annotations

import importlib.util
import math
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
_spec = importlib.util.spec_from_file_location(
    'e11_t5_protocol_helpers', ROOT / 'tests/integration/py/test_e11_t5_assistant_protocol.py'
)
protocol = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(protocol)
host = protocol.host


def rows(result):
    return {p['path']: p for p in result['snapshot']['parameters']}


def load_source(host, *, baseline=True):
    result = host.command(
        'load', path=str(ROOT / 'docs/user/cli/pd-neut-cwl_cosio-d20_start-1/project')
    )
    assert not result['snapshot']['files_error'], (
        'I6/I8: the full scientific source is serializable'
    )
    scales = [p for p in rows(result) if p.endswith('.scale')]
    assert scales, 'I8: the real neutron source has an independently controlled scale group'
    if baseline:
        result = host.command('manual_fit', free_paths=scales)
        assert result['reply']['status'] not in {'error', 'superseded'}, (
            'I8: a real manual FitJob establishes the captured accepted-state baseline'
        )
        assert math.isfinite(result['reply']['objective']), (
            'I8: baseline quality is a finite real engine fact'
        )
    host.start()
    return scales


def approve(host, paths, *, iterations=80, elapsed=5000):
    result = host.tool(
        'propose_plan',
        {
            'summary': 'Only the displayed parameter group may move',
            'groups': [{'id': 'workflow', 'paths': paths}],
            'budget': {'max_trials': 3, 'max_iterations': iterations, 'max_elapsed_ms': elapsed},
            'objective': {'absolute_tolerance': 0.0, 'relative_tolerance': 0.0},
        },
    )
    assert result['reply']['ok'], 'I2/I9: a finite explicit scoped plan must be displayable'
    plan = result['state']['pending_plan_id']
    host.provider('turn_finished', **host.binding(), status='completed')
    result = host.user(
        'approve_plan',
        plan_id=plan,
        project_id='project-A',
        revision=host.last['state']['revision'],
    )
    assert result['reply']['ok'], 'I2: real user approval admits exactly this group and budget'
    return plan


def settle(host):
    for _ in range(8):
        result = host.command('fence', milliseconds=800)
        if result['reply']['fenced'] and not result['state']['active_job_id']:
            return result
    pytest.fail('I10: the real worker must settle in the bounded independent host')


def candidate(host, plan, paths):
    begun = host.tool('begin_trial', {'group_id': 'workflow'}, plan_id=plan)
    assert begun['reply']['ok'], 'I8: an approved trial starts on an isolated accepted-state copy'
    trial = begun['reply']['value']['trial_id']
    result = host.tool(
        'set_free', {'flags': [{'path': p, 'free': True} for p in paths]}, plan_id=plan
    )
    assert result['reply']['ok'], (
        'I2/I8: the approved candidate free group is admitted before fitting'
    )
    result = host.tool('fit_trial', {'trial_id': trial}, plan_id=plan)
    assert result['reply']['ok'], 'I8: the supported real single fit must start'
    return trial


def useful_paths(host):
    return [
        p
        for p in rows(host.last)
        if p.endswith(('.scale', '.cell.length_a')) or '.background[' in p
    ]


@pytest.mark.parametrize('in_candidate', [False, True])
def test_fixed_profile_setting_can_be_edited_but_never_freed(host, in_candidate):
    load_source(host, baseline=False)
    host.command('profile', name='cwl-pseudo-voigt-berar-baldinozzi')
    host.start()
    fixed = [
        p
        for p, record in rows(host.last).items()
        if not record['fittable'] and 'asym_beba_limit' in p
    ]
    assert len(fixed) == 1, (
        'I2/I9: the declared source exposes the independent fixed-setting metadata witness'
    )
    plan = approve(host, fixed)
    if in_candidate:
        result = host.tool('begin_trial', {'group_id': 'workflow'}, plan_id=plan)
        assert result['reply']['ok'], (
            'I8: fixed-setting admission is checked on a real isolated candidate too'
        )
    changed = host.tool(
        'set_parameters', {'values': [{'path': fixed[0], 'value': 179.0}]}, plan_id=plan
    )
    assert changed['reply']['ok'], (
        'I2/I9: an explicitly approved valid fixed-setting value remains editable'
    )
    before = host.last['snapshot']
    result = host.tool('set_free', {'flags': [{'path': fixed[0], 'free': True}]}, plan_id=plan)
    assert not result['reply']['ok'], (
        'I2/I9: a fixed profile setting cannot enter any executable free set'
    )
    assert result['snapshot'] == before, (
        'I4/I8: refusing a fixed setting preserves the captured live state'
    )


def test_preexisting_free_cell_cannot_escape_a_scale_only_approval(host):
    scales = load_source(host)
    cell = next(p for p in rows(host.last) if p.endswith('.cell.length_a'))
    host.command('mutate', path=cell, free=True)
    host.start()
    before = host.last['snapshot']
    plan = approve(host, scales)
    begun = host.tool('begin_trial', {'group_id': 'workflow'}, plan_id=plan)
    if not begun['reply']['ok']:
        assert begun['snapshot'] == before, (
            'I2/I8: free-set admission refusal preserves the accepted state'
        )
        return
    trial = begun['reply']['value']['trial_id']
    result = host.tool('fit_trial', {'trial_id': trial}, plan_id=plan)
    if result['reply']['ok']:
        settle(host)
        result = host.tool('evaluate_trial', {'trial_id': trial}, plan_id=plan)
    assert rows(result)[cell] == {p['path']: p for p in before['parameters']}[cell], (
        'I2/I9: pre-existing unapproved cell freedom cannot execute and publish '
        'under a scale-only plan'
    )


@pytest.mark.parametrize('edit', ['value', 'free'])
def test_post_fit_candidate_edits_cannot_reuse_old_evidence_for_adoption(host, edit):
    load_source(host)
    paths = useful_paths(host)
    before = host.last['snapshot']
    plan = approve(host, paths)
    trial = candidate(host, plan, paths)
    settled = settle(host)
    assert any(e['type'] == 'job_finished' for e in settled['events']), (
        'I8: the real fit actually settles before the stale-evidence attack'
    )
    path = next(p for p in paths if p.endswith('.cell.length_a'))
    if edit == 'value':
        changed = host.tool(
            'set_parameters',
            {'values': [{'path': path, 'value': rows(host.last)[path]['value'] * 1.03}]},
            plan_id=plan,
        )
    else:
        changed = host.tool('set_free', {'flags': [{'path': path, 'free': False}]}, plan_id=plan)
    if not changed['reply']['ok']:
        assert changed['snapshot'] == before, (
            'I4/I8: a refused post-fit edit cannot write live state'
        )
        return
    result = host.tool('evaluate_trial', {'trial_id': trial}, plan_id=plan)
    assert not (result['reply']['ok'] and result['reply']['value'].get('accepted')), (
        'I8/I9: candidate values/free flags changed after settlement invalidate that fit evidence'
    )
    assert result['snapshot'] == before, (
        'I8: invalidated fit evidence cannot change the exact accepted state'
    )


@pytest.mark.parametrize('interruption', ['cancel', 'manual-edit', 'detach'])
def test_real_fit_late_completion_never_restores_over_accepted_or_manual_state(host, interruption):
    load_source(host)
    paths = useful_paths(host)
    plan = approve(host, paths)
    candidate(host, plan, paths)
    if interruption == 'cancel':
        host.command('cancel')
    elif interruption == 'detach':
        host.command('detach')
    else:
        path = next(p for p in paths if p.endswith('.cell.length_a'))
        host.command('mutate', path=path, value=rows(host.last)[path]['value'] * 1.013)
    protected = host.last['snapshot']
    result = settle(host)
    assert result['snapshot'] == protected, (
        'I7/I8/I10: cancelled/detached/stale completion preserves every captured value, optional, '
        'free flag, fit-start, relation, persisted record and live row identity'
    )
    assert result['owner_clock_violations'] == 0, (
        'I10: scientific time hooks retain their owner-thread contract'
    )


def test_scientific_terminal_reaches_the_next_provider_request(host):
    load_source(host)
    paths = useful_paths(host)
    plan = approve(host, paths)
    candidate(host, plan, paths)
    request = host.binding()['request_id']
    host.provider('turn_finished', **host.binding(), status='completed')
    result = settle(host)
    assert result['requests'][-1]['request_id'] != request, (
        'I13: completed fit work resumes the provider continuation'
    )
    history = result['requests'][-1]['history']

    def objects(value):
        if isinstance(value, dict):
            yield value
            for child in value.values():
                yield from objects(child)
        elif isinstance(value, list):
            for child in value:
                yield from objects(child)

    terminal = [
        v
        for v in objects(history)
        if str(v.get('status', '')).lower()
        in {'done', 'max_iter', 'no_step', 'cancelled', 'error', 'superseded'}
    ]
    assert terminal, (
        'I8/I13: continuation receives a correlated scientific terminal, not only a job-start ID'
    )
    assert any('objective' in v or 'objective_value' in v for v in objects(terminal)), (
        'I8/I13: the full terminal retains labelled quality facts or explicit unavailability'
    )


def test_consecutive_useful_trials_keep_complete_results_and_accepted_best_state(host):
    load_source(host)
    paths = useful_paths(host)
    plan = approve(host, paths)
    original = host.last['snapshot']
    trial = candidate(host, plan, paths)
    settled = settle(host)
    assert settled['snapshot'] == original, (
        'I8: a moving real fit remains isolated until acceptance'
    )
    accepted = host.tool('evaluate_trial', {'trial_id': trial}, plan_id=plan)
    assert accepted['reply']['ok'] and accepted['reply']['value']['accepted'], (
        'I8/I9: an eligible moving real fit is usable under the declared small-workflow budgets'
    )
    best = accepted['snapshot']
    assert best != original, 'I8: the useful-workflow witness actually moves fitted state'
    begun = host.tool('begin_trial', {'group_id': 'workflow'}, plan_id=plan)
    assert begun['reply']['ok'], (
        'I8/F6: retaining the full first outcome leaves capacity for a second ordinary trial'
    )
    rejected = host.tool(
        'discard_trial', {'trial_id': begun['reply']['value']['trial_id']}, plan_id=plan
    )
    assert rejected['reply']['ok'], 'I8/I10: a later rejected trial can settle/discard normally'
    assert rejected['snapshot'] == best, (
        'I8: a later rejected trial preserves the exact accepted best state'
    )
