# SPDX-License-Identifier: BSD-3-Clause
"""Export crysta's source at a commit out of a checkout, with native paths on every platform.

    python3 tools/ci/crysta_source_export.py CHECKOUT SHA DESTINATION

The whole commit is judged before anything is written. A name must mean the same file on every
platform: none that is absolute, climbs, or that Windows reads as another (a drive, a stream, a
device, a trailing dot, another case). A link must name a file of the commit along its own folders.
Each file is checked after it is written; a failure removes what was written.
"""

from __future__ import annotations

import os
import re
import shutil
import subprocess
import sys
from pathlib import Path, PurePosixPath

sys.path.insert(0, str(Path(__file__).resolve().parent))

import source_lists


class RefusedError(Exception):
    """The commit cannot be exported as it is."""


def git(checkout: str, *args: str, stdin: bytes | None = None) -> bytes:
    """Run git quietly."""
    run = subprocess.run(
        ['git', '-C', checkout, *args], input=stdin, capture_output=True, check=False
    )
    if run.returncode:
        raise RefusedError(f'git {args[0]} exited {run.returncode}')
    return run.stdout


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


def target_of(name: str, target: str, folders: set[tuple[str, ...]]) -> str:
    """The name a link leads to, through folders of the commit only, never another link."""
    if (
        not target
        or target.startswith('/')
        or UNNAMEABLE.search(target.replace('/', '').rstrip('.'))
    ):
        raise RefusedError('a link leaves the destination')
    here = parts_of(name)[:-1]
    for part in PurePosixPath(target).parts:
        if here not in folders or (part == '..' and not here):
            raise RefusedError('a link leaves the destination')
        here = here[:-1] if part == '..' else (*here, part)
    return '/'.join(parts_of('/'.join(here)))


def entries(checkout: str, sha: str) -> list[tuple[str, str, str]]:
    """The commit's files and links: mode, blob and name."""
    listed = git(checkout, 'ls-tree', '-r', '-z', sha).decode('utf-8', 'surrogateescape')
    found = []
    for entry in filter(None, listed.split('\0')):
        head, name = entry.split('\t', 1)
        mode, kind, blob = head.split()
        if kind != 'blob' or mode not in {'100644', '100755', '120000'}:
            raise RefusedError('the commit holds more than files and links')
        found.append((mode, blob, name))
    return found


def blobs(checkout: str, ids: list[str]) -> dict[str, bytes]:
    """The bytes of each blob."""
    out = git(checkout, 'cat-file', '--batch', stdin='\n'.join(ids).encode())
    found, at = {}, 0
    while at < len(out):
        end = out.index(b'\n', at)
        blob, _, size = out[at:end].split()
        found[blob.decode()] = out[end + 1 : end + 1 + int(size)]
        at = end + 2 + int(size)
    return found


def plan(checkout: str, sha: str) -> list[tuple[str, bytes, str, str]]:
    """Each file's name, bytes, mode and, for a link, what it names; the bytes are its file's."""
    listed = entries(checkout, sha)
    data = blobs(checkout, sorted({blob for _, blob, _ in listed}))
    if any(source_lists.blob_id(data[blob]) != blob for _, blob, _ in listed):
        raise RefusedError('a file differs from the commit')
    folders = folders_of([name for _, _, name in listed])
    files = {name: data[blob] for mode, blob, name in listed if mode != '120000'}
    planned = []
    for mode, blob, name in listed:
        if mode != '120000':
            planned.append((name, data[blob], mode, ''))
            continue
        target = data[blob].decode()
        named = target_of(name, target, folders)
        if named not in files:
            raise RefusedError('a link names no file of the commit')
        planned.append((name, files[named], mode, target))
    return planned


def write(destination: Path, name: str, data: bytes, mode: str, target: str) -> None:
    """One file or link, read back."""
    path = destination.joinpath(*name.split('/'))
    path.parent.mkdir(parents=True, exist_ok=True)
    if target and os.name != 'nt':
        path.symlink_to(target)
    else:
        path.write_bytes(data)
        path.chmod(0o755 if mode == '100755' else 0o644)
    if path.read_bytes() != data:
        raise RefusedError('a written file differs from the commit')


def export(checkout: str, sha: str, destination: Path) -> None:
    """Write the commit, links where the platform has them, else as copies of their file."""
    planned = plan(checkout, sha)
    if destination.is_symlink() or (destination.exists() and any(destination.iterdir())):
        raise RefusedError('the destination is not a new folder')
    destination.mkdir(parents=True, exist_ok=True)
    try:
        for entry in sorted(planned, key=lambda entry: bool(entry[3])):
            write(destination, *entry)
    except BaseException:
        shutil.rmtree(destination, ignore_errors=True)
        raise


def main() -> int:
    """Export, or exit 1 with the reason and nothing of the source."""
    checkout, sha, destination = sys.argv[1], sys.argv[2], Path(sys.argv[3])
    try:
        export(checkout, sha, destination)
    except (RefusedError, OSError, ValueError) as error:
        reason = str(error) if isinstance(error, RefusedError) else type(error).__name__
        print(f'source-export: REFUSED: {reason}', file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
