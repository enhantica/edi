#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-3-Clause
"""Pixi's developer-only official native helper provisioner; CMake consumes its output."""
from __future__ import annotations
import argparse
import fcntl
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import platform
import shutil
import tarfile
import tempfile
import tomllib
import urllib.request

ROOT = Path(__file__).resolve().parents[2]

def digest(path: Path) -> str:
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()

def files(root: Path) -> dict[str, str]:
    result = {}
    for path in sorted(root.rglob('*')):
        if path.is_symlink() or not (path.is_dir() or path.is_file()):
            raise RuntimeError('The provisioned helper contains a non-regular member')
        if path.is_file():
            result[path.relative_to(root).as_posix()] = digest(path)
    return result

def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--offline', action='store_true')
    parser.add_argument('--dedicated-archive', type=Path)
    parser.add_argument('--dedicated-sha256')
    args = parser.parse_args()
    pin = tomllib.loads((ROOT / 'pixi.toml').read_text())['feature']['app']['tasks']['assistant-runtime']['env']
    system, machine = platform.system(), platform.machine().lower()
    if system == 'Linux' and machine in ('x86_64', 'amd64'):
        target, expected = 'x86_64-unknown-linux-musl', pin['EDI_CODEX_LINUX_SHA256']
    elif system == 'Darwin' and machine in ('arm64', 'aarch64'):
        target, expected = 'aarch64-apple-darwin', pin['EDI_CODEX_MACOS_SHA256']
    else:
        raise RuntimeError(f'No qualified native helper for {system}/{machine}')
    version = pin['EDI_CODEX_VERSION']
    dedicated = args.dedicated_archive is not None
    if dedicated:
        expected = args.dedicated_sha256 or ''
    elif args.dedicated_sha256:
        raise RuntimeError('A dedicated digest requires its qualified archive')
    if len(expected) != 64 or any(c not in '0123456789abcdef' for c in expected):
        raise RuntimeError('The canonical helper digest is invalid')
    base = ROOT / 'build' / 'deps' / 'codex' / version
    if dedicated:
        base = base / ('edi-' + digest(ROOT / 'tools/assistant-runtime/edi-app-server.patch'))
    cache = base / target
    cache.mkdir(parents=True, exist_ok=True)
    with (cache / 'acquire.lock').open('a+b') as lock:
        fcntl.flock(lock.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        archive = cache / 'package.tar.gz'
        if not archive.exists():
            staged_archive = cache / 'package.tar.gz.download'
            try:
                if dedicated:
                    source = args.dedicated_archive.resolve(strict=True)
                    if args.dedicated_archive.is_symlink() or not source.is_file():
                        raise RuntimeError('The qualified dedicated archive is not regular')
                    shutil.copyfile(source, staged_archive)
                elif args.offline:
                    raise RuntimeError('The canonical archive is absent; run the Pixi provision task online once')
                else:
                    url = f'https://github.com/openai/codex/releases/download/rust-v{version}/codex-app-server-package-{target}.tar.gz'
                    with urllib.request.urlopen(url, timeout=30) as source, staged_archive.open('wb') as output:
                        shutil.copyfileobj(source, output)
                if digest(staged_archive) != expected:
                    raise RuntimeError('The downloaded helper archive failed its canonical SHA256')
                staged_archive.replace(archive)
            finally:
                staged_archive.unlink(missing_ok=True)
        if archive.is_symlink() or not archive.is_file() or digest(archive) != expected:
            raise RuntimeError('The cached helper archive failed its canonical SHA256')
        with tempfile.TemporaryDirectory(prefix='provision-', dir=cache) as temporary:
            stage = Path(temporary)
            with tarfile.open(archive, 'r:gz') as package:
                for member in package.getmembers():
                    name = PurePosixPath(member.name)
                    if name.is_absolute() or '..' in name.parts or not (member.isfile() or member.isdir()):
                        raise RuntimeError('The helper archive has a non-regular or escaping member')
                package.extractall(stage, filter='data')
            metadata = json.loads((stage / 'codex-package.json').read_text())
            required_metadata = dict(layoutVersion=1, version=version, target=target, variant='codex-app-server',
                entrypoint='bin/codex-app-server', resourcesDir='codex-resources', pathDir='codex-path')
            if any(metadata.get(key) != value for key, value in required_metadata.items()):
                raise RuntimeError('The official helper package has an incompatible native layout')
            required = ['bin/codex-app-server', 'bin/codex-code-mode-host', 'codex-path/rg', 'codex-resources/zsh/bin/zsh']
            if system == 'Linux':
                required.append('codex-resources/bwrap')
            if any(not (stage / item).is_file() or not os.access(stage / item, os.X_OK) for item in required):
                raise RuntimeError('The official helper package is missing an executable resource')
            expected_files = files(stage)
            published = cache / ('input-' + expected)
            if published.exists() or published.is_symlink():
                if published.is_symlink() or not published.is_dir() or files(published) != expected_files:
                    raise RuntimeError('The immutable provisioned helper was modified; it was not overwritten')
            else:
                stage.rename(published)
            manifest = dict(schema='edi.assistant.provisioned/1', root=str(published), version=version,
                target=target, archive_sha256=expected, dedicated=dedicated, files=expected_files)
            destination = ROOT / 'build/deps/codex/provisioned' / target
            destination.mkdir(parents=True, exist_ok=True)
            candidate = destination / 'input.json.stage'
            candidate.write_text(json.dumps(manifest, indent=2, sort_keys=True) + '\n')
            candidate.replace(destination / 'input.json')
            print(f'Provisioned {version} {target}: {destination / "input.json"}', flush=True)

if __name__ == '__main__':
    main()
