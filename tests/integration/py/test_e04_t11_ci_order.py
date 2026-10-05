"""Owner 2026-10-04: each core starts early; repair runs cannot count as full CI."""

from pathlib import Path

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
        assert core.get('permissions', {}).get('actions') == 'write', (
            'failed core jobs have permission to cancel their run'
        )
        cancels = [step for step in core['steps'] if step.get('if') == 'failure()']
        assert any('/cancel' in step.get('run', '') for step in cancels), (
            'a real failed-core step cancels the remaining CI run'
        )


def test_full_ci_consumers_run_on_every_event_and_only_skip_core_only_repairs():
    jobs = yaml.safe_load((ROOT / '.github/workflows/ci.yml').read_text())['jobs']
    public = public_profile(jobs)
    for event in ['pull_request', 'push', 'workflow_dispatch']:
        for key in ['lint', 'audit', 'notebooks', 'cli-python', 'docs', 'app', 'app-wasm']:
            assert active(jobs[key], event), (
                'full CI retains every required consumer on each supported event'
            )
            assert not active(jobs[key], event, core_only=True), (
                'explicitly requested core-only repair skips downstream consumers'
            )
        keys = ['changes', 'pin-currency', 'native', 'core']
        if not public:
            keys.extend(['native-macos', 'core-macos'])
        for key in keys:
            assert active(jobs[key], event, core_only=True), (
                'core-only repair retains both platforms and pin currency'
            )


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
