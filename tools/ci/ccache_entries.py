# SPDX-License-Identifier: BSD-3-Clause
"""Remove from a compiler cache what may not be stored, before the cache is saved.

    python3 tools/ci/ccache_entries.py DIRECTORY

A result keeps the diagnostics its compile printed beside the object, so each result in the
directory, restored or new, is extracted and its text checked for source lines. One that quotes a
line or cannot be read is deleted, and so is every file that is neither an entry nor one of
ccache's own small files with its own content. Exit 1 if that cannot end or there is no cache.
"""

from __future__ import annotations

import re
import subprocess
import sys
import tempfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import source_lists

# ccache's own files: where each may be (its depth in the cache) and what it holds.
TAG = re.compile(
    rb'Signature: 8a477f597d28d172789f06886806bc55\n'
    rb'# This file is a cache directory tag created by ccache\.\n'
    rb'# For information about cache directory tags, see:\n'
    rb'#\thttps?://[a-z./]+\n'
)
COUNTERS = re.compile(rb'(?:\d{1,20}\n)+')
SETTINGS = re.compile(rb'(?:(?:# [ -~]{0,80}|[a-z_]{3,40} = [\w./:~+-]{0,200})?\n)*')
OWN = {
    'CACHEDIR.TAG': ({1, 2}, TAG),
    'stats': ({1, 2, 3}, COUNTERS),
    'ccache.conf': ({1}, SETTINGS),
}
ENTRY = re.compile(r'[0-9a-f]/(?:[0-9a-f]/)?[0-9a-z]{20,64}[RMW]?')
PASSES = 3


def own(root: Path, path: Path) -> bool:
    """Whether a file is one of ccache's own, in its place and with its content."""
    if path.name not in OWN:
        return False
    depths, content = OWN[path.name]
    inside = len(path.relative_to(root).parts) in depths
    return inside and path.stat().st_size < 4096 and bool(content.fullmatch(path.read_bytes()))


def safe(entry: Path, source: source_lists.Source) -> bool:
    """Whether a cache entry may be saved."""
    inspected = subprocess.run(['ccache', '--inspect', entry], capture_output=True, check=False)
    kind = re.search(rb'^Entry type: \d+ \((\w+)\)', inspected.stdout, flags=re.MULTILINE)
    if inspected.returncode or kind is None:
        return False
    if kind[1] == b'manifest':
        return not source.quoted_in(inspected.stdout)
    with tempfile.TemporaryDirectory() as scratch:
        extracted = subprocess.run(
            ['ccache', '--extract-result', str(entry.resolve())],
            cwd=scratch,
            capture_output=True,
            check=False,
        )
        outputs = [path.read_bytes() for path in Path(scratch).iterdir()]
    if extracted.returncode or not outputs:
        return False
    return not any(
        source.is_file(data) or (source_lists.is_text(data) and source.quoted_in(data))
        for data in outputs
    )


def keep(root: Path, path: Path, source: source_lists.Source) -> bool:
    """Whether a file stays in the cache."""
    if path.is_symlink():
        return False
    if own(root, path):
        return True
    return bool(ENTRY.fullmatch(path.relative_to(root).as_posix())) and safe(path, source)


def main() -> int:
    """Delete what may not be saved and say how many."""
    root = Path(sys.argv[1]).expanduser()
    if not root.is_dir() or root.is_symlink():
        print(f'ccache-entries: REFUSED: {root} is not a cache directory', file=sys.stderr)
        return 1
    try:
        source = source_lists.Source()
    except source_lists.UnavailableError as missing:
        print(f'ccache-entries: REFUSED: the list {missing} is unavailable', file=sys.stderr)
        return 1
    removed = 0
    for _ in range(PASSES):
        held = [path for path in sorted(root.rglob('*')) if path.is_symlink() or not path.is_dir()]
        with ThreadPoolExecutor(8) as pool:
            kept = pool.map(lambda path: keep(root, path, source), held)
            bad = [path for path, stays in zip(held, kept, strict=True) if not stays]
        for path in bad:
            path.unlink()
        removed += len(bad)
        if not bad:
            print(f'ccache-entries: {len(held)} files kept, {removed} removed')
            return 0
    print('ccache-entries: REFUSED: files kept appearing', file=sys.stderr)
    return 1


if __name__ == '__main__':
    raise SystemExit(main())
