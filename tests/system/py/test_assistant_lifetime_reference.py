# SPDX-License-Identifier: BSD-3-Clause
"""An established offline native runtime cannot outlive its killed app owner."""

import ctypes
import json
import os
import signal
import subprocess
import time
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]


def alive(pid):
    if os.name == 'nt':
        kernel = ctypes.windll.kernel32
        kernel.OpenProcess.restype = ctypes.c_void_p
        handle = kernel.OpenProcess(0x100000, False, pid)
        if not handle:
            return False
        try:
            return kernel.WaitForSingleObject(ctypes.c_void_p(handle), 0) == 258
        finally:
            kernel.CloseHandle(ctypes.c_void_p(handle))
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    status = Path(f'/proc/{pid}/stat')
    if not Path('/proc').is_dir():
        return True
    try:
        state = status.read_text(encoding='utf-8').rsplit(')', 1)[1].split()[0]
    except FileNotFoundError:
        return False
    return state != 'Z'


@pytest.mark.parametrize('streaming', [False, True], ids=['idle', 'streaming'])
def test_killed_app_leaves_no_connected_runtime_descendants(tmp_path, streaming):
    suffix = '.exe' if os.name == 'nt' else ''
    host = ROOT / f'build/app/app/edi_assistant_lifetime_host{suffix}'
    runtime = ROOT / f'build/app/app/edi_assistant_lifetime_fixture{suffix}'
    receipt, ready = tmp_path / 'pids', tmp_path / 'connected'
    environment = {**os.environ, 'EDI_LIFETIME_PID_FILE': str(receipt)}
    if streaming:
        environment['EDI_LIFETIME_STREAM'] = '1'
    process = subprocess.Popen(
        [str(host), str(runtime), str(tmp_path), str(ready)],
        env=environment,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    descendants = []
    try:
        deadline = time.monotonic() + 3
        while time.monotonic() < deadline and process.poll() is None:
            if ready.exists() and receipt.exists():
                descendants = [int(row.split()[1]) for row in receipt.read_text().splitlines()]
                if len(descendants) >= 4:
                    break
        assert len(descendants) >= 4 and all(alive(pid) for pid in descendants), (
            'The kill test must first prove a connected guard, runtime, child and grandchild'
        )
        process.kill()
        process.wait(timeout=2)
        deadline = time.monotonic() + 2
        while any(alive(pid) for pid in descendants) and time.monotonic() < deadline:
            pass
        survivors = [pid for pid in descendants if alive(pid)]
        (tmp_path / 'lifetime-observation.json').write_text(
            json.dumps({'observed': descendants, 'survivors_after_two_seconds': survivors}),
            encoding='utf-8',
        )
        assert not survivors, (
            'Killing the app must stop every observed native runtime descendant: ' + str(survivors)
        )
    finally:
        if process.poll() is None:
            process.kill()
            process.wait(timeout=2)
        for pid in descendants:
            if alive(pid):
                os.kill(pid, signal.SIGTERM)
