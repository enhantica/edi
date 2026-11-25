# SPDX-License-Identifier: BSD-3-Clause
"""The crysta source a job holds, as the two lists its output is checked against.

`crysta_fetch.py` writes them beside the checkout: the Git blob id of each source file and the
SHA-256 of each normalised source line. They are read here and never stored or printed.
"""

from __future__ import annotations

import hashlib
import os
import re
from pathlib import Path

BLOBS = 'CRYSTA_SOURCE_BLOB_LIST'
LINES = 'CRYSTA_SOURCE_LINE_LIST'
# A shorter line says nothing about where it came from.
SHORTEST = 12
ANSI = re.compile(rb'\x1b\[[0-?]*[ -/]*[@-~]|\x1b\][^\x07\x1b]*(?:\x07|\x1b\\)')
# What a tool puts before a line it quotes: a compiler's gutter, pytest's markers, a diff's sign,
# a log command, a timestamp.
QUOTES = (
    re.compile(rb'^\s*\d+\s*[|:]\s?'),
    re.compile(rb'^\s*[|>]\s'),
    re.compile(rb'^E\s+'),
    re.compile(rb'^[+-]'),
    re.compile(rb'^::[a-z-]+[^:]*::'),
    re.compile(rb'^\d{4}-\d\d-\d\dT[\d:.]+Z\s'),
)


class UnavailableError(Exception):
    """A list is missing or malformed, so nothing can be checked."""


def line_id(text: bytes) -> str | None:
    """The id of a line as the list has it, or None for one too short to judge."""
    words = text.split()
    if sum(len(word) for word in words) < SHORTEST:
        return None
    return hashlib.sha256(text.strip()).hexdigest()


def readings(line: bytes) -> set[str]:
    """The ids of ``line`` and of what it quotes."""
    found, todo = set(), [ANSI.sub(b'', line)]
    while todo:
        text = todo.pop()
        if (known := line_id(text)) is not None:
            found.add(known)
        for quote in QUOTES:
            bare = quote.sub(b'', text, count=1)
            if bare != text:
                todo.append(bare)
    return found


def _read(variable: str, length: int) -> frozenset[str]:
    try:
        entries = Path(os.environ[variable]).read_text(encoding='ascii').split()
    except (KeyError, OSError, UnicodeError) as error:
        raise UnavailableError(variable) from error
    if not entries or not all(re.fullmatch(f'[0-9a-f]{{{length}}}', entry) for entry in entries):
        raise UnavailableError(variable)
    return frozenset(entries)


def blobs() -> frozenset[str]:
    """The Git blob ids of the source files."""
    return _read(BLOBS, 40)


def lines() -> frozenset[str]:
    """The ids of the source lines."""
    return _read(LINES, 64)


def quotes_source(text: bytes, known: frozenset[str]) -> bool:
    """Whether any line of ``text`` is a source line."""
    return any(not known.isdisjoint(readings(line)) for line in re.split(rb'[\r\n]+', text))


def blob_id(data: bytes) -> str:
    """Git's id of a file with these bytes."""
    return hashlib.sha1(b'blob %d\0' % len(data) + data, usedforsecurity=False).hexdigest()
