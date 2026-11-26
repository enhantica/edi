# SPDX-License-Identifier: BSD-3-Clause
"""Put an .ico file in place of a Windows program's icon, as binarycreator does for an installer.

The maintenance tool is the Framework's installerbase.exe, which carries the Framework's icon.
"""

import ctypes
import struct
from pathlib import Path

RT_ICON, RT_GROUP_ICON = 3, 14
LOAD_LIBRARY_AS_DATAFILE = 0x2


def icon_resources(data: bytes, first: int = 1) -> tuple[list[bytes], bytes]:
    """An .ico file's images and the icon group that lists them, numbered from first.

    The group repeats each image's directory entry with its resource number in place of its offset.
    """
    reserved, kind, count = struct.unpack_from('<HHH', data)
    if reserved != 0 or kind != 1 or count == 0:
        raise RuntimeError('Not an icon file')
    images, group = [], struct.pack('<HHH', 0, 1, count)
    for index in range(count):
        entry = struct.unpack_from('<BBBBHHII', data, 6 + 16 * index)
        size, offset = entry[6], entry[7]
        if offset + size > len(data):
            raise RuntimeError('The icon file is cut short')
        images.append(data[offset : offset + size])
        group += struct.pack('<BBBBHHIH', *entry[:7], first + index)
    return images, group


def _kernel():
    from ctypes import wintypes  # noqa: PLC0415 - Windows only

    kernel = ctypes.WinDLL('kernel32', use_last_error=True)
    kernel.LoadLibraryExW.restype = wintypes.HMODULE
    kernel.LoadLibraryExW.argtypes = [wintypes.LPCWSTR, wintypes.HANDLE, wintypes.DWORD]
    kernel.FreeLibrary.argtypes = [wintypes.HMODULE]
    kernel.BeginUpdateResourceW.restype = wintypes.HANDLE
    kernel.BeginUpdateResourceW.argtypes = [wintypes.LPCWSTR, wintypes.BOOL]
    kernel.UpdateResourceW.argtypes = [
        wintypes.HANDLE, ctypes.c_void_p, ctypes.c_void_p, wintypes.WORD, ctypes.c_char_p,
        wintypes.DWORD,
    ]  # fmt: skip
    kernel.EndUpdateResourceW.argtypes = [wintypes.HANDLE, wintypes.BOOL]
    return kernel


def _resource_name(pointer: int) -> int | str:
    # Below 65536 it is a resource number; anything else points to the name.
    return pointer if pointer < 0x10000 else ctypes.wstring_at(pointer)


def _first_group(kernel, executable: Path) -> tuple[int | str, int, int]:
    """The first icon group's name and language, and the number after the highest icon's."""
    names = ctypes.WINFUNCTYPE(
        ctypes.c_int, ctypes.c_void_p, ctypes.c_void_p, ctypes.c_void_p, ctypes.c_void_p
    )
    languages = ctypes.WINFUNCTYPE(
        ctypes.c_int, ctypes.c_void_p, ctypes.c_void_p, ctypes.c_void_p, ctypes.c_ushort,
        ctypes.c_void_p,
    )  # fmt: skip
    kernel.EnumResourceNamesW.argtypes = [
        ctypes.c_void_p, ctypes.c_void_p, names, ctypes.c_void_p
    ]  # fmt: skip
    kernel.EnumResourceLanguagesW.argtypes = [
        ctypes.c_void_p, ctypes.c_void_p, ctypes.c_void_p, languages, ctypes.c_void_p
    ]  # fmt: skip
    groups, icons, found = [], [], []

    def add_group(_module, _kind, name, _param):
        groups.append(_resource_name(name))
        return True

    def add_icon(_module, _kind, name, _param):
        icons.append(_resource_name(name))
        return True

    def add_language(_module, _kind, _name, language, _param):
        found.append(language)
        return True

    module = kernel.LoadLibraryExW(str(executable), None, LOAD_LIBRARY_AS_DATAFILE)
    if not module:
        raise ctypes.WinError(ctypes.get_last_error())
    try:
        kernel.EnumResourceNamesW(module, RT_GROUP_ICON, names(add_group), None)
        kernel.EnumResourceNamesW(module, RT_ICON, names(add_icon), None)
        if not groups:
            raise RuntimeError(f'{executable.name} has no icon to replace')
        held = ctypes.create_unicode_buffer(groups[0]) if isinstance(groups[0], str) else None
        name = ctypes.cast(held, ctypes.c_void_p).value if held else groups[0]
        kernel.EnumResourceLanguagesW(module, RT_GROUP_ICON, name, languages(add_language), None)
    finally:
        kernel.FreeLibrary(module)
    numbered = [icon for icon in icons if isinstance(icon, int)]
    return groups[0], (found or [0])[0], max(numbered, default=0) + 1


def set_icon(executable: Path, icon: Path) -> None:
    """Replace the first icon group, the one Explorer shows, in its own language.

    The new images take numbers above every existing one, so no other group loses its images.
    """
    kernel = _kernel()
    group_name, language, first = _first_group(kernel, executable)
    images, group = icon_resources(icon.read_bytes(), first)
    held = ctypes.create_unicode_buffer(group_name) if isinstance(group_name, str) else None
    name = ctypes.cast(held, ctypes.c_void_p).value if held else group_name
    update = kernel.BeginUpdateResourceW(str(executable), False)
    if not update:
        raise ctypes.WinError(ctypes.get_last_error())
    written = all(
        kernel.UpdateResourceW(update, RT_ICON, first + index, language, image, len(image))
        for index, image in enumerate(images)
    ) and kernel.UpdateResourceW(update, RT_GROUP_ICON, name, language, group, len(group))
    # Ending with discard set drops a half-written update.
    if not kernel.EndUpdateResourceW(update, not written) or not written:
        raise ctypes.WinError(ctypes.get_last_error())
