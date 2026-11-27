#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-3-Clause
"""Run the app's Qt Quick Test cases a list names, on Windows, keeping crash dumps.

    python tools/ci/windows_app_cases.py --runner EXE --cases FILE --dumps DIR --logs DIR

Each line of the list that is not a comment (`#`) is the arguments of one call of edi_app_tests,
run from the repository root with edi's info messages on, so a log shows each click and step.
Windows Error Reporting writes a minidump to --dumps when the runner crashes, and a call that runs
out of --timeout is dumped before it is stopped. Every call's output goes to --logs as well. Exits
1 if a call failed, ran no case or left a dump; an empty list runs nothing and exits 0.
"""

from __future__ import annotations

import argparse
import os
import re
import shlex
import subprocess
import sys
import threading
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
LOCAL_DUMPS = r'SOFTWARE\Microsoft\Windows\Windows Error Reporting'
# The categories edi logs under (app/src/run_log.cpp and the edi.* ones), at Info and above.
LOGGING_RULES = 'app.info=true;crysta.info=true;edi.*.info=true'
TOTALS = re.compile(rb'^Totals: (\d+) passed, (\d+) failed', re.MULTILINE)
MINI_DUMP = 1


def calls(cases: Path) -> list[list[str]]:
    """The runner arguments of each line that is not blank or a comment."""
    lines = [line.strip() for line in cases.read_text(encoding='utf-8').splitlines()]
    return [shlex.split(line) for line in lines if line and not line.startswith('#')]


def keep_dumps(runner: str, folder: Path) -> None:
    """Have Windows Error Reporting write the runner's crash dumps to the folder, no dialog."""
    import winreg  # noqa: PLC0415 - Windows only

    access = winreg.KEY_SET_VALUE | winreg.KEY_WOW64_64KEY
    with winreg.CreateKeyEx(winreg.HKEY_LOCAL_MACHINE, LOCAL_DUMPS, 0, access) as key:
        winreg.SetValueEx(key, 'DontShowUI', 0, winreg.REG_DWORD, 1)
    path = rf'{LOCAL_DUMPS}\LocalDumps\{runner}'
    with winreg.CreateKeyEx(winreg.HKEY_LOCAL_MACHINE, path, 0, access) as key:
        winreg.SetValueEx(key, 'DumpFolder', 0, winreg.REG_EXPAND_SZ, str(folder))
        winreg.SetValueEx(key, 'DumpType', 0, winreg.REG_DWORD, MINI_DUMP)
        winreg.SetValueEx(key, 'DumpCount', 0, winreg.REG_DWORD, 5)


def dump_hung(pid: int, path: Path) -> None:
    """Write a minidump of a runner that ran out of time, so its stacks show where it waited."""
    import ctypes  # noqa: PLC0415 - Windows API
    import msvcrt  # noqa: PLC0415
    from ctypes import wintypes  # noqa: PLC0415

    kernel32 = ctypes.WinDLL('kernel32', use_last_error=True)
    kernel32.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
    kernel32.OpenProcess.restype = wintypes.HANDLE
    kernel32.CloseHandle.argtypes = [wintypes.HANDLE]
    dbghelp = ctypes.WinDLL('dbghelp', use_last_error=True)
    dbghelp.MiniDumpWriteDump.argtypes = [
        wintypes.HANDLE,
        wintypes.DWORD,
        wintypes.HANDLE,
        ctypes.c_int,
        ctypes.c_void_p,
        ctypes.c_void_p,
        ctypes.c_void_p,
    ]
    dbghelp.MiniDumpWriteDump.restype = wintypes.BOOL
    # PROCESS_QUERY_INFORMATION | PROCESS_VM_READ
    process = kernel32.OpenProcess(0x0400 | 0x0010, False, pid)
    if not process:
        raise ctypes.WinError(ctypes.get_last_error())
    try:
        with path.open('wb') as out:
            handle = msvcrt.get_osfhandle(out.fileno())
            if not dbghelp.MiniDumpWriteDump(process, pid, handle, 0, None, None, None):
                raise ctypes.WinError(ctypes.get_last_error())
    finally:
        kernel32.CloseHandle(process)


def run(command: list[str], log: Path, timeout: float, hung: Path) -> tuple[str, bytes]:
    """Run one call, its output to the console and the log; its exit code, or `timeout`."""
    environment = dict(os.environ)
    # A CI runner has no console window, so Qt would send its messages and Qt Test's results to
    # the debugger only (OutputDebugString), and the log would hold no case at all.
    environment.setdefault('QT_FORCE_STDERR_LOGGING', '1')
    environment.setdefault('QT_LOGGING_RULES', LOGGING_RULES)
    environment.setdefault('QT_MESSAGE_PATTERN', '%{time process} %{category}: %{message}')
    seen = bytearray()
    with log.open('wb') as out:
        runner = subprocess.Popen(
            command, cwd=ROOT, env=environment, stdout=subprocess.PIPE, stderr=subprocess.STDOUT
        )

        def copy() -> None:
            for line in iter(runner.stdout.readline, b''):
                seen.extend(line)
                out.write(line)
                sys.stdout.buffer.write(line)
                sys.stdout.flush()

        # A daemon, joined with a limit: a process the runner started may still hold the pipe.
        copier = threading.Thread(target=copy, daemon=True)
        copier.start()
        try:
            code = str(runner.wait(timeout=timeout))
        except subprocess.TimeoutExpired:
            try:
                dump_hung(runner.pid, hung)
            except OSError as error:
                print(f'windows_app_cases: could not dump the hung runner: {error}', flush=True)
            runner.kill()
            runner.wait()
            code = 'timeout'
        copier.join(timeout=60)
    return code, bytes(seen)


def call(
    runner: Path, arguments: list[str], number: int, args: argparse.Namespace
) -> tuple[list[str], str, float, int]:
    """One call: its arguments, exit code, seconds and the number of cases it ran."""
    # Qt Test's own crash handler ends the process itself, which leaves Windows nothing to dump;
    # and its default limit of 2000 messages would cut a long log short.
    command = [str(runner), '-nocrashhandler', '-maxwarnings', '0', *arguments]
    print(f'windows_app_cases: call {number}: {shlex.join(arguments)}', flush=True)
    start = time.monotonic()
    log = args.logs / f'call-{number:02}.log'
    hung = args.dumps.resolve() / f'call-{number:02}-hung.dmp'
    code, output = run(command, log, args.timeout, hung)
    seconds = time.monotonic() - start
    ran = sum(int(passed) + int(failed) for passed, failed in TOTALS.findall(output))
    if code.isdigit() and int(code) > 255:
        code = f'0x{int(code):08X}'  # an NTSTATUS, such as 0xC0000005 for an access violation
    return arguments, code, seconds, ran


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split('\n\n', 1)[0])
    parser.add_argument('--runner', type=Path, required=True, help='edi_app_tests.exe')
    parser.add_argument('--cases', type=Path, required=True, help='the list of calls')
    parser.add_argument('--dumps', type=Path, required=True, help='where crash dumps go')
    parser.add_argument('--logs', type=Path, required=True, help="where each call's output goes")
    parser.add_argument('--timeout', type=float, default=900, help='seconds a call may take')
    args = parser.parse_args()
    if sys.platform != 'win32':
        print('windows_app_cases: runs the app on Windows only', file=sys.stderr)
        return 2
    todo = calls(args.cases)
    if not todo:
        print(f'windows_app_cases: {args.cases} names no call, so there is nothing to run')
        return 0
    runner = args.runner.resolve()
    if not runner.is_file():
        print(f'windows_app_cases: {args.runner} is not built', file=sys.stderr)
        return 1
    dumps = args.dumps.resolve()
    dumps.mkdir(parents=True, exist_ok=True)
    args.logs.mkdir(parents=True, exist_ok=True)
    try:
        keep_dumps(runner.name, dumps)
    except OSError as error:
        print(f'windows_app_cases: crash dumps are off: {error}', flush=True)
    results = [call(runner, arguments, number, args) for number, arguments in enumerate(todo, 1)]
    failed = False
    for arguments, code, seconds, ran in results:
        verdict = 'ok' if code == '0' and ran else 'FAILED'
        failed |= verdict != 'ok'
        print(f'{verdict}: exit {code}, {seconds:.0f} s, {ran} case(s): {shlex.join(arguments)}')
    found = sorted(dumps.glob('*.dmp'))
    for dump in found:
        print(f'windows_app_cases: dump {dump} ({dump.stat().st_size} bytes)')
    return 1 if failed or found else 0


if __name__ == '__main__':
    sys.exit(main())
