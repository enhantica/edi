# SPDX-License-Identifier: BSD-3-Clause
"""The crysta source a job holds, as the lists its output is checked against.

`crysta_fetch.py` writes them beside the checkout: the Git blob id of every source file, the
SHA-256 of every line a person wrote in it, and a short mark of how each line begins. They are read
here and never stored or printed.
"""

from __future__ import annotations

import bisect
import functools
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
PUBLIC = 'CRYSTA_SOURCE_PUBLIC_LIST'
# What the SDK of one commit carries of the source on purpose, and the commits the lists are of.
MEMBERS = 'CRYSTA_SOURCE_MEMBER_LIST'
# A shorter line, or one without a letter, says nothing about where it came from.
SHORTEST = 12
# Part of an output line is source from this length on (a short part is a word or two of anyone's
# code); a part longer than the longest is not looked up.
PART = 24
LONGEST = 1000
# One plain word is not a line of anyone's, and neither is one name or web address with its
# punctuation inside a longer line, also when a source line holds nothing else.
WORD = re.compile(rb'\W*[A-Za-z]+\W*')
NAME = re.compile(rb'\W*(?:[\w.]+|https?://[^\s<>"\']+)\W*')
# Recorded data among the tests (results, logs, structures, measured patterns), the lock and the
# licences are compared as whole files only: single lines of them recur in any tool's output. A
# person wrote the lines of everything else, whatever its kind.
RECORDED = {
    *('.ast', '.bac', '.cif', '.csv', '.dat', '.dic', '.edi', '.f64', '.fou', '.gss', '.gz'),
    *('.hkl', '.int', '.irf', '.json', '.log', '.mcif', '.new', '.oracle', '.out', '.pcr', '.prf'),
    *('.record', '.sum', '.sym', '.symtab', '.tsv', '.txt', '.xy', '.xye', '.xys', '.zip'),
}
# What a tool puts before a line it quotes: a compiler's gutter, pytest's markers, a diff's sign, a
# log command, a timestamp.
QUOTES = (
    re.compile(rb'^\s*\d+\s*[|:]\s?'),
    re.compile(rb'^\s*[|>]\s'),
    re.compile(rb'^E\s+'),
    re.compile(rb'^[+-]'),
    re.compile(rb'^::[a-z-]+[^:]*::'),
    re.compile(rb'^\d{4}-\d\d-\d\dT[\d:.]+Z\s'),
)
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
    if path.name == 'CMakeLists.txt':
        return True
    recorded = path.parts[0] == 'tests' and path.suffix.lower() in RECORDED
    return not (recorded or path.suffix == '.lock' or path.name.endswith('LICENSE'))


def line_id(text: bytes) -> str | None:
    """The id of a line as the list has it, or None for one too short to judge."""
    bare = text.strip()
    if len(b''.join(bare.split())) < SHORTEST or not re.search(rb'[A-Za-z]', bare):
        return None
    if WORD.fullmatch(bare):
        return None
    return hashlib.sha256(bare).hexdigest()


def mark(text: bytes) -> int:
    """The short mark of how a line begins."""
    return zlib.crc32(text[:SHORTEST])


def mark_entry(line: bytes) -> str:
    """A listed line's mark and length, as the list of marks holds them."""
    return f'{mark(line):08x}{min(len(line), 0xFFFF):04x}'


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
            todo += [bare for quote in QUOTES if (bare := quote.sub(b'', part, count=1)) != part]


def spans(text: bytes, marks: dict[int, list[int]] | None) -> Iterator[bytes]:
    """Every part of the line that could be a whole source line."""
    ends = [] if marks is not None else sorted({e.start() for e in ENDS.finditer(text)})
    for begin in BEGINS.finditer(text):
        start = begin.start()
        if marks is not None:
            for length in marks.get(zlib.crc32(text[start : start + SHORTEST]), ()):
                if start + length <= len(text) and ENDS.match(text, start + length):
                    yield text[start : start + length]
            continue
        for end in ends[bisect.bisect_left(ends, start + PART) :]:
            if end > start + LONGEST:
                break
            yield text[start:end]


def sdk_members() -> list[list[str]]:
    """The SDK's members: how each is made, its name and what from; without the list, none."""
    listed = Path(__file__).with_name('sdk-members.txt')
    text = listed.read_text(encoding='utf-8') if listed.is_file() else ''
    return [line.split() for line in text.splitlines() if line and not line.startswith('#')]


class Source:
    """The lists, read once."""

    marks: dict[int, list[int]] | None = None

    def __init__(self) -> None:
        self.lines = _read(LINES, 64)
        if MARKS in os.environ:
            self.marks = {}
            for entry in _read(MARKS, 12):
                if PART <= (length := int(entry[8:], 16)) <= LONGEST:
                    self.marks.setdefault(int(entry[:8], 16), []).append(length)

    @functools.cached_property
    def blobs(self) -> frozenset[str]:
        """The source files' ids; the output filter needs the lines alone."""
        return _read(BLOBS, 40)

    @functools.cached_property
    def public(self) -> frozenset[str]:
        """The files edi publishes itself; without the list none is known."""
        there = PUBLIC in os.environ and Path(os.environ[PUBLIC]).read_bytes().strip()
        return _read(PUBLIC, 40) if there else frozenset()

    def hits(self, line: bytes) -> Iterator[str]:
        """The id of every source line one printed line holds."""
        for text in forms(line):
            if (whole := line_id(text)) is not None and whole in self.lines:
                yield whole
            for span in spans(text, self.marks):
                if NAME.fullmatch(span):
                    continue
                if (part := line_id(span)) is not None and part in self.lines:
                    yield part

    def quoted_in_line(self, line: bytes) -> bool:
        """Whether one printed line holds a source line."""
        return next(self.hits(line), None) is not None

    def quoted_in(self, text: bytes) -> bool:
        """Whether any line of a text holds a source line."""
        return any(self.quoted_in_line(line) for line in re.split(rb'[\r\n]+', text))

    @functools.cached_property
    def members(self) -> dict[str, dict[str, set[str]]]:
        """What each commit's SDK carries: an installed file's name, and its blob or line ids."""
        found: dict[str, dict[str, set[str]]] = {}
        if MEMBERS in os.environ:
            for entry in Path(os.environ[MEMBERS]).read_text(encoding='utf-8').splitlines():
                commit, known, name = entry.split(' ', 2)
                found.setdefault(commit, {}).setdefault(name, set()).add(known)
        return found

    def is_public(self, data: bytes) -> bool:
        """Whether these bytes are a file edi publishes itself."""
        return blob_id(data) in self.public

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
