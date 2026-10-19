"""Keep the plain-data host build bounded and stop its descendants on timeout."""

from __future__ import annotations

import os
import signal
import subprocess
import sys
from contextlib import suppress

import pytest

from tests.fixtures.plain_data import build_probe


@pytest.mark.parametrize('timing', [False, True])
def test_build_passes_a_numeric_budget_to_cmake(monkeypatch, tmp_path, timing):
    calls = []
    if timing:
        monkeypatch.setattr(build_probe.shutil, 'copy2', lambda *_args: None)
        monkeypatch.setattr(
            build_probe.subprocess, 'check_output', lambda *_args, **_kwargs: 'revision'
        )
    monkeypatch.setenv('CONDA_PREFIX', str(tmp_path))
    monkeypatch.setenv('CMAKE_BUILD_PARALLEL_LEVEL', '2')
    monkeypatch.setattr(
        sys,
        'argv',
        [
            'build_probe.py',
            '--root',
            str(tmp_path),
            '--sdk',
            str(tmp_path),
            '--build',
            str(tmp_path / 'build'),
        ],
    )

    class Archive:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        @staticmethod
        def extractall(source, **_kwargs):
            (source / 'CMakeLists.txt').write_text('')
            (source / '.git/objects/info').mkdir(parents=True)

    monkeypatch.setattr(build_probe.tarfile, 'open', lambda *_args: Archive())
    monkeypatch.setattr(build_probe.shutil, 'copytree', lambda *_args, **_kwargs: None)
    monkeypatch.setattr(
        build_probe.subprocess, 'run', lambda command, **_kwargs: calls.append(command)
    )
    if timing:
        sys.argv.append('--timing-observer')
    build_probe.main()
    configure = next(command for command in calls if '-S' in command)
    assert '-DQT_QML_NO_CACHEGEN=' + ('OFF' if timing else 'ON') in configure, (
        'Direct view-model host omits unused QML caches; '
        'the production timing observer retains them'
    )
    command = next(command for command in calls if '--build' in command)
    assert command[-2:] == ['--parallel', '2'], (
        'Native host build must pass the worker limit numerically; bare -j discards that limit'
    )


@pytest.mark.parametrize('value', ['0', '-1', '', 'bad', '2.5'])
def test_invalid_worker_budget_refuses_before_build(monkeypatch, value):
    monkeypatch.setenv('CMAKE_BUILD_PARALLEL_LEVEL', value)
    with pytest.raises(RuntimeError, match='positive numeric worker budget'):
        build_probe.build_jobs()


def test_unset_budget_uses_detected_cores(monkeypatch):
    monkeypatch.delenv('CMAKE_BUILD_PARALLEL_LEVEL', raising=False)
    monkeypatch.setattr(build_probe.os, 'cpu_count', lambda: 3)
    assert build_probe.build_jobs() == '3', (
        'Native host build must bound compilation to detected cores when no limit was supplied'
    )
    monkeypatch.setattr(build_probe.os, 'cpu_count', lambda: None)
    assert build_probe.build_jobs() == '1', (
        'Native host build must retain a finite worker count when CPU detection is unavailable'
    )


@pytest.mark.parametrize('parent_exits', [False, True])
def test_timeout_stops_the_build_descendant_and_preserves_output(tmp_path, parent_exits):
    pid_file = tmp_path / 'child.pid'
    child = (
        'import os,time,pathlib; '
        f'pathlib.Path({str(pid_file)!r}).write_text(str(os.getpid())); '
        'print("native compile started",flush=True); time.sleep(60)'
    )
    parent = f'import subprocess,sys,time; subprocess.Popen([sys.executable,"-c",{child!r}]); ' + (
        '' if parent_exits else 'time.sleep(60)'
    )
    try:
        with pytest.raises(RuntimeError, match='native compile started'):
            build_probe.build_host([sys.executable, '-c', parent], timeout=0.4)
        assert pid_file.is_file(), (
            'Timeout control must reach a real build descendant before its deadline'
        )
        pid = int(pid_file.read_text())
        completed = subprocess.run(
            ['ps', '-o', 'stat=', '-p', str(pid)], capture_output=True, text=True, check=False
        )
        assert not completed.stdout.strip() or completed.stdout.strip().startswith('Z'), (
            'Native build timeout must leave no running compiler child, '
            'even after its parent exits'
        )
    finally:
        if pid_file.exists():
            with suppress(ProcessLookupError):
                os.kill(int(pid_file.read_text()), signal.SIGKILL)


def test_completed_build_retains_its_failure_output():
    completed = build_probe.build_host([
        sys.executable,
        '-c',
        'import sys; print("configure refused"); sys.exit(7)',
    ])
    assert completed.returncode == 7 and 'configure refused' in completed.stdout, (
        'Native host build must retain the actual configure or compile refusal and its output'
    )
