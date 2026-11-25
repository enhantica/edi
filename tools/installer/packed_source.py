# SPDX-License-Identifier: BSD-3-Clause
"""Check what the delivered installers and component archives really hold, and write a receipt.

    python packed_source.py --devtool IFW/bin/devtool --receipt FILE PATH...

Opens each delivered file down to its members: a zip, a 7z archive, a disk image (mounted
read-only) and an installer (its own archives, taken out by the Framework's devtool). Every member
is checked as tools/ci/stored_source.py checks a file. The receipt names the SHA-256 of each
delivered file whose members all passed; only those may be published.
"""

from __future__ import annotations

import argparse
import contextlib
import hashlib
import json
import os
import platform
import subprocess
import sys
import tempfile
import zipfile
from collections.abc import Iterator
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'tools/ci'))

import source_lists  # noqa: E402
import stored_source  # noqa: E402


class RefusedError(Exception):
    """A delivered file cannot be opened down to its members."""


def digest(data: bytes) -> str:
    """The SHA-256 of these bytes."""
    return hashlib.sha256(data).hexdigest()


def walk(folder: Path) -> Iterator[Path]:
    """Every file in a folder; one that cannot be listed refuses."""
    for where, _, names in os.walk(folder, onerror=stored_source.refuse):
        for name in names:
            path = Path(where) / name
            if not path.is_symlink():
                yield path


@contextlib.contextmanager
def mounted(image: Path, scratch: Path) -> Iterator[Path]:
    """A disk image's files."""
    if platform.system() != 'Darwin':
        raise RefusedError(f'{image.name} is a disk image, which only macOS opens')
    point = scratch / 'image'
    point.mkdir()
    attach = ['hdiutil', 'attach', '-readonly', '-nobrowse', '-mountpoint', str(point), str(image)]
    subprocess.run(attach, check=True, capture_output=True, input=b'Y\n')
    try:
        yield point
    finally:
        subprocess.run(
            ['hdiutil', 'detach', '-force', str(point)], check=False, capture_output=True
        )


class Packed:
    """One run over the delivered files."""

    def __init__(self, devtool: Path) -> None:
        self.devtool = devtool
        self.check = stored_source.Check([], withhold=False)

    def open(self, path: Path) -> None:
        """Check a file, or what it holds when it is an installer or a disk image."""
        data = path.read_bytes()
        kind = stored_source.sealed(data)
        if kind is None:
            self.members(path, data)
            return
        with tempfile.TemporaryDirectory() as folder:
            scratch = Path(folder)
            if kind == 'a disk image':
                with mounted(path, scratch) as files:
                    self.all(files)
            elif kind == 'an installer':
                held = scratch / 'held'
                dump = [str(self.devtool), 'dump', str(path), str(held)]
                run = subprocess.run(dump, check=False, capture_output=True)
                if run.returncode or not held.is_dir() or not any(walk(held)):
                    raise RefusedError(f'{path.name} does not give its archives')
                self.all(held)
            else:
                raise RefusedError(f'{path.name} is {kind}')

    def members(self, path: Path, data: bytes) -> None:
        """An ordinary file, or an archive whose members may be installers."""
        if zipfile.is_zipfile(path):
            with tempfile.TemporaryDirectory() as folder, zipfile.ZipFile(path) as archive:
                archive.extractall(folder)
                self.all(Path(folder))
            return
        if data[:6] == b"7z\xbc\xaf'\x1c":
            with tempfile.TemporaryDirectory() as folder:
                for count, (name, content) in enumerate(stored_source.seven_members(data)):
                    member = Path(folder) / f'{count}-{Path(name).name}'
                    member.write_bytes(content)
                    self.open(member)
            return
        self.check.file(str(path.name), data)

    def all(self, folder: Path) -> None:
        """Every file in a folder."""
        for path in walk(folder):
            self.open(path)


def main() -> int:
    """Check the delivered files; write the receipt only when all of them passed."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--devtool', required=True, type=Path)
    parser.add_argument('--receipt', required=True, type=Path)
    parser.add_argument('paths', nargs='+', type=Path)
    args = parser.parse_args()
    passed, problems = {}, []
    try:
        packed = Packed(args.devtool)
        for root in args.paths:
            for path in [root] if root.is_file() else walk(root):
                packed.open(path)
                passed[digest(path.read_bytes())] = path.name
        problems = packed.check.found
    except (RefusedError, stored_source.RefusedError, subprocess.CalledProcessError) as error:
        problems = [str(error) if 'Refused' in type(error).__name__ else type(error).__name__]
    except (source_lists.UnavailableError, OSError, ValueError, RuntimeError) as error:
        problems = [f'the check could not finish ({type(error).__name__}: {error})']
    for line in problems:
        print(f'packed-source: REFUSED: {line}', file=sys.stderr)
    if problems:
        return 1
    args.receipt.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps({'sha256': dict(sorted(passed.items()))}, indent=1)
    args.receipt.write_text(text + '\n', encoding='utf-8')
    print(f'packed-source: {len(passed)} delivered files checked down to their members')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
