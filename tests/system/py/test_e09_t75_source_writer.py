"""Review17 F3: a source checkout can be cleaned during an ordinary reader's build.

Real local Git supplies the pinned source; the existing qualified download fixture
supplies the SDK. No diagnostic SDK selector may bypass source acquisition.
"""

from __future__ import annotations

import subprocess
import tomllib

import pytest

from tests.integration.py import test_e09_t75_sdk_consumer as sdk
from tests.system.py.test_e09_t74_ci_crysta_resolution import RemoteFixture


def source_world(base, monkeypatch):
    history = base / 'history'
    history.mkdir(parents=True)
    remote = RemoteFixture(history)
    monkeypatch.setattr(sdk, 'SHA', remote.first)
    workspace = base / 'caller'
    workspace.mkdir()
    env, repo, _ = sdk.consumer(workspace, platform='linux-64', download=True, prepare_only=True)
    # Restore native Git through its standard transport mapping, not synthetic
    # checkout effects. Keep the retained, narrowed download command substitute.
    (workspace / 'bin/git').unlink()
    config = base / 'gitconfig'
    config.write_text(
        f'[url "{remote.sibling}"]\n'
        ' insteadOf = https://x-access-token:fixture-token@github.com/enhantica/crysta\n'
    )
    env.update(
        GIT_CONFIG_GLOBAL=str(config),
        GIT_CONFIG_NOSYSTEM='1',
        GITHUB_TOKEN='fixture-token',  # noqa: S106 — inert local transport credential
        EDI_CORE_BUILD_LOCK_WAIT_S='0',
    )
    env.pop('PYTEST_XDIST_WORKER', None)
    prefix = repo / 'build/crysta-prefix'
    prefix.mkdir(parents=True)
    (prefix / '.crysta-sha').write_text(remote.first + '\n')
    source = repo / 'build/crysta-src'
    subprocess.run([remote.git, 'clone', '-q', str(remote.sibling), str(source)], check=True)
    (source / 'CRYSTA_SOURCE_SHA').write_text(remote.second + '\n')
    (source / 'untracked-reader').write_text('owned in-progress source\n')
    (repo / 'CMakeLists.txt').write_text('project(fixture)\n')
    return remote, env, repo, source


@pytest.mark.parametrize('caller', ['direct-source', 'sdk-task', 'core'])
def test_non_diagnostic_source_writers_reach_the_checkout_and_preserve_a_holder(
    tmp_path, monkeypatch, caller
):
    if caller == 'sdk-task':
        task = tomllib.loads((sdk.ROOT / 'pixi.toml').read_text())['tasks']['crysta-sdk']
        command = task if isinstance(task, str) else task['cmd']
    else:
        command = 'bash tools/ci/' + (
            'crysta-src.sh' if caller == 'direct-source' else 'core-build.sh'
        )
    for held in (False, True):
        remote, env, repo, source = source_world(tmp_path / str(held), monkeypatch)
        assert 'CRYSTA_SDK_DIR' not in env, (
            ' review17 F3 the source route must not take the diagnostic early return'
        )
        if held:
            (repo / 'build/.core-build.lock.d').mkdir()
        result = subprocess.run(
            ['bash', '-eu', '-c', command],
            cwd=repo,
            env=env,
            text=True,
            capture_output=True,
            timeout=3,
            check=False,
        )
        head = subprocess.check_output(
            [remote.git, '-C', str(source), 'rev-parse', 'HEAD'], text=True
        ).strip()
        if held:
            assert result.returncode != 0, (
                ' review17 F3 a held producer refuses another source writer'
            )
            assert head == remote.second, ' review17 F3 refusal must preserve the held source HEAD'
            assert (source / 'untracked-reader').read_text() == 'owned in-progress source\n', (
                ' review17 F3 refusal precedes the destructive source clean'
            )
            assert (source / 'CRYSTA_SOURCE_SHA').read_text().strip() == remote.second, (
                ' review17 F3 refusal preserves the held source marker'
            )
        else:
            assert result.returncode == (91 if caller == 'core' else 0), (
                ' review17 F3 clean source and nested producer handoff must run: ' + result.stderr
            )
            assert head == remote.first, ' review17 F3 the real checkout reaches the pinned source'
            assert not (source / 'untracked-reader').exists(), (
                ' review17 F3 the positive control reaches the actual source clean'
            )
            assert (source / 'CRYSTA_SOURCE_SHA').read_text().strip() == remote.first, (
                ' review17 F3 the positive control writes the acquired source identity'
            )
