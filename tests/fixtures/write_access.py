"""Prove that a cache parent cannot create files or directories on the current host."""

import csv
import os
import stat
import subprocess
import tempfile
import uuid
from contextlib import ExitStack, contextmanager
from pathlib import Path


@contextmanager
def _without_restore_privilege():
    """Keep admin membership but suspend the write-access-check bypass in this process.

    Child CMake processes inherit this token state. Preserve and restore the exact
    previous privilege attributes; no account ACL or system policy is changed.
    https://learn.microsoft.com/en-us/windows-hardware/drivers/ifs/privileges
    """
    import ctypes  # noqa: PLC0415 - this API exists only on Windows
    from ctypes import wintypes  # noqa: PLC0415

    class Luid(ctypes.Structure):
        _fields_ = [('low', wintypes.DWORD), ('high', wintypes.LONG)]

    class Entry(ctypes.Structure):
        _fields_ = [('luid', Luid), ('attributes', wintypes.DWORD)]

    class Privileges(ctypes.Structure):
        _fields_ = [('count', wintypes.DWORD), ('entries', Entry * 1)]

    api = ctypes.WinDLL('advapi32', use_last_error=True)
    kernel = ctypes.WinDLL('kernel32', use_last_error=True)
    kernel.GetCurrentProcess.restype = wintypes.HANDLE
    kernel.CloseHandle.argtypes = [wintypes.HANDLE]
    api.OpenProcessToken.argtypes = [
        wintypes.HANDLE,
        wintypes.DWORD,
        ctypes.POINTER(wintypes.HANDLE),
    ]
    api.LookupPrivilegeValueW.argtypes = [wintypes.LPCWSTR, wintypes.LPCWSTR, ctypes.POINTER(Luid)]
    api.AdjustTokenPrivileges.argtypes = [
        wintypes.HANDLE,
        wintypes.BOOL,
        ctypes.c_void_p,
        wintypes.DWORD,
        ctypes.c_void_p,
        ctypes.POINTER(wintypes.DWORD),
    ]
    token = wintypes.HANDLE()
    if not api.OpenProcessToken(kernel.GetCurrentProcess(), 0x20 | 0x8, ctypes.byref(token)):
        raise ctypes.WinError(ctypes.get_last_error())
    previous = Privileges()
    try:
        requested = Privileges()
        requested.count = 1
        if not api.LookupPrivilegeValueW(
            None, 'SeRestorePrivilege', ctypes.byref(requested.entries[0].luid)
        ):
            raise ctypes.WinError(ctypes.get_last_error())
        length = wintypes.DWORD()
        ctypes.set_last_error(0)
        if not api.AdjustTokenPrivileges(
            token,
            False,
            ctypes.byref(requested),
            ctypes.sizeof(previous),
            ctypes.byref(previous),
            ctypes.byref(length),
        ):
            raise ctypes.WinError(ctypes.get_last_error())
        error = ctypes.get_last_error()
        # ERROR_NOT_ALL_ASSIGNED means this token never had the bypass privilege.
        if error not in {0, 1300}:
            raise ctypes.WinError(error)
        yield
    finally:
        try:
            if previous.count:
                ctypes.set_last_error(0)
                if (
                    not api.AdjustTokenPrivileges(
                        token, False, ctypes.byref(previous), 0, None, None
                    )
                    or ctypes.get_last_error()
                ):
                    raise ctypes.WinError(ctypes.get_last_error())
        finally:
            kernel.CloseHandle(token)


@contextmanager
def unwritable_directory(directory):
    """Retain read access while denying actual creation, then restore the original permissions."""
    directory = Path(directory)
    mode = stat.S_IMODE(directory.stat().st_mode)
    with tempfile.TemporaryDirectory(dir=directory.parent) as scratch, ExitStack() as privileges:
        if os.name == 'nt':
            system = Path(os.environ['SYSTEMROOT']) / 'System32'
            user = subprocess.run(
                [str(system / 'whoami.exe'), '/user', '/fo', 'csv', '/nh'],
                capture_output=True,
                text=True,
                check=True,
                timeout=5,
            )
            sid = next(csv.reader(user.stdout.splitlines()))[1]
            if not sid.startswith('S-1-'):
                raise RuntimeError(
                    'The cache permission vehicle requires the actual current user SID'
                )
            icacls = str(system / 'icacls.exe')
            saved = str(Path(scratch) / 'original.acl')

            def acl(*args):
                subprocess.run(
                    [icacls, *args],
                    cwd=directory.parent,
                    check=True,
                    capture_output=True,
                    timeout=5,
                )

            acl(directory.name, '/save', saved)
            privileges.enter_context(_without_restore_privilege())
        try:
            if os.name == 'nt':
                acl(directory.name, '/inheritancelevel:r')
                acl(directory.name, '/grant:r', '*' + sid + ':(RX)')
                acl(directory.name, '/deny', '*' + sid + ':(OI)(CI)(WD,AD,WA,WEA)')
            else:
                directory.chmod(0o555)
            for kind in ['file', 'directory']:
                try:  # noqa: PLW0717 - an allowed create disproves the permission premise
                    if kind == 'file':
                        descriptor, path = tempfile.mkstemp(dir=directory)
                        os.close(descriptor)
                        Path(path).unlink()
                    else:
                        # CMake creates an ordinary directory with inherited security.
                        # tempfile.mkdtemp uses Python's Windows-only 0700 protected ACL.
                        path = directory / ('permission-probe-' + uuid.uuid4().hex)
                        path.mkdir()
                        path.rmdir()
                except PermissionError:
                    continue
                raise RuntimeError(
                    'The cache permission vehicle must deny actual ' + kind + ' creation'
                )
            yield
        finally:
            if os.name == 'nt':
                acl('.', '/restore', saved)
            else:
                directory.chmod(mode)
