"""Owner 2026-10-04: each core starts early; repair runs cannot count as full CI."""

from pathlib import Path

import yaml

from tests.fixtures.e09_t75_workflow import active

ROOT = Path(__file__).resolve().parents[3]


def test_platform_cores_wait_only_for_their_own_native_build():
    jobs = yaml.safe_load((ROOT / '.github/workflows/ci.yml').read_text())['jobs']
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
        assert jobs[core].get('permissions', {}).get('actions') == 'write', (
            'failed core jobs have permission to cancel their run'
        )
        cancels = [step for step in jobs[core]['steps'] if step.get('if') == 'failure()']
        assert any('/cancel' in step.get('run', '') for step in cancels), (
            'a real failed-core step cancels the remaining CI run'
        )


def test_full_ci_consumers_run_on_every_event_and_only_skip_core_only_repairs():
    jobs = yaml.safe_load((ROOT / '.github/workflows/ci.yml').read_text())['jobs']
    for event in ['pull_request', 'push', 'workflow_dispatch']:
        for key in ['lint', 'audit', 'notebooks', 'cli-python', 'docs', 'app', 'app-wasm']:
            assert active(jobs[key], event), (
                'full CI retains every required consumer on each supported event'
            )
            assert not active(jobs[key], event, core_only=True), (
                'explicitly requested core-only repair skips downstream consumers'
            )
        for key in ['changes', 'pin-currency', 'native', 'native-macos', 'core', 'core-macos']:
            assert active(jobs[key], event, core_only=True), (
                'core-only repair retains both platforms and pin currency'
            )


def test_pages_stays_disabled_and_webapp_keeps_default_retention():
    jobs = yaml.safe_load((ROOT / '.github/workflows/ci.yml').read_text())['jobs']
    assert jobs['pages'].get('if') is False and jobs['pages']['steps'], (
        'retain Pages steps while disabling the job on every event'
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
        'the disabled Pages job cannot block another CI job'
    )
