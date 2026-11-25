# SPDX-License-Identifier: BSD-3-Clause
"""Refuse to store or publish a file that is crysta's source or quotes a line of it.

    python3 tools/ci/stored_source.py [--opaque] PATH...

Every file under the paths (globs too), and every member of a tar, tar.gz, zip or wheel among them,
is compared by its bytes, and a text file by its lines as well. `--opaque` accepts archives of
other kinds, for third-party tools; without it they refuse, as anything unreadable does.
"""

from __future__ import annotations

import argparse
import gzip
import io
import itertools
import os
import sys
import tarfile
import zipfile
from collections.abc import Iterator
from pathlib import Path

import source_lists

OPAQUE = (
    '.7z',
    '.rar',
    '.xz',
    '.bz2',
    '.zst',
    '.lz4',
    '.br',
    '.conda',
    '.dmg',
    '.pkg',
    '.deb',
    '.rpm',
)


class RefusedError(Exception):
    """A file may not be stored, or cannot be judged."""


def inside(name: str, data: bytes) -> list[tuple[str, bytes]]:
    """The files an archive this check can open holds; none for any other file."""
    stream, lower = io.BytesIO(data), name.lower()
    if zipfile.is_zipfile(stream):
        with zipfile.ZipFile(stream) as archive:
            entries = [entry for entry in archive.infolist() if not entry.is_dir()]
            return [(f'{name}:{entry.filename}', archive.read(entry)) for entry in entries]
    if lower.endswith(('.tar', '.tar.gz', '.tgz')):
        with tarfile.open(fileobj=stream) as archive:
            entries = [entry for entry in archive if entry.isfile()]
            return [(f'{name}:{e.name}', archive.extractfile(e).read()) for e in entries]
    if lower.endswith('.gz'):
        return [(name[: -len('.gz')], gzip.decompress(data))]
    return []


UNREADABLE = (OSError, EOFError, RuntimeError, ValueError, tarfile.TarError, zipfile.BadZipFile)


def members(name: str, data: bytes, *, opaque: bool) -> Iterator[tuple[str, bytes]]:
    """The file itself, then each file inside it."""
    yield name, data
    try:
        held = inside(name, data)
    except UNREADABLE as error:
        raise RefusedError(f'{name} cannot be read') from error
    for inner, content in held:
        yield from members(inner, content, opaque=opaque)
    if not held and name.lower().endswith(OPAQUE) and not opaque:
        raise RefusedError(f'{name} is an archive this check cannot open')


def matched(pattern: str) -> list[Path]:
    """What a path or pattern names."""
    path = Path(pattern).expanduser()
    if not any(mark in pattern for mark in '*?['):
        return [path]
    fixed = list(itertools.takewhile(lambda part: not set('*?[') & set(part), path.parts))
    root = Path(*fixed) if fixed else Path()
    return sorted(root.glob(str(Path(*path.parts[len(fixed) :]))))


def files(pattern: str) -> Iterator[Path]:
    """Every file a path or pattern names, links followed as an upload follows them."""
    for root in matched(pattern):
        if root.is_file():
            yield root
        seen = set()
        for folder, names, entries in os.walk(root, followlinks=True):
            real = os.path.realpath(folder)
            if real in seen:
                names.clear()
                continue
            seen.add(real)
            for entry in entries:
                path = Path(folder) / entry
                if path.is_file():
                    yield path
                elif not path.is_symlink():
                    raise RefusedError(f'{path} cannot be read')


def check(paths: list[str], *, opaque: bool) -> list[str]:
    """What may not be stored, by name only."""
    blobs, known = source_lists.blobs(), source_lists.lines()
    found = []
    for pattern in paths:
        for path in files(pattern):
            try:
                data = path.read_bytes()
            except OSError as error:
                raise RefusedError(f'{path} cannot be read') from error
            for name, content in members(str(path), data, opaque=opaque):
                if source_lists.blob_id(content) in blobs:
                    found.append(f'{name} is a source file')
                elif b'\0' not in content[:8192] and source_lists.quotes_source(content, known):
                    found.append(f'{name} quotes a source line')
    return found


def main() -> int:
    """Exit 1, naming the files, when anything may not be stored."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--opaque', action='store_true')
    parser.add_argument('paths', nargs='+')
    args = parser.parse_args()
    try:
        found = check(args.paths, opaque=args.opaque)
    except source_lists.UnavailableError as missing:
        found = [f'the list {missing} is unavailable']
    except RefusedError as refusal:
        found = [str(refusal)]
    for line in found:
        print(f'stored-source: REFUSED: {line}', file=sys.stderr)
    return 1 if found else 0


if __name__ == '__main__':
    raise SystemExit(main())
