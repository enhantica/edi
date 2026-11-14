"""Restore/save cache grouping follows committed inputs despite local Pixi metadata writes."""

import hashlib
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
PIN = 'a7' * 20


def git(root, *args):
    return subprocess.run(['git', *args], cwd=root, check=True, capture_output=True, text=True)


@pytest.fixture
def checkout(tmp_path):
    for name in ('compiler_cache.py', 'crysta_sdk.py'):
        shutil.copyfile(ROOT / 'tools/ci' / name, tmp_path / name)
    (tmp_path / 'pixi.toml').write_text('[activation.env]\nCRYSTA_COMMIT="' + PIN + '"\n')
    (tmp_path / 'pixi.lock').write_bytes(b'independent committed lock bytes\n')
    git(tmp_path, 'init')
    git(tmp_path, 'add', 'pixi.toml', 'pixi.lock')
    git(
        tmp_path,
        '-c',
        'user.name=Cache contract',
        '-c',
        'user.email=cache@example.invalid',
        'commit',
        '-m',
        'Independent cache identity',
    )
    return tmp_path


def configure(root, platform='Linux'):
    environment, output = root / 'environment', root / 'output'
    for path in (environment, output):
        path.write_text('retained sentinel\n')
    result = subprocess.run(
        [sys.executable, str(root / 'compiler_cache.py'), '2G'],
        cwd=root,
        env={
            **os.environ,
            'GITHUB_ENV': str(environment),
            'GITHUB_OUTPUT': str(output),
            'RUNNER_OS': platform,
            'RUNNER_ARCH': 'X64',
        },
        capture_output=True,
        text=True,
        timeout=5,
        check=False,
    )
    return result, environment.read_text(), output.read_text()


@pytest.mark.parametrize('platform', ['Linux', 'macOS', 'Windows'])
def test_working_lock_rewrite_cannot_change_the_restore_save_family(checkout, platform):
    result, environment, output = configure(checkout, platform)
    assert result.returncode == 0, result.stderr
    digest = hashlib.sha256((checkout / 'pixi.lock').read_bytes()).hexdigest()[:12]
    assert f'prefix={platform}-X64-crysta-{PIN[:12]}-lock-{digest}-\n' in output
    assert 'CCACHE_COMPILERCHECK=content\n' in environment
    (checkout / 'pixi.lock').write_bytes(b'locally realized editable package metadata\n')
    repeated, _, saved = configure(checkout, platform)
    assert repeated.returncode == 0, repeated.stderr
    assert saved == output, 'Restore/save must retain one committed lock identity'
    git(checkout, 'add', 'pixi.lock')
    git(
        checkout,
        '-c',
        'user.name=Cache contract',
        '-c',
        'user.email=cache@example.invalid',
        'commit',
        '-m',
        'Change the actual lock',
    )
    changed, _, committed = configure(checkout, platform)
    assert changed.returncode == 0, changed.stderr
    assert committed != output, 'A genuine committed lock change selects a new family'


@pytest.mark.parametrize('damage', ['no-head', 'no-committed-lock', 'no-committed-pin'])
def test_unproved_committed_inputs_refuse_before_mutating_ci_files(checkout, damage):
    if damage == 'no-head':
        git(checkout, 'update-ref', '-d', 'HEAD')
    else:
        name = 'pixi.lock' if damage == 'no-committed-lock' else 'pixi.toml'
        git(checkout, 'rm', '--cached', name)
        git(
            checkout,
            '-c',
            'user.name=Cache contract',
            '-c',
            'user.email=cache@example.invalid',
            'commit',
            '-m',
            'Remove the declared committed input',
        )
        assert (checkout / name).is_file(), 'Working files cannot supply missing committed proof'
    result, environment, output = configure(checkout)
    assert result.returncode != 0, 'Unproved cache identity must refuse'
    assert environment == output == 'retained sentinel\n', 'No partial cache settings on refusal'
