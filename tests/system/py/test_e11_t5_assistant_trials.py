"""Real-worker authorization, fit evidence and accepted-state preservation invariants."""

from __future__ import annotations

import importlib.util
import json
import math
import re
import shutil
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
_spec = importlib.util.spec_from_file_location(
    'e11_t5_protocol_helpers', ROOT / 'tests/integration/py/test_e11_t5_assistant_protocol.py'
)
protocol = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(protocol)
protocol_host = protocol.host


@pytest.fixture
def host(protocol_host):
    # Real optimizer setup/publication may take longer than a pure protocol reply.
    protocol_host.reply_timeout = 5
    return protocol_host


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


def settle(host, *, recover=False):
    for _ in range(8):
        result = host.command('fence', milliseconds=800)
        if result['reply']['fenced']:
            if not result['state']['active_job_id']:
                return result
            # A complete quarantined terminal can retain a recovery ID after work ends.
            retained = result.get('retention', {})
            if retained.get('quarantined') and any(
                row.get('pending') is False and isinstance(row.get('result'), dict)
                for row in retained.get('terminals', [])
            ):
                return result
            # Existing publication-failure cases recover only after actual baseline/fit
            # final owner delivery plus the FIFO fence, never merely an interrupted phase.
            jobs = result.get('worker_jobs', [])
            if (
                recover
                and jobs
                and all(row['finished'] and row['final_delivered'] for row in jobs)
            ):
                return host.command('cancel')
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
    host.provider('turn_finished', **host.binding(), status='completed')
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
    host.provider('turn_finished', **host.binding(), status='completed')
    begun = host.tool('begin_trial', {'group_id': 'workflow'}, plan_id=plan)
    assert begun['reply']['ok'], 'I8: a subsequent joint trial starts from the accepted best state'
    discarded = host.tool(
        'discard_trial', {'trial_id': begun['reply']['value']['trial_id']}, plan_id=plan
    )
    assert discarded['reply']['ok'] and discarded['snapshot'] == best, (
        'I8: discarding the next trial preserves every captured '
        'bank/structure/result/optional/start/row identity of accepted joint state'
    )


@pytest.mark.parametrize('source', ['single', 'joint'])
@pytest.mark.parametrize('candidate_target', [False, True], ids=['live', 'candidate'])
def test_all_declared_fixed_settings_refuse_free_flags_across_real_project_metadata(
    host, source, candidate_target
):
    if source == 'single':
        load_source(host, baseline=False)
        host.command('profile', name='cwl-pseudo-voigt-berar-baldinozzi')
    else:
        host.command(
            'load',
            path=str(ROOT / 'docs/user/cli/pd-neut-tof_ferrite-austenite-beer_joint/project'),
        )
        host.start()
    fixed = [path for path, row in rows(host.last).items() if not row['fittable']]
    if not fixed:
        assert rows(host.last) and all(row['fittable'] for row in rows(host.last).values()), (
            'I2/I9: an all-fittable source is recorded as a metadata control, '
            'not claimed as an exercised fixed-setting refusal'
        )
        return
    host.start()
    plan = approve(host, fixed)
    if candidate_target:
        result = host.tool('begin_trial', {'group_id': 'workflow'}, plan_id=plan)
        assert result['reply']['ok'], (
            'I8: declared fixed-setting values can be scoped on an isolated candidate'
        )
    violations = []
    for path in fixed:
        result = host.tool('set_free', {'flags': [{'path': path, 'free': True}]}, plan_id=plan)
        if result['reply']['ok']:
            violations.append(path)
    assert not violations, (
        'I2/I9: every independently declared nonfittable setting refuses '
        'executable freedom across CW/TOF and live/candidate routes'
    )


@pytest.mark.parametrize('source', ['single', 'joint'])
def test_iteration_objective_is_the_original_weighted_residual_not_reduced_quality(host, source):
    if source == 'single':
        load_source(host)
        paths = useful_paths(host)
    else:
        result = host.command(
            'load',
            path=str(ROOT / 'docs/user/cli/pd-neut-tof_ferrite-austenite-beer_joint/project'),
        )
        paths = [path for path in rows(result) if path.endswith(('.scale', '.cell.length_a'))]
        host.command('manual_fit', free_paths=[path for path in paths if path.endswith('.scale')])
        host.start()
    plan = approve(host, paths)
    trial = candidate(host, plan, paths)
    settled = settle(host)
    progress = [event for event in settled['events'] if event.get('type') == 'job_progress']
    assert progress, (
        'I8/I13: a genuinely moving single/joint optimizer emits measured iteration evidence'
    )
    result = host.tool('evaluate_trial', {'trial_id': trial}, plan_id=plan)
    assert result['reply']['ok'] and result['reply']['value']['accepted'], (
        'I8: the converged physical witness is adopted before independently '
        'measuring its original weighted objective'
    )
    measured = host.command('objective')
    assert progress[-1]['objective'] == pytest.approx(
        measured['reply']['objective'], rel=1e-7, abs=1e-7
    ), (
        'I8/I13: a field labelled objective carries the independently calculated '
        'weighted residual on the original population, not reduced chi-square'
    )


@pytest.mark.parametrize('replacement', [False, True], ids=['no-candidate', 'new-candidate'])
def test_retired_candidate_request_cannot_retarget_distinct_late_mutation(host, replacement):
    load_source(host, baseline=False)
    paths = useful_paths(host)
    plan = approve(host, paths)
    begun = host.tool('begin_trial', {'group_id': 'workflow'}, plan_id=plan)
    assert begun['reply']['ok'], 'I8: the original isolated candidate is genuinely admitted'
    old_binding = host.binding()
    old_trial = begun['reply']['value']['trial_id']
    discarded = host.tool('discard_trial', {'trial_id': old_trial}, plan_id=plan)
    assert discarded['reply']['ok'], 'I8: the original candidate target has been retired'
    if replacement:
        # A completed provider response settles its tools before a fresh request may target
        # a replacement candidate. Keep the captured old binding for the late-call escape.
        host.provider('turn_finished', **host.binding(), status='completed')
        begun = host.tool('begin_trial', {'group_id': 'workflow'}, plan_id=plan)
        assert begun['reply']['ok'] and begun['reply']['value']['trial_id'] != old_trial, (
            'I8: a distinct current candidate is admitted through the current request scope'
        )
    original = host.last['snapshot']
    path = next(path for path in paths if path.endswith('.scale'))
    result = host.tool(
        'set_parameters',
        {'values': [{'path': path, 'value': 17.31}]},
        **old_binding,
        call_id='late-former-candidate',
        plan_id=plan,
    )
    assert not result['reply']['ok'], (
        'I2/I7/I8: a distinct delayed call from a retired candidate request cannot '
        'retarget the accepted live project or a replacement candidate'
    )
    assert result['snapshot'] == original, (
        'I4/I7: rejecting a retired candidate call preserves exact accepted '
        'state and row identities'
    )


def nested_objects(value):
    if isinstance(value, dict):
        yield value
        for child in value.values():
            yield from nested_objects(child)
    elif isinstance(value, list):
        for child in value:
            yield from nested_objects(child)


def prepared_native_case(host, tmp_path, mode, iterations):
    source = (
        'pd-neut-cwl_cosio-d20_start-1'
        if mode == 'single'
        else 'pd-neut-tof_ferrite-austenite-beer_joint'
    )
    target = tmp_path / 'native-source'
    shutil.copytree(ROOT / 'docs/user/cli' / source / 'project', target)
    analysis = target / 'analysis/analysis.edi'
    text = analysis.read_text()
    if '_minimizer.max_iterations' in text:
        text = re.sub(
            r'(?m)^_minimizer.max_iterations\s+[^\n]+',
            f'_minimizer.max_iterations {iterations}',
            text,
        )
    else:
        text += f'\n_minimizer.max_iterations {iterations}\n'
    analysis.write_text(text)
    loaded = host.command('load', path=str(target))
    paths = useful_paths(host)
    assert loaded['context']['project']['fitting_mode'] == mode, (
        'I8/F4: the actual serialized scientific fixture declares its single/joint mode'
    )
    assert paths, 'I8/F4: the native qualification has a real nonempty useful free group'
    return target, paths


def reload_exact_free_group(host, target, paths):
    host.command('load', path=str(target))
    # One real setup edit avoids serializing the entire joint project per free flag.
    host.command('prepare_free_group', paths=paths)
    host.start()


@pytest.mark.parametrize('mode', ['single', 'joint'])
@pytest.mark.parametrize(('iterations', 'expected_status'), [(1, 'max_iter'), (1000, 'done')])
def test_independent_native_workflow_reaches_status_trigger(
    host, tmp_path, mode, iterations, expected_status
):
    # Separate real native qualification from controller projection to bound each end-to-end case.
    _, paths = prepared_native_case(host, tmp_path, mode, iterations)
    native = host.command('manual_fit', free_paths=paths)['reply']
    assert native['status'] == expected_status, (
        'F4 fixture qualification: direct real FitJob reaches the declared native status'
    )
    assert native['converged'] == (expected_status == 'done'), (
        'F4 fixture qualification: actual native convergence distinguishes DONE from MAX_ITER'
    )


@pytest.mark.parametrize('mode', ['single', 'joint'])
@pytest.mark.parametrize(('iterations', 'expected_status'), [(1, 'max_iter'), (1000, 'done')])
def test_genuine_native_status_survives_scientific_terminal_and_provider_continuation(
    host, tmp_path, mode, iterations, expected_status
):
    _, paths = prepared_native_case(host, tmp_path, mode, iterations)
    host.command('prepare_free_group', paths=paths)
    host.start()
    before = host.last['snapshot']
    plan = approve(host, paths, iterations=iterations)
    candidate(host, plan, paths)
    job = host.last['state']['active_job_id']
    old_request = host.binding()['request_id']
    host.provider('turn_finished', **host.binding(), status='completed')
    settled = settle(host)
    terminal = [
        event
        for event in settled['events']
        if event.get('type') == 'job_finished' and event.get('job_id') == job
    ]
    assert len(terminal) == 1, (
        'I8/F4: actual optimizer settlement emits exactly one correlated full terminal'
    )
    status_rows = [
        obj
        for obj in nested_objects(terminal)
        if str(obj.get('status', '')).lower()
        in {'done', 'max_iter', 'no_step', 'cancelled', 'error', 'superseded'}
    ]
    assert status_rows and all(
        str(obj['status']).lower() == expected_status for obj in status_rows
    ), 'I8/F4: terminal projection preserves genuine DONE/MAX_ITER'
    convergence = [obj['converged'] for obj in nested_objects(terminal) if 'converged' in obj]
    assert convergence and all(value == (expected_status == 'done') for value in convergence), (
        'I8/F4: full terminal preserves independently observed native convergence'
    )
    assert settled['snapshot'] == before, (
        'I8/F4: even a genuine DONE terminal remains isolated until explicit evaluation/adoption'
    )
    latest = settled['requests'][-1]
    assert latest['request_id'] != old_request, (
        'I13/F4: settled actual work resumes its provider continuation with a fresh request'
    )
    results = [
        obj
        for obj in nested_objects(latest['history'])
        if obj.get('type') == 'tool_result' and job in json.dumps(obj, ensure_ascii=False)
    ]
    assert any(
        str(child.get('status', '')).lower() == expected_status
        for result in results
        for child in nested_objects(result)
    ), 'I8/I13/F4: continuation retains the full correlated scientific terminal'
    later = host.command('fence', milliseconds=800)
    assert (
        sum(
            event.get('type') == 'job_finished' and event.get('job_id') == job
            for event in later['events']
        )
        == 1
    ), 'I10/F4: fencing late delivery cannot duplicate a scientific terminal'


@pytest.mark.parametrize('mode', ['single', 'joint'])
def test_real_zero_free_error_or_preflight_refusal_never_becomes_fit_success(host, tmp_path, mode):
    target, paths = prepared_native_case(host, tmp_path, mode, 1000)
    native = host.command('manual_fit', free_paths=[])['reply']
    assert native['status'] == 'error', (
        'F4 fixture qualification: actual zero-free native work reports ERROR'
    )
    reload_exact_free_group(host, target, [])
    before = host.last['snapshot']
    plan = approve(host, paths)
    begun = host.tool('begin_trial', {'group_id': 'workflow'}, plan_id=plan)
    assert begun['reply']['ok'], (
        'I8/F4: the actual zero-free candidate is admitted before fit preflight'
    )
    trial = begun['reply']['value']['trial_id']
    # begin_trial intentionally applies the approved group; explicitly clear it on the candidate.
    cleared = host.tool(
        'set_free', {'flags': [{'path': path, 'free': False} for path in paths]}, plan_id=plan
    )
    assert cleared['reply']['ok'], 'I8/F4: real approved candidate flags reach the zero-free path'
    fitted = host.tool('fit_trial', {'trial_id': trial}, plan_id=plan)
    if fitted['reply']['ok']:
        job = fitted['state']['active_job_id']
        settled = settle(host)
        terminals = [
            event
            for event in settled['events']
            if event.get('type') == 'job_finished' and event.get('job_id') == job
        ]
        assert len(terminals) == 1, (
            'I8/F4: an admitted actual failing FitJob still settles exactly once'
        )
        assert any(
            str(obj.get('status', '')).lower() == 'error' for obj in nested_objects(terminals)
        ), 'I8/F4: actual failing scientific work cannot be projected as successful DONE/NO_STEP'
    else:
        assert not fitted['state']['active_job_id'], (
            'I8/F4: a legal synchronous scientific preflight refusal does not invent an async job'
        )
    assert host.last['snapshot'] == before, (
        'I8/F4: native-error/preflight preserves the exact captured accepted state'
    )


@pytest.mark.parametrize('elapsed_budget', [50, 5000], ids=['expired-in-queue', 'useful-budget'])
def test_approved_elapsed_budget_includes_time_waiting_on_actual_worker(host, elapsed_budget):
    load_source(host)
    paths = useful_paths(host)
    before = host.last['snapshot']
    host.command('clock', steady=False)
    plan = approve(host, paths, elapsed=elapsed_budget)
    armed = host.command('queue_hold')
    assert armed['reply']['armed'], 'I10/F7: the actual worker queue hold is established'
    begun = host.tool('begin_trial', {'group_id': 'workflow'}, plan_id=plan)
    assert begun['reply']['ok'], 'I8/F7: queue witness starts an actual isolated candidate'
    trial = begun['reply']['value']['trial_id']
    free = host.tool(
        'set_free', {'flags': [{'path': path, 'free': True} for path in paths]}, plan_id=plan
    )
    assert free['reply']['ok'], 'I8/F7: approved real flags are prepared before timed admission'
    host.command('clock', steady=True)
    started = host.tool('fit_trial', {'trial_id': trial}, plan_id=plan)
    assert started['reply']['ok'], 'I10/F7: actual fit enters the held worker queue'
    job_id = host.last['state']['active_job_id']
    assert host.last['state']['active_job_id'], (
        'I10/F7: the real scientific job was admitted before the waiting deadline exercise'
    )
    try:
        waiting = host.command('queue_elapsed', milliseconds=100)
        receipt = waiting['reply']
        assert receipt['elapsed_ms'] >= 100, (
            'I10/F7: actual steady elapsed time exceeds the approved short budget before release'
        )
        assert receipt['submitted'] > 0, (
            'I10/F7: a real later job is submitted behind the held actual worker delivery'
        )
        assert receipt['started'] == 0, (
            'I10/F7: scientific work has not started during its admitted queue wait'
        )
    finally:
        host.command('queue_release')
    settled = settle(host)
    assert not settled['state']['active_job_id'], (
        'I10/F7: admitted queued work settles once after the actual queue is released'
    )
    assert settled['snapshot'] == before, (
        'I8/F7: queued candidate work never publishes over the captured accepted state by itself'
    )
    evaluated = host.tool('evaluate_trial', {'trial_id': trial}, plan_id=plan)
    if elapsed_budget == 50:
        terminals = [
            event
            for event in settled['events']
            if event.get('type') == 'job_finished' and event.get('job_id') == job_id
        ]
        assert len(terminals) == 1, (
            'I10/F7: already-expired admitted work has exactly one correlated settled terminal'
        )

        def terminal_statuses(value):
            found = []
            if isinstance(value, dict):
                status = str(value.get('status', '')).lower()
                if status in {'done', 'max_iter', 'no_step', 'cancelled', 'error', 'superseded'}:
                    found.append(status)
                for child in value.values():
                    found.extend(terminal_statuses(child))
            elif isinstance(value, list):
                for child in value:
                    found.extend(terminal_statuses(child))
            return found

        statuses = terminal_statuses(terminals)
        assert statuses and all(status in {'cancelled', 'error'} for status in statuses), (
            'I10/F7: expired-before-start work cannot report a successful scientific optimization'
        )
        assert not evaluated['reply']['ok'] or not evaluated['reply']['value'].get(
            'accepted', False
        ), 'I10/F7: expired-before-start work cannot be adopted as a successful improvement'
        assert evaluated['snapshot'] == before, (
            'I8/F7: expired queued work preserves the exact original accepted state'
        )
    else:
        assert evaluated['reply']['ok'] and evaluated['reply']['value']['accepted'], (
            'I8/F7: an otherwise-identical real queued moving fit is useful with sufficient budget'
        )
        assert evaluated['snapshot'] != before, (
            'I8/F7: the positive larger-budget witness actually moves and adopts fitted state'
        )
    assert evaluated['owner_clock_violations'] == 0, (
        'I10/F7: real elapsed checks preserve the clock dependency owner-thread contract'
    )
