#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-3-Clause
"""Provision the immutable native math source closure declared by the app Pixi task."""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath
import shutil
import tarfile
import tempfile
import tomllib
import urllib.request

ROOT = Path(__file__).resolve().parents[2]

def digest(path: Path) -> str:
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()

def members(root: Path) -> dict[str, str]:
    result = {}
    for path in sorted(root.rglob('*')):
        if path.is_symlink() or not (path.is_dir() or path.is_file()):
            raise RuntimeError('Native math source contains a non-regular member')
        if path.is_file():
            result[path.relative_to(root).as_posix()] = digest(path)
    return result

def wanted(path: PurePosixPath) -> bool:
    name = path.as_posix()
    if name in ('LICENSE', 'VERSION', 'cmake/jkqtplotter_macros.cmake'):
        return True
    if any(part in ('tests', 'test', 'test-suite', 'examples', 'tools', 'doc') for part in path.parts):
        return False
    if name.startswith('lib/jkqtcommon/'):
        return True
    if not name.startswith('lib/jkqtmathtext/'):
        return False
    if '/resources/' not in name:
        return True
    return name == 'lib/jkqtmathtext/resources/xits.qrc' or (
        name.startswith('lib/jkqtmathtext/resources/xits/') and
        (path.suffix == '.otf' or path.name in ('OFL.txt', 'README.md')))

def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--offline', action='store_true')
    parser.add_argument('--archive', type=Path)
    args = parser.parse_args()
    manifest = ROOT / 'pixi.toml'
    pin = tomllib.loads(manifest.read_text())['feature']['app']['tasks']['assistant-math']['env']
    commit, expected = pin['EDI_MATH_COMMIT'], pin['EDI_MATH_ARCHIVE_SHA256']
    if len(commit) != 40 or len(expected) != 64 or any(c not in '0123456789abcdef' for c in commit+expected):
        raise RuntimeError('The native math source pin is invalid')
    base = ROOT / 'build' / 'deps' / 'jkqtmathtext' / commit
    base.mkdir(parents=True, exist_ok=True)
    source = base / 'source'
    destination = ROOT / 'build' / 'deps' / 'assistant-math.json'
    identity = {'schema': 'edi.assistant.math-source/1', 'commit': commit,
                'archive_sha256': expected, 'provisioner_sha256': digest(Path(__file__)), 'source': str(source)}
    if destination.is_file() and not destination.is_symlink():
        previous = json.loads(destination.read_text())
        if all(previous.get(key) == value for key, value in identity.items()):
            if source.is_symlink() or not source.is_dir() or not previous.get('files') or members(source) != previous['files']:
                raise RuntimeError('Retained native math source changed; it was not overwritten')
            # Other app task edits can change pixi.toml without changing this pin.
            current = dict(previous, manifest_sha256=digest(manifest))
            if current != previous:
                candidate = destination.with_suffix('.json.new')
                candidate.write_text(json.dumps(current, indent=2)+'\n')
                candidate.replace(destination)
            print(f'Native math source already verified: {commit}')
            return
    archive = base / 'package.tar.gz'
    if not archive.exists():
        candidate = base / 'package.tar.gz.download'
        try:
            if args.archive:
                if args.archive.is_symlink() or not args.archive.is_file():
                    raise RuntimeError('The native math archive must be a regular file')
                shutil.copyfile(args.archive, candidate)
            elif args.offline:
                raise RuntimeError('Native math source is absent; run the canonical Pixi task online once')
            else:
                url = f'https://codeload.github.com/jkriege2/JKQtPlotter/tar.gz/{commit}'
                with urllib.request.urlopen(url, timeout=30) as source, candidate.open('wb') as output:
                    shutil.copyfileobj(source, output)
            if digest(candidate) != expected:
                raise RuntimeError('Native math archive failed its canonical SHA256')
            candidate.replace(archive)
        finally:
            candidate.unlink(missing_ok=True)
    if digest(archive) != expected:
        raise RuntimeError('The retained native math archive failed its canonical SHA256')
    expected_files = {}
    with tempfile.TemporaryDirectory(prefix='source-', dir=base) as temporary:
        staged = Path(temporary)
        with tarfile.open(archive, 'r:gz') as package:
            prefix = f'JKQtPlotter-{commit}'
            for member in package:
                parts = PurePosixPath(member.name).parts
                if not parts or parts[0] != prefix or any(p in ('..', '.') for p in parts):
                    raise RuntimeError('Native math archive has an unexpected path')
                relative = PurePosixPath(*parts[1:])
                if not wanted(relative) or member.isdir():
                    continue
                if not member.isfile():
                    raise RuntimeError('Native math source has a non-regular member')
                target = staged / relative
                if target.exists():
                    raise RuntimeError('Native math archive has a duplicate member')
                target.parent.mkdir(parents=True, exist_ok=True)
                with package.extractfile(member) as original, target.open('xb') as output:
                    shutil.copyfileobj(original, output)
        expected_files = members(staged)
        for required in ('lib/jkqtcommon/CMakeLists.txt', 'lib/jkqtmathtext/CMakeLists.txt',
                         'lib/jkqtmathtext/resources/xits/OFL.txt', 'LICENSE'):
            if required not in expected_files:
                raise RuntimeError('Native math source closure is incomplete')
        if source.exists():
            if members(source) != expected_files:
                raise RuntimeError('Retained native math source changed; it was not overwritten')
        else:
            # Publish only this fully checked source closure; never execute upstream setup.
            staged.rename(source)
    result = dict(identity, manifest_sha256=digest(manifest), files=expected_files)
    candidate = destination.with_suffix('.json.new')
    candidate.write_text(json.dumps(result, indent=2)+'\n')
    candidate.replace(destination)
    print(f'Native math source verified: {commit}; only Common/MathText and XITS are staged')

if __name__ == '__main__':
    main()
