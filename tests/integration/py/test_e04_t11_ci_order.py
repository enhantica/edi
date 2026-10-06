"""Owner 2026-10-04: each core starts early; repair runs cannot count as full CI."""

import copy
from pathlib import Path

import pytest
import yaml

from tests.fixtures.e09_t75_workflow import active
from tests.integration.py.test_e09_t75_native_workflow import (
    public_build_boundary,
    public_profile,
)

ROOT = Path(__file__).resolve().parents[3]


def test_platform_cores_wait_only_for_their_own_native_build():
    jobs = yaml.safe_load((ROOT / '.github/workflows/ci.yml').read_text())['jobs']
    if public_profile(jobs):
        for sdk in ('linux-64', 'osx-arm64'):
            public_build_boundary(jobs, 'core', sdk)
        cores = [jobs['core']]
    else:
        cores = []
        for core, native, sdk in [
            ('core', 'native', 'linux-64'),
            ('core-macos', 'native-macos', 'osx-arm64'),
        ]:
            assert set(jobs[core]['needs']) == {'changes', native}, (
                'each platform core starts when its own native build finishes'
            )
            assert [leg['sdk'] for leg in jobs[core]['strategy']['matrix']['include']] == [sdk], (
                'each early core runs exactly its prescribed platform'
            )
            cores.append(jobs[core])
    for core in cores:
        assert_core_failure_reporting(core)


def test_full_ci_consumers_run_on_every_event_and_only_skip_core_only_repairs():
    jobs = yaml.safe_load((ROOT / '.github/workflows/ci.yml').read_text())['jobs']
    public = public_profile(jobs)
    for event in ['pull_request', 'push', 'workflow_dispatch']:
        for key in ['lint', 'audit', 'notebooks', 'cli-python', 'docs', 'app', 'app-wasm']:
            assert active(
                jobs[key],
                event,
                states={'changes': 'success', 'core': 'success', 'native': 'success'},
            ), 'full CI retains every required consumer on each supported event'
            assert not active(
                jobs[key],
                event,
                states={'changes': 'success', 'core': 'success', 'native': 'success'},
                core_only=True,
            ), 'explicitly requested core-only repair skips downstream consumers'
        keys = ['changes', 'pin-currency', 'native', 'core']
        if not public:
            keys.extend(['native-macos', 'core-macos'])
        for key in keys:
            assert active(
                jobs[key],
                event,
                states={'changes': 'success', 'core': 'success', 'native': 'success'},
                core_only=True,
            ), 'core-only repair retains both platforms and pin currency'


def test_pages_visibility_and_webapp_default_retention_follow_the_public_profile():
    jobs = yaml.safe_load((ROOT / '.github/workflows/ci.yml').read_text())['jobs']
    if public_profile(jobs):
        pages = yaml.safe_load((ROOT / '.github/workflows/pages.yml').read_text())['jobs']
        assert set(pages) == {'build', 'deploy'} and all(job['steps'] for job in pages.values()), (
            'public Pages retains both real build and deployment jobs'
        )
        for event in ('push', 'workflow_dispatch'):
            assert active(pages['build'], event), 'public Pages builds on each site event'
            assert active(pages['deploy'], event), 'public Pages deploys on each site event'
            assert not active(pages['deploy'], event, repository_private=True), (
                'the publicly visible site deploys only from a public repository'
            )
        assert not active(pages['build'], 'pull_request', fork=True), (
            'Pages private SDK acquisition retains the fork credential boundary'
        )
    else:
        pages = {'pages': jobs['pages']}
        assert all(job.get('if') is False and job['steps'] for job in pages.values()), (
            'private CI retains Pages steps with deployment explicitly disabled'
        )
    uploads = [
        step
        for step in jobs['app-wasm']['steps']
        if step.get('with', {}).get('name') == 'edi-webapp'
    ]
    assert len(uploads) == 1 and 'retention-days' not in uploads[0]['with'], (
        'every full run uploads the webapp with repository default retention'
    )
    assert not any('pages' in job.get('needs', []) for job in jobs.values()), (
        'site publication must not block another CI job'
    )


def assert_core_failure_reporting(core):
    # Before: the first red core cancelled its entire run. After owner 2026-10-06:
    # preserve the red core result while later jobs report their own failures.
    assert core.get('permissions', {}).get('actions') != 'write', (
        'core failure reporting must not retain run-cancellation authority'
    )
    assert not core.get('continue-on-error') and core['strategy']['fail-fast'] is False, (
        'a red core must remain a red run while both platform legs finish'
    )
    assert not any('/cancel' in step.get('run', '') for step in core['steps']), (
        'a core failure must leave the remaining jobs available to report failures'
    )
    required = [s for s in core['steps'] if 'pixi run group-quick' in s.get('run', '')]
    assert len(required) == 1 and 'pixi run group-full' in required[0]['run'], (
        'the red-run control must reach both real event-selected core test groups'
    )
    assert 'if' not in required[0] and not any(
        step.get('continue-on-error') for step in core['steps']
    ), 'core commands must propagate failures rather than convert or skip a red result'


@pytest.mark.parametrize('event', ['pull_request', 'push', 'workflow_dispatch'])
@pytest.mark.parametrize('upstream', ['success', 'failure', 'skipped'])
def test_later_jobs_report_after_core_and_native_results(event, upstream):
    jobs = yaml.safe_load((ROOT / '.github/workflows/ci.yml').read_text())['jobs']
    for name in ['audit', 'notebooks', 'cli-python', 'docs', 'app', 'app-wasm']:
        states = {'changes': 'success', 'core': upstream}
        if name == 'notebooks':
            states['native'] = upstream
        assert active(jobs[name], event, states=states), (
            'owner failure reporting requires every later job after a successful source resolution'
        )
        assert not jobs[name].get('continue-on-error'), (
            'later reporting must retain each job failure in the overall run conclusion'
        )


@pytest.mark.parametrize('event', ['pull_request', 'push', 'workflow_dispatch'])
@pytest.mark.parametrize('block', ['changes-failed', 'changes-skipped', 'cancelled', 'core-only'])
def test_reporting_keeps_source_cancellation_and_repair_boundaries(event, block):
    jobs = yaml.safe_load((ROOT / '.github/workflows/ci.yml').read_text())['jobs']
    states = {'changes': 'success', 'core': 'failure', 'native': 'failure'}
    if block.startswith('changes-'):
        states['changes'] = 'failure' if block == 'changes-failed' else 'skipped'
    for name in ['audit', 'notebooks', 'cli-python', 'docs', 'app', 'app-wasm']:
        assert not active(
            jobs[name],
            event,
            states=states,
            cancelled=block == 'cancelled',
            core_only=block == 'core-only',
        ), (
            'later reporting must refuse cancelled runs, failed source resolution '
            'and core-only repair'
        )
    assert all(
        not active(jobs[name], 'pull_request', states=states, fork=True)
        for name in ['audit', 'notebooks', 'cli-python', 'docs', 'app']
    ), 'later reporting must retain the private SDK fork credential boundary'


def test_newer_heads_still_cancel_superseded_runs():
    workflow = yaml.safe_load((ROOT / '.github/workflows/ci.yml').read_text())
    assert workflow['concurrency'] == {
        'group': '${{ github.workflow }}-${{ github.event.pull_request.number || github.ref }}',
        'cancel-in-progress': True,
    }, 'only a newer run on the same PR or ref cancels the superseded head'


@pytest.mark.parametrize(
    'escape', ['cancel', 'permission', 'optional-job', 'optional-step', 'fail-fast']
)
def test_red_core_reporting_refuses_success_conversion_and_run_cancel_escapes(escape):
    core = yaml.safe_load((ROOT / '.github/workflows/ci.yml').read_text())['jobs']['core']
    assert_core_failure_reporting(core)
    damaged = copy.deepcopy(core)
    if escape == 'cancel':
        damaged['steps'].append({'if': 'failure()', 'run': 'gh api run/cancel'})
    elif escape == 'permission':
        damaged['permissions'] = {'actions': 'write'}
    elif escape == 'optional-job':
        damaged['continue-on-error'] = True
    elif escape == 'optional-step':
        damaged['steps'][0]['continue-on-error'] = True
    else:
        damaged['strategy']['fail-fast'] = True
    with pytest.raises(AssertionError):
        assert_core_failure_reporting(damaged)


@pytest.mark.parametrize('state', ['success', 'failure', 'skipped'])
def test_condition_observer_distinguishes_implicit_success_and_reporting(state):
    preceding = {'core': state}
    assert all(
        active({'if': value}, 'push', states=preceding) == (state == 'success')
        for value in ('true', True)
    ), (
        'Actions implicit success must prevent a plain condition from concealing '
        'a failed dependency'
    )
    assert active({'if': '!cancelled()'}, 'push', states=preceding), (
        'an explicit status function allows the owner later-job reporting contract'
    )
    assert active({'if': 'failure()'}, 'push', states=preceding) == (state == 'failure'), (
        'the failure observer must use the preceding job result'
    )
    assert not active({'if': '!cancelled()'}, 'push', states=preceding, cancelled=True), (
        'the cancellation observer must use the actual workflow cancellation state'
    )
    with pytest.raises(AssertionError, match='must be resolved'):
        active({'if': "needs.unknown.result == 'success'"}, 'push', states=preceding)
    with pytest.raises(AssertionError, match='must be resolved'):
        active({'if': 'unknown()'}, 'push', states=preceding)
