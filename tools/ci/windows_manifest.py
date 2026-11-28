#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-3-Clause
"""Check that Windows executables run with UTF-8 as their ANSI code page (ADR-0109).

    python tools/ci/windows_manifest.py EXE...
    python tools/ci/windows_manifest.py --refused EXE

Reads each program's own embedded manifest (resource RT_MANIFEST 1), not the build files, and
exits non-zero naming every program whose manifest does not set activeCodePage to UTF-8.
--refused inverts the check for one program known to lack it, so a run shows the check can fail.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

RT_MANIFEST = 24
PROCESS_MANIFEST = 1
# LOAD_LIBRARY_AS_DATAFILE | LOAD_LIBRARY_AS_IMAGE_RESOURCE: read the resources, run nothing.
LOAD_AS_RESOURCE = 0x00000002 | 0x00000020
# The element as the linker's merge writes it, a namespace prefix allowed.
ACTIVE_CODE_PAGE = re.compile(
    rb'<(?:[\w.-]+:)?activeCodePage\b[^>]*>\s*UTF-8\s*</(?:[\w.-]+:)?activeCodePage>',
    re.IGNORECASE,
)


def embedded_manifest(executable: Path) -> bytes | None:
    """The program's embedded manifest, or None when it has none. Windows only."""
    import ctypes  # noqa: PLC0415 - Windows API, loaded only when a program is read
    from ctypes import wintypes  # noqa: PLC0415

    kernel32 = ctypes.WinDLL('kernel32', use_last_error=True)
    kernel32.LoadLibraryExW.argtypes = [wintypes.LPCWSTR, wintypes.HANDLE, wintypes.DWORD]
    kernel32.LoadLibraryExW.restype = wintypes.HMODULE
    kernel32.FindResourceW.argtypes = [wintypes.HMODULE, ctypes.c_void_p, ctypes.c_void_p]
    kernel32.FindResourceW.restype = wintypes.HANDLE
    kernel32.SizeofResource.argtypes = [wintypes.HMODULE, wintypes.HANDLE]
    kernel32.SizeofResource.restype = wintypes.DWORD
    kernel32.LoadResource.argtypes = [wintypes.HMODULE, wintypes.HANDLE]
    kernel32.LoadResource.restype = wintypes.HANDLE
    kernel32.LockResource.argtypes = [wintypes.HANDLE]
    kernel32.LockResource.restype = ctypes.c_void_p
    kernel32.FreeLibrary.argtypes = [wintypes.HMODULE]

    module = kernel32.LoadLibraryExW(str(executable.resolve()), None, LOAD_AS_RESOURCE)
    if not module:
        raise OSError(ctypes.get_last_error(), f'cannot read {executable}')
    try:
        found = kernel32.FindResourceW(module, PROCESS_MANIFEST, RT_MANIFEST)
        if not found:
            return None
        size = kernel32.SizeofResource(module, found)
        data = kernel32.LockResource(kernel32.LoadResource(module, found))
        return ctypes.string_at(data, size) if data and size else None
    finally:
        kernel32.FreeLibrary(module)


def sets_utf8(manifest: bytes | None) -> bool:
    """Whether a manifest's activeCodePage element says UTF-8."""
    return bool(manifest) and ACTIVE_CODE_PAGE.search(manifest) is not None


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split('\n\n', 1)[0])
    parser.add_argument('--refused', action='store_true', help='expect the one program to lack it')
    parser.add_argument('executables', type=Path, nargs='+')
    args = parser.parse_args()
    if sys.platform != 'win32':
        print('windows_manifest: reads Windows programs, on Windows only', file=sys.stderr)
        return 2
    if args.refused and len(args.executables) != 1:
        parser.error('--refused takes exactly one program')
    failed = []
    for executable in args.executables:
        utf8 = sets_utf8(embedded_manifest(executable))
        print(f'{executable}: activeCodePage {"UTF-8" if utf8 else "not UTF-8"}')
        if utf8 == args.refused:
            failed.append(executable)
    if failed:
        wanted = 'should lack' if args.refused else 'lacks'
        for executable in failed:
            print(f'windows_manifest: {executable} {wanted} the UTF-8 code page', file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
