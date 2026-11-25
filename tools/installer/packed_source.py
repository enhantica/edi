# SPDX-License-Identifier: BSD-3-Clause
"""Check what the delivered disk images hold, and write a receipt of those that passed.

    python packed_source.py --receipt FILE PATH...

Only macOS opens its disk images, so they are checked where they are made: every volume is mounted
read-only and every file and link on it is checked as tools/ci/stored_source.py checks a file. The
receipt names the SHA-256 of each image and the source commit the lists are of; a disk image
without one may not be stored or published. Other files need no receipt: every check reads them
itself.
"""

from __future__ import annotations

import argparse
import contextlib
import hashlib
import json
import os
import subprocess
import sys
import tempfile
from collections.abc import Iterator
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'tools/ci'))

import source_lists  # noqa: E402
import stored_source  # noqa: E402


@contextlib.contextmanager
def mounted(image: Path) -> Iterator[Path]:
    """The volumes of a disk image, each a folder."""
    with tempfile.TemporaryDirectory() as folder:
        attach = ['hdiutil', 'attach', '-readonly', '-nobrowse', '-mountroot', folder, str(image)]
        subprocess.run(attach, check=True, capture_output=True, input=b'Y\n')
        try:
            yield Path(folder)
        finally:
            for volume in Path(folder).iterdir():
                detach = ['hdiutil', 'detach', '-force', str(volume)]
                subprocess.run(detach, check=False, capture_output=True)


def entries(folder: Path) -> Iterator[Path]:
    """Every file and link; a folder that cannot be listed refuses."""
    for where, folders, names in os.walk(folder, onerror=stored_source.refuse):
        for name in names + [name for name in folders if (Path(where) / name).is_symlink()]:
            yield Path(where) / name


def images(paths: list[Path]) -> Iterator[Path]:
    """The disk images among the delivered files."""
    for root in paths:
        for path in [root] if root.is_file() else entries(root):
            if path.is_file() and stored_source.sealed(path.read_bytes()) == 'a disk image':
                yield path


def checked(paths: list[Path]) -> tuple[dict[str, str], list[str]]:
    """The images by their SHA-256, and what may not be stored."""
    check = stored_source.Check([], withhold=False)
    passed = {}
    for image in images(paths):
        with mounted(image) as volumes:
            held = list(entries(volumes))
            if not held:
                check.found.append(f'{image.name} holds nothing')
            for path in held:
                name = f'{image.name}:{path.relative_to(volumes)}'
                check.file(name, stored_source.link_or_file(path))
        passed[hashlib.sha256(image.read_bytes()).hexdigest()] = image.name
    return passed, check.found


def main() -> int:
    """Check the images; write the receipt only when all of them passed."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--receipt', required=True, type=Path)
    parser.add_argument('paths', nargs='+', type=Path)
    args = parser.parse_args()
    try:
        listed = os.environ['CRYSTA_LISTED_SHA']
        passed, problems = checked(args.paths)
    except stored_source.RefusedError as refusal:
        problems = [str(refusal)]
    except (*stored_source.UNREADABLE, source_lists.UnavailableError, KeyError) as error:
        problems = [f'the check could not finish ({type(error).__name__})']
    for line in problems:
        print(f'packed-source: REFUSED: {line}', file=sys.stderr)
    if problems:
        return 1
    args.receipt.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps({'crysta': listed, 'sha256': dict(sorted(passed.items()))}, indent=1)
    args.receipt.write_text(text + '\n', encoding='utf-8')
    print(f'packed-source: {len(passed)} disk images checked down to their members')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
