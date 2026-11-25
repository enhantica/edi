# SPDX-License-Identifier: BSD-3-Clause
"""Refuse to store or publish a file that is crysta's source or holds a line of it.

    python3 tools/ci/stored_source.py [--withhold] [--receipt PATH]... PATH...

Run on exactly the paths that are stored, right before they are. Every file, and every member of an
archive, is compared by its bytes, and a text file by its lines as well. An archive is known by its
first bytes, not its name. One this check cannot open, an installer and a disk image refuse unless
a receipt names their bytes, as a folder or file that cannot be read does. The SDK's own members
are those sdk-members.txt names. `--withhold` replaces a source line in a text file (diagnostics
only).
"""

from __future__ import annotations

import argparse
import bz2
import gzip
import hashlib
import io
import itertools
import json
import lzma
import os
import re
import subprocess
import sys
import tarfile
import zipfile
from collections.abc import Iterator
from pathlib import Path

import source_lists

ROOT = Path(__file__).resolve().parents[2]
LOCKS = [
    lock for lock in (ROOT / 'pixi.lock', ROOT / 'tools/installer/pixi.lock') if lock.is_file()
]
MEMBERS = Path(__file__).with_name('sdk-members.txt')
SDK = re.compile(r'(?:^|/)crysta-sdk-[0-9a-f]{40}-(?:linux-64|osx-arm64|win-64)\.tar\.gz$')
# The Installer Framework ends an installer's own archives with its marker and one of two numbers.
INSTALLER = re.compile(rb'[\x32-\x36]\x32\x02\x12\0{4}[\xf8\xf9]\x68\xd6\x99\x1c\x0a\x63\xc2')
SEALED = {
    b'Rar!\x1a\x07': 'a RAR archive',
    b'\x04\x22\x4d\x18': 'an LZ4 stream',
    b'MSCF': 'a cabinet',
    b'xar!': 'a macOS package',
    b'\xed\xab\xee\xdb': 'an RPM package',
    b'!<arch>\ndebian': 'a Debian package',
}
UNREADABLE = (
    *(OSError, EOFError, RuntimeError, ValueError, zipfile.BadZipFile, lzma.LZMAError),
    *(tarfile.TarError, ImportError, subprocess.SubprocessError),
)


class RefusedError(Exception):
    """A file may not be stored, or cannot be judged."""


def tar_members(data: bytes) -> list[tuple[str, bytes]]:
    """A tar's files; a link holds no bytes, anything else is not a file an upload makes."""
    found = []
    with tarfile.open(fileobj=io.BytesIO(data)) as archive:
        for entry in archive:
            if entry.isreg() or entry.islnk():
                found.append((entry.name, archive.extractfile(entry).read()))
            elif entry.issym():
                found.append((entry.name, entry.linkname.encode()))
            elif not entry.isdir():
                raise ValueError(entry.name)
    return found


def seven_members(data: bytes) -> list[tuple[str, bytes]]:
    """A 7z archive's files, where py7zr is installed."""
    import py7zr  # noqa: PLC0415 - the packaging environment has it, others meet no 7z

    factory = py7zr.io.BytesIOFactory(1 << 31)
    with py7zr.SevenZipFile(io.BytesIO(data)) as archive:
        archive.extractall(factory=factory)  # noqa: S202 - into memory
    return [(name, held.read()) for name, held in factory.products.items()]


def zip_members(data: bytes) -> list[tuple[str, bytes]]:
    """A zip's files."""
    with zipfile.ZipFile(io.BytesIO(data)) as archive:
        entries = [entry for entry in archive.infolist() if not entry.is_dir()]
        return [(entry.filename, archive.read(entry)) for entry in entries]


def zstandard(data: bytes) -> bytes:
    """A Zstandard stream's bytes, by the standard library (3.14) or the zstd program."""
    try:
        from compression import zstd  # noqa: PLC0415 - not in every runner's Python
    except ImportError:
        command = ['zstd', '-dcq', '--long=31']
        return subprocess.run(command, input=data, capture_output=True, check=True).stdout
    return zstd.decompress(data)


ZSTANDARD = b'\x28\xb5\x2f\xfd'
STREAMS = {
    b'\x1f\x8b': gzip.decompress,
    b'BZh': bz2.decompress,
    b'\xfd7zXZ\0': lzma.decompress,
    ZSTANDARD: zstandard,
}
PACKED = (*STREAMS, b'PK', b"7z\xbc\xaf'\x1c")


def unpacked(name: str, data: bytes) -> list[tuple[str, bytes]] | None:
    """What the file holds, or None when it is not an archive."""
    for start, decompress in STREAMS.items():
        if data.startswith(start):
            return [('', decompress(data))]
    if data.startswith(b"7z\xbc\xaf'\x1c"):
        return seven_members(data)
    if data[257:262] == b'ustar' or name.lower().endswith('.tar'):
        return tar_members(data)
    if zipfile.is_zipfile(io.BytesIO(data)) and not installer(data):
        return zip_members(data)
    return None


def installer(data: bytes) -> bool:
    """Whether a file carries archives the Framework appended to it."""
    tar = data[257:262] == b'ustar'
    return not tar and not data.startswith(PACKED) and INSTALLER.search(data) is not None


def sealed(data: bytes) -> str | None:
    """Why a file's content cannot be seen here."""
    for start, kind in SEALED.items():
        if data.startswith(start):
            return kind
    if data[-512:-508] == b'koly':
        return 'a disk image'
    return 'an installer' if installer(data) else None


class Check:
    """One run over the paths that are about to be stored."""

    def __init__(self, receipts: list[Path], *, withhold: bool) -> None:
        self.source = source_lists.Source()
        self.source.blobs  # noqa: B018 - a missing list refuses even when nothing is stored
        self.withhold = withhold
        self.approved = locked()
        for receipt in receipts:
            named = sorted(receipt.rglob('*.json')) if receipt.is_dir() else [receipt]
            if not named:
                raise RefusedError(f'{receipt} holds no receipt')
            for file in named:
                self.approved |= set(json.loads(file.read_text(encoding='utf-8'))['sha256'])
        self.found: list[str] = []

    def file(self, name: str, data: bytes, *, sdk: bool = False) -> None:
        """Judge one file and everything in it."""
        if hashlib.sha256(data).hexdigest() in self.approved or self.source.is_public(data):
            return
        if kind := sealed(data):
            self.found.append(f'{name} is {kind} no receipt names')
            return
        if self.source.is_file(data):
            self.found.append(f'{name} is a source file')
            return
        try:
            held = unpacked(name, data)
        except UNREADABLE:
            self.found.append(f'{name} cannot be read')
            return
        if held is None:
            if source_lists.is_text(data) and self.source.quoted_in(data):
                self.found.append(f'{name} quotes a source line')
            return
        names = sdk_members() if sdk or SDK.search(name) else None
        for member, content in held:
            if not member:
                self.file(name, content, sdk=names is not None)
            elif names is None:
                self.file(f'{name}:{member}', content)
            else:
                self.sdk_member(name, member, content, names)

    def sdk_member(self, name: str, member: str, data: bytes, names: dict[str, str]) -> None:
        """A member of the SDK archive: one the list names, and a copy only where it says so."""
        for pattern, kind in names.items():
            if Path(member).match(pattern) and member.count('/') == pattern.count('/'):
                installed = kind == 'copy' and self.source.is_file(data)
                if not installed and kind != 'template':
                    self.file(f'{name}:{member}', data)
                return
        self.found.append(f'{name}:{member} is not a member the SDK may have')

    def path(self, path: Path) -> None:
        """Judge a file on disk, withholding its lines where that is asked."""
        data = path.read_bytes()
        if self.withhold and source_lists.is_text(data) and not self.source.is_file(data):
            kept = [
                b'[source line withheld]\n' if self.source.quoted_in_line(line) else line
                for line in data.splitlines(keepends=True)
            ]
            if (shown := b''.join(kept)) != data:
                path.write_bytes(shown)
                data = shown
        self.file(str(path), data)


def sdk_members() -> dict[str, str]:
    """The SDK's members and how each is made (sdk-members.txt)."""
    lines = MEMBERS.read_text(encoding='utf-8').splitlines()
    entries = [line.split() for line in lines if line and not line.startswith('#')]
    return {pattern: kind for kind, pattern in entries}


def locked() -> set[str]:
    """The third-party packages edi's committed locks name, by their bytes."""
    found = set()
    for lock in LOCKS:
        found |= set(re.findall(r'sha256: ([0-9a-f]{64})', lock.read_text(encoding='utf-8')))
    return found


def matched(pattern: str) -> list[Path]:
    """What a path or pattern names."""
    path = Path(pattern).expanduser()
    if not any(mark in pattern for mark in '*?['):
        return [path]
    fixed = list(itertools.takewhile(lambda part: not set('*?[') & set(part), path.parts))
    root = Path(*fixed) if fixed else Path()
    return sorted(root.glob(str(Path(*path.parts[len(fixed) :]))))


def refuse(error: OSError) -> None:
    """A directory that cannot be listed is not an empty one."""
    raise RefusedError(f'{error.filename} cannot be read') from error


def files(pattern: str) -> Iterator[Path]:
    """Every file a path or pattern names, links followed as an upload follows them."""
    for root in matched(pattern):
        if root.is_file():
            yield root
            continue
        # What is not there is not stored; a folder that cannot be listed refuses below.
        if not root.exists():
            continue
        seen = set()
        for folder, names, entries in os.walk(root, followlinks=True, onerror=refuse):
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
                    raise RefusedError(f'{path} is no ordinary file')


def run(args: argparse.Namespace) -> list[str]:
    """What may not be stored, by name only."""
    try:
        check = Check(args.receipt, withhold=args.withhold)
        for path in itertools.chain.from_iterable(map(files, args.paths)):
            check.path(path)
    except source_lists.UnavailableError as missing:
        return [f'the list {missing} is unavailable']
    except RefusedError as refusal:
        return [str(refusal)]
    except (OSError, ValueError, KeyError) as error:
        return [f'the check could not finish ({type(error).__name__})']
    return check.found


def main() -> int:
    """Exit 1, naming the files, when anything may not be stored."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--withhold', action='store_true')
    parser.add_argument('--receipt', action='append', default=[], type=Path)
    parser.add_argument('paths', nargs='+')
    found = run(parser.parse_args())
    for line in found:
        print(f'stored-source: REFUSED: {line}', file=sys.stderr)
    return 1 if found else 0


if __name__ == '__main__':
    raise SystemExit(main())
