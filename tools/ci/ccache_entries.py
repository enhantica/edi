# SPDX-License-Identifier: BSD-3-Clause
"""Remove from a compiler cache what may not be stored, before the cache is saved.

    python3 tools/ci/ccache_entries.py DIRECTORY

A result keeps the diagnostics its compile printed beside the object, so each result in the
directory, restored or new, is extracted and its text checked for source lines. One that quotes a
line or cannot be read is deleted, and so is a file of no known kind. Exit 1 if that cannot end.
"""

from __future__ import annotations

import re
import subprocess
import sys
import tempfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import source_lists

# What ccache keeps beside its entries: counters, configuration, locks and unfinished files.
BESIDE = {'stats', 'ccache.conf', 'CACHEDIR.TAG'}
PASSES = 3


def unsafe(entry: Path, blobs: frozenset[str], known: frozenset[str]) -> bool:
    """Whether a cache file may not be saved."""
    inspected = subprocess.run(['ccache', '--inspect', entry], capture_output=True, check=False)
    kind = re.search(rb'^Entry type: \d+ \((\w+)\)', inspected.stdout, flags=re.MULTILINE)
    if inspected.returncode or kind is None:
        return True
    if kind[1] == b'manifest':
        return source_lists.quotes_source(inspected.stdout, known)
    with tempfile.TemporaryDirectory() as scratch:
        extracted = subprocess.run(
            ['ccache', '--extract-result', str(entry.resolve())],
            cwd=scratch,
            capture_output=True,
            check=False,
        )
        outputs = list(Path(scratch).iterdir())
        if extracted.returncode or not outputs:
            return True
        for output in outputs:
            data = output.read_bytes()
            text = b'\0' not in data[:8192]
            if source_lists.blob_id(data) in blobs or (
                text and source_lists.quotes_source(data, known)
            ):
                return True
    return False


def entries(root: Path) -> list[Path]:
    """The cache's own entries; everything else is deleted, or kept when ccache needs it."""
    found = []
    for path in sorted(root.rglob('*')):
        if not path.is_file() and not path.is_symlink():
            continue
        if path.is_symlink() or path.relative_to(root).parts[0] in {'tmp', 'lock'}:
            path.unlink()
        elif path.name not in BESIDE:
            found.append(path)
    return found


def main() -> int:
    """Delete what may not be saved and say how many."""
    root = Path(sys.argv[1]).expanduser()
    if not root.is_dir():
        print(f'ccache-entries: {root} holds no cache')
        return 0
    try:
        blobs, known = source_lists.blobs(), source_lists.lines()
    except source_lists.UnavailableError as missing:
        print(f'ccache-entries: REFUSED: the list {missing} is unavailable', file=sys.stderr)
        return 1
    removed = 0
    for _ in range(PASSES):
        held = entries(root)
        with ThreadPoolExecutor(8) as pool:
            verdicts = pool.map(lambda path: unsafe(path, blobs, known), held)
            bad = [path for path, hit in zip(held, verdicts, strict=True) if hit]
        for path in bad:
            path.unlink()
        removed += len(bad)
        if not bad:
            print(f'ccache-entries: {len(held)} entries kept, {removed} removed')
            return 0
    print('ccache-entries: REFUSED: entries kept appearing', file=sys.stderr)
    return 1


if __name__ == '__main__':
    raise SystemExit(main())
