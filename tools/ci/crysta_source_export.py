# SPDX-License-Identifier: BSD-3-Clause
"""Export crysta's source at a commit out of a checkout, with native paths on every platform.

    python3 tools/ci/crysta_source_export.py CHECKOUT SHA DESTINATION

Every file is written under its own name with the commit's bytes, checked after writing. A name or
link target that could leave the destination by this platform's or Windows' rules refuses.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path, PurePosixPath, PureWindowsPath

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


def inside(name: str) -> PurePosixPath:
    """A name that stays in the destination on every platform."""
    posix, windows = PurePosixPath(name), PureWindowsPath(name)
    anchored = posix.is_absolute() or windows.drive or windows.root
    if anchored or '\\' in name or '..' in posix.parts or not posix.parts:
        raise RefusedError('a path leaves the destination')
    return posix


def target_of(name: str, target: str) -> PurePosixPath:
    """What a link names, as a path of the commit."""
    windows = PureWindowsPath(target)
    if not target or target.startswith('/') or windows.drive or windows.root or '\\' in target:
        raise RefusedError('a link leaves the destination')
    parts = list(inside(name).parent.parts)
    for part in PurePosixPath(target).parts:
        if part == '..':
            if not parts:
                raise RefusedError('a link leaves the destination')
            parts.pop()
        else:
            parts.append(part)
    return inside('/'.join(parts))


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


def export(checkout: str, sha: str, destination: Path) -> None:
    """Write the commit, links as links where the platform follows them, else as copies."""
    listed = entries(checkout, sha)
    data = blobs(checkout, sorted({blob for _, blob, _ in listed}))
    folder = {name.casefold() for _, _, name in listed}
    if len(folder) != len(listed):
        raise RefusedError('two names differ only by case')
    if destination.is_symlink() or (destination.exists() and any(destination.iterdir())):
        raise RefusedError('the destination is not a new folder')
    destination.mkdir(parents=True, exist_ok=True)
    links = []
    for mode, blob, name in listed:
        path = destination.joinpath(*inside(name).parts)
        path.parent.mkdir(parents=True, exist_ok=True)
        if mode == '120000':
            links.append((path, name, data[blob].decode()))
            continue
        path.write_bytes(data[blob])
        path.chmod(0o755 if mode == '100755' else 0o644)
        if source_lists.blob_id(path.read_bytes()) != blob:
            raise RefusedError('a written file differs from the commit')
    for path, name, target in links:
        named = destination.joinpath(*target_of(name, target).parts)
        if os.name != 'nt':
            path.symlink_to(target)
        elif named.is_file() and not named.is_symlink():
            shutil.copyfile(named, path)
        else:
            raise RefusedError('a link names no file of the commit')


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
