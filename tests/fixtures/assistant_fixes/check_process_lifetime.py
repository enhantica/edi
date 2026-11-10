# SPDX-License-Identifier: BSD-3-Clause
"""Recorded runtime process-family shutdown checks."""

import ctypes
import os
import signal
import subprocess
import sys
import tempfile
import time
from ctypes import wintypes
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]


def _alive(pid: int) -> bool:
    if os.name == 'nt':
        kernel = ctypes.windll.kernel32
        kernel.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
        kernel.OpenProcess.restype = wintypes.HANDLE
        kernel.WaitForSingleObject.argtypes = [wintypes.HANDLE, wintypes.DWORD]
        kernel.CloseHandle.argtypes = [wintypes.HANDLE]
        handle = kernel.OpenProcess(0x100000, False, pid)
        if not handle:
            return False
        running = kernel.WaitForSingleObject(handle, 0) == 258
        kernel.CloseHandle(handle)
        return running
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    stat = Path(f'/proc/{pid}/stat')
    try:
        return stat.read_text(encoding='utf-8').split(')', 1)[1].split()[0] != 'Z'
    except FileNotFoundError:
        return not sys.platform.startswith('linux')


def _connected_pids(process: subprocess.Popen, pid_file: Path, ready: Path) -> list[int]:
    deadline = time.monotonic() + 10
    while time.monotonic() < deadline:
        pids = _recorded_pids(pid_file)
        if ready.exists() and len(pids) == 4:
            return pids
        if process.poll() is not None:
            raise AssertionError(process.communicate()[1].decode())
        time.sleep(0.05)
    raise AssertionError('Recorded session did not connect with its guard, child and grandchild')


def _exercise(tmp_path: Path, *, retire: bool, streaming: bool = False) -> None:
    pid_file = tmp_path / 'pids'
    ready = tmp_path / 'ready'
    suffix = '.exe' if os.name == 'nt' else ''
    binaries = Path(os.environ.get('EDI_LIFETIME_BIN_DIR', str(ROOT / 'build/app/app')))
    host = binaries / f'edi_assistant_lifetime_host{suffix}'
    fixture = binaries / f'edi_assistant_lifetime_fixture{suffix}'
    environment = dict(os.environ, EDI_LIFETIME_PID_FILE=str(pid_file))
    if streaming:
        environment['EDI_LIFETIME_STREAM'] = '1'
    command = [str(host), str(fixture), str(tmp_path), str(ready)]
    if retire:
        command.append('--retire')
    process = subprocess.Popen(
        command, env=environment, stdout=subprocess.PIPE, stderr=subprocess.PIPE
    )
    pids = []
    try:
        pids = _connected_pids(process, pid_file, ready)
        if not retire:
            process.kill()
        process.wait(timeout=5)
        deadline = time.monotonic() + 5
        while any(_alive(pid) for pid in pids) and time.monotonic() < deadline:
            time.sleep(0.05)
        if any(_alive(pid) for pid in pids):
            raise AssertionError('Assistant process family survived its owner')
    finally:
        if process.poll() is None:
            process.kill()
            process.wait(timeout=5)
        for pid in _recorded_pids(pid_file):
            if _alive(pid):
                os.kill(pid, signal.SIGTERM)


def _recorded_pids(path: Path) -> list[int]:
    if not path.exists():
        return []
    return [int(row.split()[1]) for row in path.read_text(encoding='utf-8').splitlines()]


def test_killing_host_stops_runtime_family() -> None:
    with tempfile.TemporaryDirectory() as folder:
        _exercise(Path(folder), retire=False)


def test_retiring_agent_stops_runtime_family() -> None:
    with tempfile.TemporaryDirectory() as folder:
        _exercise(Path(folder), retire=True)


def test_killing_host_while_streaming_stops_runtime_family() -> None:
    with tempfile.TemporaryDirectory() as folder:
        _exercise(Path(folder), retire=False, streaming=True)
