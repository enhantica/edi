"""Keep an actual Windows compiler family owned even if its first parent exits."""

import ctypes
import json
import os
import subprocess
import sys
from ctypes import wintypes


class BasicLimits(ctypes.Structure):
    _fields_ = [
        ('process_time', ctypes.c_int64),
        ('job_time', ctypes.c_int64),
        ('flags', wintypes.DWORD),
        ('minimum_working_set', ctypes.c_size_t),
        ('maximum_working_set', ctypes.c_size_t),
        ('active_processes', wintypes.DWORD),
        ('affinity', ctypes.c_size_t),
        ('priority', wintypes.DWORD),
        ('scheduling', wintypes.DWORD),
    ]


class IoCounters(ctypes.Structure):
    _fields_ = [
        (name, ctypes.c_uint64)
        for name in (
            'read_operations',
            'write_operations',
            'other_operations',
            'read_bytes',
            'write_bytes',
            'other_bytes',
        )
    ]


class ExtendedLimits(ctypes.Structure):
    _fields_ = [
        ('basic', BasicLimits),
        ('io', IoCounters),
        ('process_memory', ctypes.c_size_t),
        ('job_memory', ctypes.c_size_t),
        ('peak_process_memory', ctypes.c_size_t),
        ('peak_job_memory', ctypes.c_size_t),
    ]


def kernel_api():
    kernel = ctypes.WinDLL('kernel32', use_last_error=True)
    signatures = {
        'CreateJobObjectW': ([ctypes.c_void_p, wintypes.LPCWSTR], wintypes.HANDLE),
        'SetInformationJobObject': (
            [wintypes.HANDLE, ctypes.c_int, ctypes.c_void_p, wintypes.DWORD],
            wintypes.BOOL,
        ),
        'AssignProcessToJobObject': ([wintypes.HANDLE, wintypes.HANDLE], wintypes.BOOL),
        'TerminateJobObject': ([wintypes.HANDLE, wintypes.UINT], wintypes.BOOL),
        'OpenProcess': ([wintypes.DWORD, wintypes.BOOL, wintypes.DWORD], wintypes.HANDLE),
        'WaitForSingleObject': ([wintypes.HANDLE, wintypes.DWORD], wintypes.DWORD),
        'CloseHandle': ([wintypes.HANDLE], wintypes.BOOL),
    }
    for name, (arguments, result) in signatures.items():
        getattr(kernel, name).argtypes = arguments
        getattr(kernel, name).restype = result
    return kernel


def require_success(result):
    if not result:
        raise ctypes.WinError(ctypes.get_last_error())
    return result


class CompilerJob:
    def __init__(self):
        self.kernel = kernel_api()
        self.handle = require_success(self.kernel.CreateJobObjectW(None, None))
        limits = ExtendedLimits()
        limits.basic.flags = 0x2000  # JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE, no breakaway.
        try:
            require_success(
                self.kernel.SetInformationJobObject(
                    self.handle, 9, ctypes.byref(limits), ctypes.sizeof(limits)
                )
            )
        except BaseException:
            self.close()
            raise

    def assign(self, pid):
        process = require_success(self.kernel.OpenProcess(0x0101, False, pid))
        try:
            require_success(self.kernel.AssignProcessToJobObject(self.handle, process))
        finally:
            require_success(self.kernel.CloseHandle(process))

    def stop(self):
        require_success(self.kernel.TerminateJobObject(self.handle, 1))

    def close(self):
        if self.handle:
            handle, self.handle = self.handle, None
            require_success(self.kernel.CloseHandle(handle))


def process_running(pid):
    kernel = kernel_api()
    process = kernel.OpenProcess(0x101000, False, pid)
    if not process:
        error = ctypes.get_last_error()
        if error == 87:  # ERROR_INVALID_PARAMETER: no such PID.
            return False
        raise ctypes.WinError(error)
    try:
        state = kernel.WaitForSingleObject(process, 1000)
        if state == 0:  # WAIT_OBJECT_0: the actual process terminated.
            return False
        if state == 258:  # WAIT_TIMEOUT: it remains alive.
            return True
        raise ctypes.WinError(ctypes.get_last_error())
    finally:
        require_success(kernel.CloseHandle(process))


def build_host(command, timeout):
    job = CompilerJob()
    process = None
    released = False
    # The bootstrap waits before creating any compiler descendant; membership is established first.
    bootstrap = compiler_bootstrap()
    try:
        process = subprocess.Popen(
            [sys.executable, '-c', bootstrap, json.dumps([os.fspath(a) for a in command])],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
        )
        job.assign(process.pid)
        process.stdin.write('1')
        process.stdin.flush()
        released = True
        try:
            output, _ = process.communicate(timeout=timeout)
        except subprocess.TimeoutExpired:
            job.stop()
            output, _ = process.communicate(timeout=5)
            raise RuntimeError(
                f'Plain-data native host exceeded {timeout} seconds; compiler job stopped\n'
                + output
            ) from None
        return subprocess.CompletedProcess(command, process.returncode, output, '')
    finally:
        if process is not None and not released:
            process.kill()
            process.communicate(timeout=5)
        job.close()


def compiler_bootstrap():
    """Preserve argv quoting and exit status after the parent admits job membership."""
    return (
        'import json,subprocess,sys; args=json.loads(sys.argv[1]); '
        'ready=sys.stdin.buffer.read(1); '
        'sys.exit(125 if ready!=b"1" else subprocess.call(args))'
    )
