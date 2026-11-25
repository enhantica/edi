# SPDX-License-Identifier: BSD-3-Clause
"""The crysta source a job holds, as the lists its output is checked against.

`crysta_fetch.py` writes them beside the checkout: the Git blob id of every source file, the
SHA-256 of every line a person wrote in it, and a short mark of how each line begins. They are read
here and never stored or printed.
"""

from __future__ import annotations

import hashlib
import html
import os
import re
import zlib
from collections.abc import Iterator
from pathlib import Path, PurePosixPath

BLOBS = 'CRYSTA_SOURCE_BLOB_LIST'
LINES = 'CRYSTA_SOURCE_LINE_LIST'
MARKS = 'CRYSTA_SOURCE_MARK_LIST'
# A shorter line, or one without a letter, says nothing about where it came from.
SHORTEST = 12
# Part of an output line is source from this length on (a short part is a word or two of anyone's
# code); a part longer than the longest is not looked up.
PART = 24
LONGEST = 1000
# The kinds of file whose lines a person wrote. Recorded data (results, logs, locks, measured
# patterns) is compared as whole files only: single lines of it recur in any tool's output.
WRITTEN = {
    *('.c', '.cc', '.cmake', '.cpp', '.css', '.h', '.hpp', '.html', '.in', '.js', '.md', '.mjs'),
    *('.py', '.sh', '.toml', '.ts', '.yaml', '.yml', '.bat', '.ps1', '.cfg', '.ini'),
}
WRITTEN_NAMES = {'CMakeLists.txt', 'Doxyfile', '.clang-format', '.clang-tidy', '.gitignore'}
ANSI = re.compile(rb'\x1b\[[0-?]*[ -/]*[@-~]|\x1b\][^\x07\x1b]*(?:\x07|\x1b\\)')
ESCAPES = re.compile(rb'\\u([0-9a-fA-F]{4})|\\(.)')
PLAIN = {b'n': b'\n', b't': b'\t', b'r': b'\r', b'b': b' ', b'f': b' '}
# Where quoted text can begin and end inside a line another tool wrote.
BEGINS = re.compile(rb'(?:^|(?<=[\s\'"`<>(\[{=:|,;+*-]))(?=\S)')
ENDS = re.compile(rb'(?<=\S)(?=$|[\s\'"`<>)\]},;|])|(?<=[\'"`>)\]},;])')


class UnavailableError(Exception):
    """A list is missing or malformed, so nothing can be checked."""


def written(name: str) -> bool:
    """Whether a source file's single lines are listed, and not only the file."""
    path = PurePosixPath(name)
    return path.suffix.lower() in WRITTEN or path.name in WRITTEN_NAMES


def line_id(text: bytes) -> str | None:
    """The id of a line as the list has it, or None for one too short to judge."""
    bare = text.strip()
    if len(b''.join(bare.split())) < SHORTEST or not re.search(rb'[A-Za-z]', bare):
        return None
    return hashlib.sha256(bare).hexdigest()


def mark(text: bytes) -> int:
    """The short mark of how a line begins."""
    return zlib.crc32(text[:SHORTEST])


def _escape(match: re.Match[bytes]) -> bytes:
    if match[1]:
        return chr(int(match[1], 16)).encode('utf-8', 'replace')
    return PLAIN.get(match[2], match[2])


def forms(line: bytes) -> Iterator[bytes]:
    """The line as printed, and as it reads when its markup or string escapes are undone."""
    seen, todo = set(), [ANSI.sub(b'', line)]
    while todo:
        text = todo.pop()
        for part in re.split(rb'[\r\n]+', text):
            if part in seen or not part.strip():
                continue
            seen.add(part)
            yield part
            if b'&' in part:
                plain = html.unescape(part.decode('utf-8', 'surrogateescape'))
                todo.append(plain.encode('utf-8', 'surrogateescape'))
            if b'\\' in part:
                todo.append(ESCAPES.sub(_escape, part))


def spans(text: bytes, marks: frozenset[int] | None) -> Iterator[bytes]:
    """Every part of the line that could be a whole source line."""
    ends = None
    for begin in BEGINS.finditer(text):
        start = begin.start()
        if marks is not None and mark(text[start:]) not in marks:
            continue
        if ends is None:
            ends = sorted({end.start() for end in ENDS.finditer(text)} | {len(text)})
        for end in ends:
            if PART <= end - start <= LONGEST:
                yield text[start:end]


class Source:
    """The lists, read once."""

    def __init__(self) -> None:
        self.blobs = _read(BLOBS, 40)
        self.lines = _read(LINES, 64)
        self.marks = None
        if MARKS in os.environ:
            self.marks = frozenset(int(entry, 16) for entry in _read(MARKS, 8))

    def quoted_in_line(self, line: bytes) -> bool:
        """Whether one printed line holds a source line."""
        for text in forms(line):
            if (whole := line_id(text)) is not None and whole in self.lines:
                return True
            for span in spans(text, self.marks):
                if (part := line_id(span)) is not None and part in self.lines:
                    return True
        return False

    def quoted_in(self, text: bytes) -> bool:
        """Whether any line of a text holds a source line."""
        return any(self.quoted_in_line(line) for line in re.split(rb'[\r\n]+', text))

    def is_file(self, data: bytes) -> bool:
        """Whether these bytes are a source file, checked out with either line ending."""
        unix = data.replace(b'\r\n', b'\n')
        return blob_id(data) in self.blobs or blob_id(unix) in self.blobs


def _read(variable: str, length: int) -> frozenset[str]:
    try:
        entries = Path(os.environ[variable]).read_text(encoding='ascii').split()
    except (KeyError, OSError, UnicodeError) as error:
        raise UnavailableError(variable) from error
    if not entries or not all(re.fullmatch(f'[0-9a-f]{{{length}}}', entry) for entry in entries):
        raise UnavailableError(variable)
    return frozenset(entries)


def blob_id(data: bytes) -> str:
    """Git's id of a file with these bytes."""
    return hashlib.sha1(b'blob %d\0' % len(data) + data, usedforsecurity=False).hexdigest()


def is_text(data: bytes) -> bool:
    """Whether a file's lines mean anything."""
    return b'\0' not in data[:8192]
