"""Seq42: a stale paired pin skipped every edi job in run 36848684856.

Owner record 62fe8986b separates pin observation from required currency. Real
local Git histories distinguish ancestry, retained object presence and equal trees.
"""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest
import yaml

from tests.system.py.test_e09_t74_ci_crysta_resolution import RemoteFixture

ROOT = Path(__file__).resolve().parents[3]


def pin_text(sha):
    return ''.join(
        f'[target.{platform}.activation.env]\nCRYSTA_SDK_TAG = "build-{sha}"\n'
        for platform in ('linux-64', 'osx-arm64')
    )


def currency_world(tmp_path, shape):
    build = RemoteFixture(tmp_path)
    shutil.copytree(ROOT / 'tools/ci', build.edi / 'tools/ci')
    # A candidate object and tag can exist without being an ancestor of main.
    build._git('checkout', '-qb', 'candidate', build.first)
    (build.sibling / 'candidate.txt').write_text('unlanded candidate bytes\n')
    build._git('add', 'candidate.txt')
    build._git('commit', '-qm', 'Candidate')
    candidate = build._git('rev-parse', 'HEAD').strip()
    build._git('checkout', '-q', 'main')
    # : a paired fixture has unlanded work, not just a branch at main.
    pin = candidate if shape == 'paired-current' else build.first
    if shape.startswith('unpaired-') and shape != 'unpaired-ancestor':
        pin = candidate
    build._git('tag', 'build-' + pin, pin)
    if shape.startswith('paired-'):
        build._git('branch', 'paired-topic', candidate)
    if shape == 'unpaired-squashed':
        tree = build._git('rev-parse', candidate + '^{tree}').strip()
        squash = build._git('commit-tree', tree, '-p', build.second, '-m', 'Landed tree').strip()
        build._git('update-ref', 'refs/heads/main', squash)
    (build.edi / 'pixi.toml').write_text(
        pin_text(pin if shape == 'unpaired-main-pin' else build.first)
    )
    for args in [
        ('init', '-q'),
        ('add', 'pixi.toml'),
        ('commit', '-qm', 'Edi main'),
        ('branch', '-M', 'main'),
    ]:
        subprocess.run(
            [
                build.git,
                '-C',
                str(build.edi),
                '-c',
                'user.name=Fixture',
                '-c',
                'user.email=fixture@example.invalid',
                *args,
            ],
            check=True,
            capture_output=True,
        )
    subprocess.run(
        [build.git, '-C', str(build.edi), 'remote', 'add', 'origin', str(build.edi)], check=True
    )
    (build.edi / 'pixi.toml').write_text(pin_text(pin))
    # Git's standard URL mapping substitutes only transport; all selection,
    # fetch, ancestry, tree and pin reads execute real production code.
    config = tmp_path / 'gitconfig'
    source = str(build.sibling if shape != 'lookup-error' else tmp_path / 'missing')
    config.write_text(
        f'[url "{source}"]\n'
        '  insteadOf = https://x-access-token:fixture-token@github.com/enhantica/crysta\n'
    )
    build.env.update(
        GIT_CONFIG_GLOBAL=str(config),
        GIT_CONFIG_NOSYSTEM='1',
        GITHUB_EVENT_NAME='pull_request',
        GITHUB_HEAD_REF='paired-topic',
        GITHUB_TOKEN='fixture-token',  # noqa: S106 — public, inert transport credential
        GITHUB_OUTPUT=str(tmp_path / 'outputs'),
    )
    return build, pin


@pytest.mark.parametrize(
    'shape',
    [
        'paired-current',
        'paired-stale',
        'unpaired-ancestor',
        'unpaired-unlanded',
        'unpaired-main-pin',
        'unpaired-squashed',
        'lookup-error',
    ],
)
def test_public_currency_boundary_and_pin_reader_have_distinct_obligations(tmp_path, shape):
    build, pin = currency_world(tmp_path, shape)
    observed = build.run('crysta-source.sh')
    assert observed.returncode == 0 and observed.stdout.strip() == pin, (
        ' seq42 changes must emit the committed pin even when freshness is red'
    )
    assert observed.stderr.count('crysta: pinned SDK build-' + pin) == 1, (
        ' seq42 changes keeps one effective-pin provenance observation'
    )
    assert (tmp_path / 'outputs').read_text() == 'sha=' + pin + '\n', (
        ' seq42 the downstream build handoff carries exactly the selected pin'
    )
    result = build.run('crysta-source.sh', '--currency')
    green = shape in {
        'paired-current',
        'paired-stale',
        'unpaired-unlanded',
        'unpaired-ancestor',
        'unpaired-main-pin',
        'unpaired-squashed',
    }
    assert (result.returncode == 0) == green, (
        f' final-green-only {shape}: intermediate rows report stale pins; '
        'unread transport refuses: ' + result.stderr
    )


def test_workflow_keeps_currency_required_without_blocking_build_selection():
    jobs = yaml.safe_load((ROOT / '.github/workflows/ci.yml').read_text())['jobs']
    currency = [job for job in jobs.values() if job.get('name') == 'pin currency']
    assert len(currency) == 1, ' seq42 currency owns one named required job'
    currency_id = next(key for key, job in jobs.items() if job is currency[0])
    runs = [step['run'] for step in currency[0]['steps'] if 'run' in step]
    assert any('crysta-source.sh --currency' in run for run in runs), (
        ' seq42 the required job must execute the real currency boundary'
    )
    assert not currency[0].get('if'), ' seq42 currency is unconditional on every CI event'
    for job in jobs.values():
        needs = job.get('needs', [])
        assert currency_id not in (needs.split() if isinstance(needs, str) else needs), (
            ' seq42 stale currency cannot skip another job through its dependencies'
        )
    changes = jobs['changes']
    assert not any('--currency' in step.get('run', '') for step in changes['steps']), (
        ' seq42 changes observes its pin without imposing the freshness gate'
    )
    assert changes['outputs']['crysta_sha'] == '${{ steps.crysta-source.outputs.sha }}', (
        ' seq42 downstream jobs must receive the pin reader output'
    )
