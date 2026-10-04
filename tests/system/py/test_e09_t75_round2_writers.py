"""F02: authorized direct/special callers must share prefix and cache ownership.

Ordinary concurrent core/coverage work can otherwise replace a prefix being read;
app's separate prefix still acquires the same downloaded cache.
"""

from __future__ import annotations

import copy
import fcntl
import os
import select
import subprocess
import sys
import tomllib

import pytest
import yaml

from tests.integration.py.test_e09_t75_sdk_consumer import ROOT, SHA, consumer


@pytest.mark.parametrize('caller', ['sdk-task', 'core', 'coverage', 'app'])
def test_all_prefix_writers_respect_an_existing_producer(tmp_path, caller):
    def prepare(base):
        base.mkdir()
        env, repo, sdk = consumer(base, platform='linux-64', prepare_only=True)
        env.update(
            EDI_USE_CONSUMER_BUILD='1', EDI_CORE_BUILD_LOCK_WAIT_S='0', CONDA_PREFIX=str(base)
        )
        (repo / 'CMakeLists.txt').write_text('project(independent)\n')
        # Reachability stops at the native compiler boundary, whose effects are outside this gate.
        for tool in ('clang', 'clang++', 'llvm-profdata', 'llvm-cov'):
            binary = base / 'bin' / tool
            binary.write_text('#!/bin/sh\nexit 91\n')
            binary.chmod(0o755)
        cmake = base / 'bin/cmake'
        cmake.write_text('#!/bin/sh\nprintf "%s\\n" "$*" >> "$SDK_COMMANDS"\nexit 91\n')
        return env, repo, sdk

    if caller == 'sdk-task':
        declared = tomllib.loads((ROOT / 'pixi.toml').read_text())['tasks']['crysta-sdk']
        command = declared if isinstance(declared, str) else declared['cmd']
    else:
        command = (
            'bash tools/ci/'
            + {'core': 'core-build.sh', 'coverage': 'cpp-coverage-unit.sh', 'app': 'app-build.sh'}[
                caller
            ]
        )

    def run(env, repo):
        return subprocess.run(
            ['bash', '-eu', '-c', command],
            cwd=repo,
            env=env,
            capture_output=True,
            text=True,
            timeout=3,
            check=False,
        )

    env, repo, _ = prepare(tmp_path / 'control')
    good = run(env, repo)
    assert good.returncode == (0 if caller == 'sdk-task' else 91), (
        f' I26 clean caller must acquire before the bounded compiler stop: {good.stderr}'
    )
    prefix = repo / 'build/crysta-consumer-prefix'
    assert (prefix / '.crysta-sha').read_text().strip() == SHA, (
        ' I26 clean caller installs the independently qualified SDK'
    )
    env, repo, _ = prepare(tmp_path / 'held')
    prefix = repo / 'build/crysta-consumer-prefix'
    prefix.mkdir(parents=True)
    sentinel = prefix / 'held-reader'
    sentinel.write_text('owned by another producer\n')
    lock = repo / 'build/.core-build.lock.d'
    lock.mkdir()
    bad = run(env, repo)
    assert bad.returncode != 0, ' I26 occupied producer boundary cannot admit another writer'
    assert sentinel.exists(), (
        ' I26 direct/special caller cannot remove the prefix while another producer owns it'
    )
    assert sentinel.read_text() == 'owned by another producer\n', (
        ' I26 held prefix bytes must remain untouched'
    )
    assert not (prefix / '.crysta-sha').exists(), ' I26 refusal must precede prefix installation'


@pytest.mark.parametrize('environment', ['default', 'app'])
def test_direct_fetch_does_not_replace_a_cache_owned_by_another_acquisition(  # noqa: PLR0914
    tmp_path, environment
):
    env, repo, _ = consumer(tmp_path, platform='linux-64', download=True, prepare_only=True)
    env['PIXI_ENVIRONMENT_NAME'] = environment
    lockfile = repo / 'pixi.lock'
    lock = yaml.safe_load(lockfile.read_text())
    lock['environments']['app'] = copy.deepcopy(lock['environments']['default'])
    lockfile.write_text(yaml.safe_dump(lock, sort_keys=False))
    command = [sys.executable, 'tools/ci/crysta_sdk.py', 'fetch', '--platform', 'linux-64']
    good = subprocess.run(
        command, cwd=repo, env=env, capture_output=True, text=True, check=False, timeout=3
    )
    assert good.returncode == 0, ' I26 clean direct acquisition must qualify the cache'
    cache = repo / 'build/crysta-sdk' / (SHA + '-linux-64')
    (cache / '.sdk-sha256').unlink()
    sentinel = cache / 'owned-partial-state'
    sentinel.write_text('earlier acquisition still owns this directory\n')
    # Existing cache acquisition seam: hold the actual OS lock as the earlier writer.
    with (cache.parent / '.lock').open('w') as owned:
        fcntl.flock(owned, fcntl.LOCK_EX)
        read_fd, write_fd = os.pipe()
        entry = tmp_path / 'observed-acquisition.py'
        entry.write_text(
            'import fcntl,os,runpy,sys\n'
            'native=fcntl.flock\n'
            'def observed(fd, operation):\n'
            ' if operation & fcntl.LOCK_EX:\n'
            '  os.write(int(os.environ["LOCK_READY"]),b"ACQUIRE\\n")\n'
            ' return native(fd,operation)\n'
            'fcntl.flock=observed\n'
            'sys.argv=["tools/ci/crysta_sdk.py","fetch","--platform","linux-64"]\n'
            'runpy.run_path(sys.argv[0],run_name="__main__")\n'
        )
        child = subprocess.Popen(
            [sys.executable, str(entry)],
            cwd=repo,
            env={**env, 'LOCK_READY': str(write_fd)},
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            pass_fds=(write_fd,),
        )
        os.close(write_fd)
        try:
            ready, _, _ = select.select([read_fd], [], [], 2)
            assert ready and os.read(read_fd, 100) == b'ACQUIRE\n', (
                ' review17 F3 contention requires arrival at the actual OS acquisition'
            )
            assert child.poll() is None, (
                ' review17 F3 the contender remains blocked while the owner holds the lock'
            )
            intact = (
                sentinel.exists()
                and sentinel.read_text() == 'earlier acquisition still owns this directory\n'
            )
        finally:
            os.close(read_fd)
            fcntl.flock(owned, fcntl.LOCK_UN)
            stdout, stderr = child.communicate(timeout=3)
    assert intact, " I26 both environments wait before replacing another acquisition's cache"
    assert child.returncode == 0, (
        f' I26 acquisition must complete after the owner releases: {stdout} {stderr}'
    )
