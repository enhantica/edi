# SPDX-License-Identifier: BSD-3-Clause
"""Everything an Installer Framework program carries, read from its bytes.

The Framework appends its content to a program: Qt resource files, the operations, the archives by
package, and an index that ends with its marker. Nothing of that stretch may be left over: a part
no index names refuses, so what is returned is all there is. `tools/ci/stored_source.py` reads
installers with it on every platform.
"""

from __future__ import annotations

import re
import struct
import zlib
from collections.abc import Callable

# The index ends with the kind of program and one of two numbers.
END = re.compile(rb'[\x32-\x36]\x32\x02\x12\0{4}[\xf8\xf9]\x68\xd6\x99\x1c\x0a\x63\xc2')


class UnreadableError(ValueError):
    """The content does not have the Framework's form."""


def carries(data: bytes) -> bool:
    """Whether a program has content appended to it."""
    return END.search(data) is not None


def need(fact: object, what: str) -> None:
    """Refuse a form that is not the Framework's."""
    if not fact:
        raise UnreadableError(what)


class Reader:
    """A stretch of bytes read from the front."""

    def __init__(self, data: bytes) -> None:
        self.data = data
        self.at = 0

    def take(self, count: int) -> bytes:
        """The next bytes."""
        need(0 <= count <= len(self.data) - self.at, 'the content is cut short')
        self.at += count
        return self.data[self.at - count : self.at]

    def number(self) -> int:
        """The next 64-bit number."""
        return struct.unpack('<q', self.take(8))[0]

    def name(self) -> str:
        """The next name."""
        return self.take(self.number()).decode('utf-8', 'surrogateescape')


def tiles(parts: list[tuple[int, int]], start: int, end: int) -> None:
    """The parts cover the stretch, each byte once."""
    at = start
    for where, length in sorted(set(parts)):
        need(where == at and length >= 0, 'a part of the content has no name')
        at += length
    need(at == end, 'a part of the content has no name')


def content(data: bytes, zstandard: Callable[[bytes], bytes]) -> list[tuple[str, bytes]]:
    """Every file the program carries."""
    ends = [match.end() for match in END.finditer(data)]
    need(len(ends) == 1, 'the content has more than one end')
    end = ends[0]
    size, count = (struct.unpack('<q', data[end - back : end - back + 8])[0] for back in (24, 32))
    index = end - 32 - 16 * (count + 2)
    need(0 < size <= end and 0 <= count < 1000 and index >= end - size, 'the index is cut short')
    body = data[end - size : index]
    pairs = [struct.unpack('<qq', data[at : at + 16]) for at in range(index, end - 32, 16)]
    (table, table_length), *metas, (operations, operations_length) = pairs
    need(operations_length == 16 and not any(body[operations:][:16]), 'it carries operations')
    need(table + table_length == len(body), 'a part of the content has no name')
    tiles([*metas, (operations, operations_length)], 0, operations + operations_length)
    found = []
    for where, length in metas:
        found += resources(body[where : where + length], zstandard)
    return found + collections(body, operations + operations_length, table)


def collections(body: bytes, start: int, table: int) -> list[tuple[str, bytes]]:
    """The packages' archives, between the operations and the table that names them."""
    need(0 <= start <= table - 8, 'the content is cut short')
    named = Reader(body[table:])
    entries = [(named.name(), named.number(), named.number()) for _ in range(named.number())]
    need(named.number() == len(entries) and named.at == len(named.data), 'the table differs')
    need(struct.unpack('<q', body[start : start + 8])[0] == len(entries), 'the table differs')
    tiles([(where, length) for _, where, length in entries], start + 8, table)
    found = []
    for package, where, length in entries:
        held = Reader(body[where : where + length])
        files = [(held.name(), held.number(), held.number()) for _ in range(held.number())]
        tiles([(at, size) for _, at, size in files], where + held.at, where + length)
        found += [(f'{package}/{name}', body[at : at + size]) for name, at, size in files]
    return found


def resources(data: bytes, zstandard: Callable[[bytes], bytes]) -> list[tuple[str, bytes]]:
    """Every file of a Qt resource file."""
    need(data[:4] == b'qres' and len(data) >= 24, 'it is no Qt resource file')
    version, tree, held, names = struct.unpack('>4I', data[4:20])
    need(version in {1, 2, 3}, 'the Qt resource file is of another version')
    step = 14 if version == 1 else 22
    found: list[tuple[str, bytes]] = []
    parts: list[tuple[int, int]] = []

    def name(at: int) -> str:
        length = struct.unpack('>H', data[names + at : names + at + 2])[0]
        return data[names + at + 6 : names + at + 6 + 2 * length].decode('utf-16-be')

    def walk(node: int, where: str, depth: int) -> None:
        need(depth < 64, 'the Qt resource file is too deep')
        at = tree + node * step
        offset, flags = struct.unpack('>IH', data[at : at + 6])
        here = where if not node else f'{where}/{name(offset)}'
        if flags & 2:
            count, first = struct.unpack('>II', data[at + 6 : at + 14])
            for child in range(first, first + count):
                walk(child, here, depth + 1)
            return
        start = struct.unpack('>I', data[at + 10 : at + 14])[0]
        length = struct.unpack('>I', data[held + start : held + start + 4])[0]
        packed = data[held + start + 4 : held + start + 4 + length]
        need(len(packed) == length, 'the Qt resource file is cut short')
        parts.append((held + start, 4 + length))
        if flags & 1:
            packed = zlib.decompress(packed[4:])
        elif flags & 4:
            packed = zstandard(packed)
        found.append((here, packed))

    walk(0, '', 0)
    after = min(at for at in (tree, names, len(data)) if at >= held)
    tiles(parts, held, after)
    return found
