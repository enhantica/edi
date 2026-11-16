"""Exercise an actually unreadable regular file through one cross-platform scope."""

import ctypes
import os
import stat
from contextlib import contextmanager
from pathlib import Path


def _exclusive_reader(path):
    from ctypes import wintypes  # noqa: PLC0415 - the Windows boundary is loaded only there

    kernel = ctypes.WinDLL('kernel32', use_last_error=True)
    open_file = kernel.CreateFileW
    open_file.argtypes = [
        wintypes.LPCWSTR,
        wintypes.DWORD,
        wintypes.DWORD,
        ctypes.c_void_p,
        wintypes.DWORD,
        wintypes.DWORD,
        wintypes.HANDLE,
    ]
    open_file.restype = wintypes.HANDLE
    handle = open_file(str(path), 0x80000000, 0, None, 3, 0x80, None)
    if handle == ctypes.c_void_p(-1).value:
        raise ctypes.WinError(ctypes.get_last_error())
    kernel.CloseHandle.argtypes = [wintypes.HANDLE]
    kernel.CloseHandle.restype = wintypes.BOOL
    return kernel, handle


@contextmanager
def unreadable_file(path):
    """Deny a second real read, preserve the regular file, then restore access."""
    path = Path(path)
    before_mode = stat.S_IMODE(path.stat().st_mode)
    kernel, handle = _exclusive_reader(path) if os.name == 'nt' else (None, None)
    if kernel is None:
        path.chmod(0)
    try:
        try:
            path.read_bytes()
        except OSError:
            pass
        else:
            raise RuntimeError('The read-failure vehicle must deny an actual file read')
        yield stat.S_IMODE(path.stat().st_mode)
    finally:
        if kernel is not None:
            if not kernel.CloseHandle(handle):
                raise ctypes.WinError(ctypes.get_last_error())
        else:
            path.chmod(before_mode)
