# SPDX-License-Identifier: BSD-3-Clause
"""Exercise the CI source boundary with GitHub workflow definitions and synthetic files."""

import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[3]


def workflow(relative):
    return yaml.safe_load((ROOT / '.github' / relative).read_text(encoding='utf-8'))


@pytest.mark.parametrize('name', ['crysta-sdk', 'ci', 'pages', 'coverage', 'installers'])
def test_sdk_archive_handoff_carries_no_source_archive(name):
    jobs = workflow(f'workflows/{name}.yml')['jobs']
    references = []
    for job_id, job in jobs.items():
        for step in job.get('steps', []):
            command = step.get('run', '')
            if (
                '.tar' in command and 'crysta-src' in command
            ) or 'crysta_source_archive.py' in command:
                references.append(f'{job_id}/{step.get("name", step.get("id", "run"))}')
    assert not references, f'CI cannot create or request a crysta source archive: {references}'


def test_cold_and_warm_sdk_handoffs_never_implicitly_save_the_archive_directory():
    steps = workflow('workflows/crysta-sdk.yml')['jobs']['build']['steps']
    combined = [
        step
        for step in steps
        if step.get('uses', '').startswith('actions/cache@')
        and 'crysta-sdk-archives' in str(step.get('with', {}).get('path', ''))
    ]
    assert not combined, 'SDK cache saves must run explicitly after checking the files'


@pytest.mark.parametrize(
    ('definition', 'old_key'),
    [
        ('workflows/crysta-sdk.yml', 'crysta-objects-v1-'),
        ('workflows/ci.yml', 'ccache-core-'),
        ('workflows/ci.yml', 'ccache-app-'),
        ('workflows/ci.yml', 'ccache-app-windows-'),
        ('workflows/installers.yml', 'ccache-installer-'),
        ('actions/wasm-cache/action.yml', 'ccache-wasm-'),
    ],
)
def test_compiler_cache_can_never_restore_entries_from_before_output_checks(definition, old_key):
    data = workflow(definition)
    steps = data.get('runs', {}).get('steps', []) + [
        step for job in data.get('jobs', {}).values() for step in job.get('steps', [])
    ]
    for step in steps:
        if not step.get('uses', '').startswith('actions/cache'):
            continue
        inputs = step.get('with', {})
        keys = [str(inputs.get('key', '')), *str(inputs.get('restore-keys', '')).splitlines()]
        assert all(not key.strip().startswith(old_key) for key in keys), (
            f'{definition} must never restore a compiler cache from the prior {old_key} family'
        )


def test_unavailable_source_list_prevents_the_runner_shell_executing_a_step(tmp_path):
    step = tmp_path / 'step.sh'
    side_effect = tmp_path / 'step-ran'
    step.write_text('echo "raw step output"\ntouch "$SIDE_EFFECT"\n', encoding='utf-8')
    shell = ROOT / 'tools/ci/public_log.py'
    assert shell.is_file(), 'The runner must have its source-filtering shell'
    env = {key: value for key, value in os.environ.items() if not key.startswith('CRYSTA_')}
    env.update(
        GITHUB_ACTIONS='true',
        GITHUB_WORKSPACE=str(tmp_path),
        RUNNER_TEMP=str(tmp_path),
        SIDE_EFFECT=str(side_effect),
    )
    result = subprocess.run(
        [sys.executable, str(shell), str(step)],
        cwd=tmp_path,
        env=env,
        capture_output=True,
        text=True,
        timeout=10,
        check=False,
    )
    assert result.returncode != 0 and not side_effect.exists(), (
        'A runner missing its source line list must refuse before executing the step'
    )
    assert 'raw step output' not in result.stdout + result.stderr, (
        'A runner missing its source line list must not forward a child line'
    )


@pytest.mark.parametrize(
    'mutation', ['publisher', 'combined-cache', 'implicit-pixi-cache', 'shell-override']
)
def test_policy_refuses_a_source_job_with_an_unchecked_output_path(tmp_path, mutation):
    shutil.copytree(ROOT / '.github', tmp_path / '.github')
    shutil.copytree(ROOT / 'tools/ci', tmp_path / 'tools/ci')
    sandbox_bin = tmp_path / 'bin'
    sandbox_bin.mkdir()
    pixi = sandbox_bin / 'pixi'
    pixi.write_text('#!/bin/bash\nexit 0\n', encoding='utf-8')
    pixi.chmod(0o755)
    env = {**os.environ, 'PATH': f'{sandbox_bin}{os.pathsep}{os.environ["PATH"]}'}
    command = ['bash', 'tools/ci/lint.sh', 'policy']

    def run_policy():
        return subprocess.run(
            command, cwd=tmp_path, env=env, capture_output=True, text=True, timeout=10, check=False
        )

    clean = run_policy()
    workflow_path = tmp_path / '.github/workflows/crysta-sdk.yml'
    content = yaml.safe_load(workflow_path.read_text(encoding='utf-8'))
    steps = content['jobs']['build']['steps']
    replacements = {
        'publisher': {
            'uses': 'actions/upload-artifact@v4',
            'if': '${{ failure() }}',
            'with': {'name': 'unchecked', 'path': '${{ runner.temp }}/crysta/src'},
        },
        'combined-cache': {
            'uses': 'actions/cache@v4',
            'with': {'key': 'unchecked-objects', 'path': '${{ runner.temp }}/crysta/src'},
        },
        'implicit-pixi-cache': {
            'uses': 'prefix-dev/setup-pixi@v0.9.3',
            'with': {'manifest-path': '${{ runner.temp }}/crysta/pixi.toml'},
        },
        'shell-override': {'run': 'cat "$CRYSTA_SRC/src/probe.cpp"', 'shell': 'bash'},
    }
    steps.append({'name': f'Planted {mutation}', **replacements[mutation]})
    workflow_path.write_text(yaml.safe_dump(content, sort_keys=False), encoding='utf-8')
    changed = run_policy()
    assert clean.returncode == 0, 'The unmodified workflows pass the source-storage policy'
    assert changed.returncode != 0, f'The source-storage policy must detect the planted {mutation}'
