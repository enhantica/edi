# SPDX-License-Identifier: BSD-3-Clause
"""Check that every tracked path means the same file on every platform.

    python3 tools/ci/portable_paths.py        # this repository's paths; part of the lint job

Refuses a name Windows reads as another: a device with or without an extension (AUX, con.txt), a
drive or stream, a trailing dot or space, a character it has no name for; a name that climbs; two
that differ only by case; and one that is a file and a folder.
"""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


class RefusedError(Exception):
    """A path is another one on some platform."""


# What Windows reads as a device, whatever follows the first dot, and the characters it has no name
# for; a colon starts a drive or a stream.
DEVICE = re.compile(
    r'(?:con|prn|aux|nul|conin\$|conout\$|(?:com|lpt)[0-9\u00b9\u00b2\u00b3])\s*(?:\.|$)'
)
UNNAMEABLE = re.compile(r'[\x00-\x1f<>:"|?*\\]|[. ]$')


def parts_of(name: str) -> tuple[str, ...]:
    """The components of a name that every platform reads alike."""
    parts = tuple(name.split('/'))
    for part in parts:
        if not part or part in {'.', '..'} or UNNAMEABLE.search(part):
            raise RefusedError('a name is another one on some platform')
        if DEVICE.match(part.casefold()):
            raise RefusedError('a name is a device on Windows')
    return parts


def folders_of(names: list[str]) -> set[tuple[str, ...]]:
    """The commit's folders; two spellings of one component refuse, and a file that is a folder."""
    spelled: dict[tuple[str, ...], tuple[str, ...]] = {}
    files = {parts_of(name) for name in names}
    folders = {parts[:depth] for parts in files for depth in range(len(parts))}
    for path in files | folders:
        if spelled.setdefault(tuple(part.casefold() for part in path), path) != path:
            raise RefusedError('two names differ only by case')
    if files & folders:
        raise RefusedError('a name is a file and a folder')
    return folders


def tracked() -> list[str]:
    """The repository's paths; of a copy that is no repository, every file's."""
    listing = ['git', '-C', str(ROOT), 'ls-files', '-z']
    run = subprocess.run(listing, capture_output=True, check=False)
    if run.returncode:
        return [path.relative_to(ROOT).as_posix() for path in ROOT.rglob('*') if path.is_file()]
    return [name for name in run.stdout.decode('utf-8', 'surrogateescape').split('\0') if name]


def main() -> int:
    """Exit 1 with every tracked path that some platform reads otherwise."""
    names = tracked()
    status = 0
    for name in names:
        try:
            parts_of(name)
        except RefusedError as refusal:
            print(f'portable-paths: {name}: {refusal}', file=sys.stderr)
            status = 1
    if not status:
        try:
            folders_of(names)
        except RefusedError as refusal:
            print(f'portable-paths: {refusal}', file=sys.stderr)
            status = 1
    return status


if __name__ == '__main__':
    raise SystemExit(main())
