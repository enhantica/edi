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


def approve(host, paths, *, iterations=80, elapsed=5000, absolute=0.0):
    result = host.tool(
        'propose_plan',
        {
            'summary': 'Only the displayed parameter group may move',
            'groups': [{'id': 'workflow', 'paths': paths}],
            'budget': {'max_trials': 3, 'max_iterations': iterations, 'max_elapsed_ms': elapsed},
            'objective': {'absolute_tolerance': absolute, 'relative_tolerance': 0.0},
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


@pytest.mark.parametrize('door', [False, True], ids=['typed-edit', 'live-preview'])
@pytest.mark.parametrize(
    'armed', [False, True], ids=['positive-publication', 'allocation-failure']
)
def test_result_publication_is_complete_or_preserves_exact_original_state(host, door, armed):
    load_source(host)
    before = host.last['snapshot']
    result = host.command('publication_fault', door=door, armed=armed)
    if result['reply']['threw']:
        assert result['reply']['fired'], (
            'I4: the independent allocation failpoint actually fired during publication'
        )
        assert result['snapshot'] == before, (
            'I4/I8: throwing publication preserves the exact original parameter/result state '
            'and row identities'
        )
    else:
        assert result['reply']['complete'], (
            'I4/I8: publication without a throwing partial state commits the whole prepared result'
        )
        assert result['snapshot'] != before, (
            'I4: the positive publication control performs an actual state change'
        )


def test_stale_manual_fit_record_is_not_used_as_the_accepted_state_baseline(host):
    load_source(host)
    paths = useful_paths(host)
    fitted = host.command('manual_fit', free_paths=paths)
    assert fitted['reply']['converged'], (
        'I8: the independent manual FitJob establishes a converged historical record'
    )
    old_objective = fitted['reply']['objective']
    cell = next(p for p in paths if p.endswith('.cell.length_a'))
    host.command('mutate', path=cell, value=rows(host.last)[cell]['value'] * 1.03)
    current = host.command('objective')
    assert current['reply']['objective'] > old_objective * 1.1, (
        'I8: the independently calculated weighted residual proves the manual '
        'edit invalidated historical fit quality'
    )
    original = current['snapshot']
    host.start()
    plan = approve(host, paths, absolute=old_objective * 0.01)
    begun = host.tool('begin_trial', {'group_id': 'workflow'}, plan_id=plan)
    if not begun['reply']['ok']:
        assert begun['snapshot'] == original, (
            'I8: refusing an unavailable current baseline preserves all accepted state'
        )
        return
    trial = begun['reply']['value']['trial_id']
    host.tool(
        'set_free', {'flags': [{'path': path, 'free': True} for path in paths]}, plan_id=plan
    )
    started = host.tool('fit_trial', {'trial_id': trial}, plan_id=plan)
    if not started['reply']['ok']:
        assert started['snapshot'] == original, (
            'I8: refusing stale-baseline work before fitting changes no accepted state'
        )
        return
    settle(host)
    evaluated = host.tool('evaluate_trial', {'trial_id': trial}, plan_id=plan)
    if not evaluated['reply']['ok']:
        assert evaluated['snapshot'] == original, (
            'I8: a late currentness refusal changes no accepted state'
        )
        return
    assert evaluated['reply']['value']['accepted'], (
        'I8: completed comparable improvement uses the actual current accepted '
        'state, never its stale historical fit record'
    )
    measured = host.command('objective')
    assert measured['reply']['objective'] + old_objective * 0.01 < current['reply']['objective'], (
        'I8: actual accepted quality improves by the independently declared '
        'tolerance on the original weighted point population'
    )


def test_real_joint_fit_adoption_then_discard_preserves_both_banks(host):
    source = ROOT / 'docs/user/cli/pd-neut-tof_ferrite-austenite-beer_joint/project'
    loaded = host.command('load', path=str(source))
    assert loaded['context']['project']['fitting_mode'] == 'joint', (
        'I8: the joint witness loads the actual two-bank source project'
    )
    paths = [p for p in rows(loaded) if p.endswith(('.scale', '.cell.length_a'))]
    baseline = host.command('manual_fit', free_paths=[p for p in paths if p.endswith('.scale')])
    assert baseline['reply']['converged'], (
        'I8: a real joint manual FitJob establishes a finite current baseline'
    )
    host.start()
    plan = approve(host, paths, iterations=30)
    original = host.last['snapshot']
    trial = candidate(host, plan, paths)
    settled = settle(host)
    assert settled['snapshot'] == original, (
        'I8: both banks and structures remain untouched while the real joint candidate fits'
    )
    accepted = host.tool('evaluate_trial', {'trial_id': trial}, plan_id=plan)
    assert accepted['reply']['ok'] and accepted['reply']['value']['accepted'], (
        'I8/I9: a converged comparable moving joint fit can be adopted through the real edit door'
    )
    best = accepted['snapshot']
    assert best != original, 'I8: joint adoption publishes actual scientific movement'
    begun = host.tool('begin_trial', {'group_id': 'workflow'}, plan_id=plan)
    assert begun['reply']['ok'], 'I8: a subsequent joint trial starts from the accepted best state'
    discarded = host.tool(
        'discard_trial', {'trial_id': begun['reply']['value']['trial_id']}, plan_id=plan
    )
    assert discarded['reply']['ok'] and discarded['snapshot'] == best, (
        'I8: discarding the next trial preserves every captured '
        'bank/structure/result/optional/start/row identity of accepted joint state'
    )
