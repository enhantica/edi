# SPDX-License-Identifier: BSD-3-Clause
"""Refuse to store or publish a file that is crysta's source or holds a line of it.

    python3 tools/ci/stored_source.py [--withhold] [--receipt PATH]... PATH...

Run on exactly the paths that are stored, right before they are. Every file, and every entry of an
archive or installer as the container has it, is compared by its bytes, and a text file by its
lines as well. A container is known by its first bytes, not its name; one this check cannot open
refuses, as a folder or file that cannot be read does. A disk image refuses unless a receipt names
its bytes and the source commit it was checked against, and the lists are of that commit too. The
SDK's own members are those sdk-members.txt names, in an archive of a listed commit. `--withhold`
replaces a source line in a text file (diagnostics only).
"""

from __future__ import annotations

import argparse
import bz2
import fnmatch
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
import tempfile
import zipfile
from collections.abc import Callable, Iterator
from pathlib import Path

import installer_content
import source_lists

ROOT = Path(__file__).resolve().parents[2]
LOCKS = [
    lock for lock in (ROOT / 'pixi.lock', ROOT / 'tools/installer/pixi.lock') if lock.is_file()
]
SDK = re.compile(r'(?:^|/)crysta-sdk-([0-9a-f]{40})-(linux-64|osx-arm64|win-64)\.tar\.gz$')
MANIFEST = 'share/crysta-sdk/manifest.json'
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
    """A tar's entries, each as often as it has it; a link's is what it names."""
    found = []
    with tarfile.open(fileobj=io.BytesIO(data)) as archive:
        for entry in archive:
            if entry.isreg():
                found.append((entry.name, archive.extractfile(entry).read()))
            elif entry.issym() or entry.islnk():
                found.append((entry.name, entry.linkname.encode()))
            elif not entry.isdir():
                raise ValueError(entry.name)
    return found


def seven_members(data: bytes) -> list[tuple[str, bytes]]:
    """A 7z archive's entries, by py7zr (the packaging environment has it) or the 7z program."""
    try:
        import py7zr  # noqa: PLC0415 - not in every runner's Python
    except ImportError:
        return seven_program(data)
    factory = py7zr.io.BytesIOFactory(1 << 31)
    with py7zr.SevenZipFile(io.BytesIO(data)) as archive:
        listed = [entry.filename for entry in archive.list() if not entry.is_directory]
        archive.extractall(factory=factory)  # noqa: S202 - into memory
    found = [(name, held.read()) for name, held in factory.products.items()]
    if len(listed) != len({alias(name) for name in listed}) or len(found) != len(listed):
        raise ValueError('an entry is hidden by another')
    return found


def seven_program(data: bytes) -> list[tuple[str, bytes]]:
    """A 7z archive's entries, by the 7z program."""
    with tempfile.TemporaryDirectory() as folder:
        packed, held = Path(folder) / 'packed.7z', Path(folder) / 'held'
        packed.write_bytes(data)
        listing = ['7z', 'l', '-slt', '-ba', '-sccUTF-8', str(packed)]
        text = subprocess.run(listing, capture_output=True, check=True).stdout.decode()
        entries = [
            dict(line.split(' = ', 1) for line in entry.splitlines() if ' = ' in line)
            for entry in re.split(r'\n\s*\n', text)
            if 'Path = ' in entry
        ]
        listed = [e['Path'] for e in entries if not e.get('Attributes', '').startswith('D')]
        unpack = ['7z', 'x', '-y', '-bd', f'-o{held}', str(packed)]
        subprocess.run(unpack, capture_output=True, check=True)
        found = [
            (path.relative_to(held).as_posix(), link_or_file(path))
            for path in sorted(held.rglob('*'))
            if path.is_symlink() or path.is_file()
        ]
    if len(listed) != len({alias(name) for name in listed}) or len(found) != len(listed):
        raise ValueError('an entry is hidden by another')
    return found


def alias(name: str) -> str:
    """What a name is on the least particular file system."""
    return name.replace('\\', '/').casefold()


def link_or_file(path: Path) -> bytes:
    """A file's bytes, or what a link names."""
    return os.fsencode(path.readlink()) if path.is_symlink() else path.read_bytes()


def zip_members(data: bytes) -> list[tuple[str, bytes]]:
    """A zip's entries, each as often as it has it."""
    with zipfile.ZipFile(io.BytesIO(data)) as archive:
        entries = [e for e in archive.infolist() if e.file_size or not e.is_dir()]
        return [(entry.filename, archive.read(entry)) for entry in entries]


def zstandard(data: bytes) -> bytes:
    """A Zstandard stream's bytes, by the standard library (3.14) or the zstd program."""
    try:
        from compression import zstd  # noqa: PLC0415 - not in every runner's Python
    except ImportError:
        command = ['zstd', '-dcq', '--long=31']
        return subprocess.run(command, input=data, capture_output=True, check=True).stdout
    return zstd.decompress(data)


STREAMS = {
    b'\x1f\x8b': gzip.decompress,
    b'BZh': bz2.decompress,
    b'\xfd7zXZ\0': lzma.decompress,
    b'\x28\xb5\x2f\xfd': zstandard,
}


def container(name: str, data: bytes) -> Callable[[bytes], list[tuple[str, bytes]]] | None:
    """How to read what a file holds, or None when it is not a container."""
    for start, decompress in STREAMS.items():
        if data.startswith(start):
            return lambda packed: [('', decompress(packed))]
    if data.startswith(b"7z\xbc\xaf'\x1c"):
        return seven_members
    if data[257:262] == b'ustar' or name.lower().endswith('.tar'):
        return tar_members
    if installer_content.carries(data) and not data.startswith(b'PK'):
        return lambda program: installer_content.content(program, zstandard)
    return zip_members if zipfile.is_zipfile(io.BytesIO(data)) else None


def sealed(data: bytes) -> str | None:
    """Why a file's content cannot be seen here."""
    for start, kind in SEALED.items():
        if data.startswith(start):
            return kind
    return 'a disk image' if data[-512:-508] == b'koly' else None


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
                held = json.loads(file.read_text(encoding='utf-8'))
                if held['crysta'] not in self.source.members:
                    raise RefusedError(f'{file} is of a commit the lists are not of')
                self.approved |= set(held['sha256'])
        self.found: list[str] = []

    def file(self, name: str, data: bytes) -> None:
        """Judge one file and everything in it."""
        if hashlib.sha256(data).hexdigest() in self.approved or self.source.is_public(data):
            return
        if kind := sealed(data):
            self.found.append(f'{name} is {kind} no receipt names')
            return
        if self.source.is_file(data):
            self.found.append(f'{name} is a source file')
            return
        if source_lists.is_text(data) and self.source.quoted_in(data):
            self.found.append(f'{name} quotes a source line')
            return
        try:
            read = container(name, data)
            held = read(data) if read else []
        except UNREADABLE:
            self.found.append(f'{name} cannot be read')
            return
        for member, content in held:
            self.file(f'{name}:{member}' if member else name, content)

    def sdk(self, name: str, data: bytes, commit: str, platform: str) -> None:
        """An SDK archive: a listed commit's, that platform's, with members the list names."""
        try:
            held = tar_members(gzip.decompress(data))
            manifests = [json.loads(content) for member, content in held if member == MANIFEST]
            made = [(m['source_sha'], m['platform']) for m in manifests]
        except (*UNREADABLE, KeyError, TypeError):
            made = []
        if made != [(commit, platform)] or commit not in self.source.members:
            self.found.append(f'{name} is not the SDK its name says, or not of a listed commit')
            return
        kinds = {pattern: kind for kind, pattern in source_lists.sdk_members()}
        headers = self.source.members[commit]
        seen = set()
        for member, content in held:
            kind = kinds.get(sdk_pattern(member, kinds))
            if kind is None or member in seen:
                self.found.append(f'{name}:{member} is not a member the SDK may have')
            elif kind == 'header':
                unix = content.replace(b'\r\n', b'\n')
                made = {source_lists.blob_id(content), source_lists.blob_id(unix)}
                if headers.get(member) not in made:
                    self.found.append(f'{name}:{member} is not the public header it is named')
            else:
                self.file(f'{name}:{member}', content)
            seen.add(member)

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
        if found := SDK.search(path.as_posix()):
            self.sdk(path.name, data, *found.groups())
        else:
            self.file(path.as_posix(), data)


def sdk_pattern(member: str, kinds: dict[str, str]) -> str | None:
    """The entry of sdk-members.txt that names a member."""
    for pattern in kinds:
        if fnmatch.fnmatchcase(member, pattern) and member.count('/') == pattern.count('/'):
            return pattern
    return None


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
