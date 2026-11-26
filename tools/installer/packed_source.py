# SPDX-License-Identifier: BSD-3-Clause
"""Check what the delivered disk images hold, and write a receipt of those that passed.

    python packed_source.py --receipt FILE PATH...

Only macOS opens its disk images, so they are checked where they are made: every volume is mounted
read-only and every file, link and extended attribute on it (a resource fork is one) is checked as
tools/ci/stored_source.py checks a file, and the lines of text anywhere in the unpacked image, free
space included. The receipt names the SHA-256 of each image and the source commit the lists are of;
a disk image without one may not be stored or published. Other files need no receipt: every check
reads them itself. A receipt is written also when there are no images, for the commit.
"""

from __future__ import annotations

import argparse
import bz2
import contextlib
import hashlib
import json
import lzma
import os
import plistlib
import re
import struct
import subprocess
import sys
import tempfile
import zlib
from collections.abc import Iterator
from pathlib import Path

# How a disk image packs a stretch: as it is, or compressed; and what holds nothing.
PACKED = {
    1: bytes,
    0x80000005: zlib.decompress,
    0x80000006: bz2.decompress,
    0x80000008: lzma.decompress,
}
EMPTY = {0, 2, 0x7FFFFFFE, 0xFFFFFFFF}
# A byte no line of text has, and more than one is long.
BINARY = re.compile(rb'[\x00-\x08\x0b\x0c\x0e-\x1f]')
LONGEST = 1 << 16
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


def attributes(path: Path) -> Iterator[tuple[str, bytes]]:
    """A file's extended attributes, a link's own."""
    listing = ['xattr', '-s', str(path)]
    listed = subprocess.run(listing, check=True, capture_output=True).stdout.decode()
    for name in listed.splitlines():
        show = ['xattr', '-s', '-px', name, str(path)]
        yield (
            name,
            bytes.fromhex(subprocess.run(show, check=True, capture_output=True).stdout.decode()),
        )


def unpacked(image: bytes) -> Iterator[bytes]:
    """The stretches a disk image packs; one packed in another way refuses."""
    start, length = struct.unpack('>QQ', image[-512:][0xD8:0xE8])
    for table in plistlib.loads(image[start : start + length])['resource-fork']['blkx']:
        entries = table['Data']
        for at in range(204, 204 + 40 * struct.unpack('>I', entries[200:204])[0], 40):
            kind, _, _, _, where, size = struct.unpack('>IIQQQQ', entries[at : at + 40])
            if kind in EMPTY:
                continue
            if kind not in PACKED:
                raise stored_source.RefusedError('a disk image packs its content in another way')
            yield PACKED[kind](image[where : where + size])


def text_in(image: bytes) -> Iterator[bytes]:
    """The lines of text anywhere in a disk image; a program's strings are no lines."""
    held = b''
    for stretch in unpacked(image):
        *found, held = (held + stretch).split(b'\n')
        yield from (line.rstrip(b'\r') for line in found if not BINARY.search(line))
        held = held[-LONGEST:]


def checked(paths: list[Path]) -> tuple[dict[str, str], list[str]]:
    """The images by their SHA-256, and what may not be stored."""
    check = stored_source.Check([], withhold=False)
    passed = {}
    for image in images(paths):
        with mounted(image) as volumes:
            held = [*entries(volumes), *volumes.rglob('*/')]
            if not held:
                check.found.append(f'{image.name} holds nothing')
            for path in held:
                name = f'{image.name}:{path.relative_to(volumes)}'
                if path.is_symlink() or not path.is_dir():
                    check.file(name, stored_source.link_or_file(path))
                for attribute, data in attributes(path):
                    check.file(f'{name}:{attribute}', data)
        if any(check.source.quoted_in_line(line) for line in text_in(image.read_bytes())):
            check.found.append(f'{image.name} quotes a source line')
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
