# SPDX-License-Identifier: BSD-3-Clause
"""Observe writes in the controlled outside tree, including writes later cleaned up."""

import ctypes
import os
import struct
import sys
from pathlib import Path

# Linux sys/inotify.h: modify, attrib, close-write, moves, create/delete and self changes.
WRITE_EVENTS = (
    0x00000002
    | 0x00000004
    | 0x00000008
    | 0x00000040
    | 0x00000080
    | 0x00000100
    | 0x00000200
    | 0x00000400
    | 0x00000800
)
OVERFLOW = 0x00004000


class Watch:
    def __init__(self, root, destination, *, allow_private_staging=False):
        self.root, self.destination = root, destination
        self.allow_private_staging = allow_private_staging
        self.initial_children = {path.name for path in root.iterdir()}
        self.fd = None
        self.directories = {}

    def __enter__(self):
        if not sys.platform.startswith('linux'):
            return self
        library = ctypes.CDLL(None, use_errno=True)
        library.inotify_init1.argtypes = [ctypes.c_int]
        library.inotify_init1.restype = ctypes.c_int
        library.inotify_add_watch.argtypes = [ctypes.c_int, ctypes.c_char_p, ctypes.c_uint32]
        library.inotify_add_watch.restype = ctypes.c_int
        self.fd = library.inotify_init1(os.O_NONBLOCK | os.O_CLOEXEC)
        if self.fd < 0:
            raise OSError(ctypes.get_errno(), 'Could not observe the outside tree')
        for directory, children, _ in os.walk(self.root, followlinks=False):
            path = Path(directory)
            if self.destination is not None:
                children[:] = [
                    name for name in children if not (path / name).is_relative_to(self.destination)
                ]
            descriptor = library.inotify_add_watch(self.fd, os.fsencode(path), WRITE_EVENTS)
            if descriptor < 0:
                os.close(self.fd)
                self.fd = None
                raise OSError(ctypes.get_errno(), 'Could not watch a controlled outside directory')
            self.directories[descriptor] = path
        return self

    def events(self):
        events = []
        stages = {}
        if self.fd is None:
            return events
        while True:
            try:
                content = os.read(self.fd, 1024 * 1024)
            except BlockingIOError:
                break
            offset = 0
            while offset < len(content):
                descriptor, mask, _, length = struct.unpack_from('iIII', content, offset)
                name = os.fsdecode(content[offset + 16 : offset + 16 + length].rstrip(b'\0'))
                offset += 16 + length
                if mask & OVERFLOW:
                    raise RuntimeError(
                        'The outside-write observation overflowed; safety is unproved'
                    )
                if descriptor not in self.directories or not mask & WRITE_EVENTS:
                    continue
                path = self.directories[descriptor] / name
                if (
                    self.allow_private_staging
                    and mask & 0x40000000
                    and path.parent == self.root
                    and name not in self.initial_children
                ):
                    stages[path] = stages.get(path, 0) | mask
                    continue
                if not path.is_relative_to(self.destination):
                    events.append(path.relative_to(self.root).as_posix())
        for path, mask in stages.items():
            if not (mask & 0x100 and mask & (0x200 | 0x40)) or path.exists() or path.is_symlink():
                events.append(path.relative_to(self.root).as_posix())
        return sorted(set(events))

    def __exit__(self, *_):
        if self.fd is not None:
            os.close(self.fd)
            self.fd = None


class Publications(Watch):
    """Pair kernel move cookies at existing parents, without guessing generated names."""

    def __init__(self, root):
        super().__init__(root, None)

    def changes(self):
        pairs = {}
        creations = []
        if self.fd is None:
            return []
        while True:
            try:
                content = os.read(self.fd, 1024 * 1024)
            except BlockingIOError:
                break
            offset = 0
            while offset < len(content):
                descriptor, mask, cookie, length = struct.unpack_from('iIII', content, offset)
                name = os.fsdecode(content[offset + 16 : offset + 16 + length].rstrip(b'\0'))
                offset += 16 + length
                if mask & OVERFLOW:
                    raise RuntimeError(
                        'The publication observation overflowed; rename is unproved'
                    )
                if descriptor not in self.directories or not mask & 0x40000000:
                    continue
                path = self.directories[descriptor] / name
                if mask & 0x100:
                    creations.append({'kind': 'create', 'destination': path})
                if not cookie:
                    continue
                if mask & 0x40:
                    pairs.setdefault(cookie, {})['source'] = path
                if mask & 0x80:
                    pairs.setdefault(cookie, {})['destination'] = path
        return creations + [
            {'kind': 'rename', **row} for row in pairs.values() if 'destination' in row
        ]
