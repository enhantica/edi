# SPDX-License-Identifier: BSD-3-Clause
"""edi's one crysta: the C++ SDK built from the pinned crysta commit (edi ADR-0083).

  crysta_sdk.py fetch --platform P    reuse or unpack the pinned commit's SDK, check it
  crysta_sdk.py check --sdk DIR --platform P    the fingerprint check alone (CRYSTA_SDK_DIR)
  crysta_sdk.py pins pixi.toml    the pinned commit

The pin is `CRYSTA_COMMIT` under `[activation.env]` in pixi.toml. edi's own CI builds that commit's
SDK once per platform (.github/workflows/crysta-sdk.yml) and hands it to every job as an archive in
`CRYSTA_SDK_ARCHIVES` (default build/crysta-sdk-archives); a desk build packs it from a crysta
checkout (crysta: `pixi run -e cpp-ci sdk-pack <sha> <platform> <dir>`) or points CRYSTA_SDK_DIR at
one. Nothing is downloaded from crysta. Every refusal exits 1 naming its cause.
"""

from __future__ import annotations

import argparse
import fcntl
import hashlib
import json
import os
import re
import shutil
import sys
import tarfile
import tomllib
from pathlib import Path
from typing import NoReturn

ROOT = Path(__file__).resolve().parents[2]
PLATFORMS = ('linux-64', 'osx-arm64')
MANIFEST = 'share/crysta-sdk/manifest.json'


class RefusedError(Exception):
    """A precondition failed: edi builds against no crysta."""


def refuse(message: str) -> NoReturn:
    """Stop with ``message`` as the refusal."""
    raise RefusedError(message)


# THE pin reader (edi ADR-0083): every reader of the crysta commit goes through it.
def pinned(text: str | None = None) -> str:
    """The crysta commit pixi.toml pins, from its `[activation.env]` table."""
    text = text if text is not None else (ROOT / 'pixi.toml').read_text(encoding='utf-8')
    sha = tomllib.loads(text).get('activation', {}).get('env', {}).get('CRYSTA_COMMIT', '')
    if not re.fullmatch(r'[0-9a-f]{40}', sha):
        refuse(f'pixi.toml pins no crysta commit (CRYSTA_COMMIT {sha!r} under [activation.env])')
    return sha


def archive_name(sha: str, platform: str) -> str:
    return f'crysta-sdk-{sha}-{platform}.tar.gz'


def sha256(path: Path) -> str:
    """Return the hex sha256 of the file at ``path``."""
    digest = hashlib.sha256()
    with path.open('rb') as fh:
        for block in iter(lambda: fh.read(1 << 20), b''):
            digest.update(block)
    return digest.hexdigest()


def lock_packages(env: str, platform: str) -> dict[str, tuple[str, str]]:
    """Return ``{name: (version, build)}`` pixi.lock resolves for ``env`` on ``platform``."""
    lines = (ROOT / 'pixi.lock').read_text(encoding='utf-8').splitlines()
    head = lines[: next(i for i, x in enumerate(lines) if x.startswith('environments:'))]
    plats: dict[str, str] = {}  # lock platform name -> conda subdir (without `subdir:`, its name)
    name = None
    for ln in head:
        if m := re.match(r'^- name: (\S+)$', ln):
            name = plats[m.group(1)] = m.group(1)
        elif (m := re.match(r'^  subdir: (\S+)$', ln)) and name:
            plats[name] = m.group(1)
    keys = {n for n, s in plats.items() if s == platform} | {platform}  # a key named as its subdir
    found, in_env, in_key = {}, False, False
    for ln in lines:
        if re.match(r'^  \S', ln):
            in_env = ln.strip() == f'{env}:'
        elif in_env and re.match(r'^      \S+:$', ln):
            in_key = ln.strip()[:-1] in keys
        elif (
            in_env
            and in_key
            and (m := re.match(r'^      - conda: \S+/([^/]+?)\.(?:conda|tar\.bz2)$', ln))
        ):
            pkg, version, build = m.group(1).rsplit('-', 2)
            found[pkg] = (version, build)
        elif ln.startswith('packages:'):
            break
    return found or refuse(f'pixi.lock resolves nothing for environment {env!r} on {platform}')


# I25: the ABI packages edi itself requires an SDK to declare — never the SDK's own list.
REQUIRED = {
    'linux-64': {
        'gcc_impl_linux-64',
        'gxx_impl_linux-64',
        'libgcc',
        'libgcc-devel_linux-64',
        'libstdcxx',
        'libstdcxx-devel_linux-64',
        'libgomp',
        'sysroot_linux-64',
        'eigen',
        'sleef',
    },
    'osx-arm64': {
        'clang_impl_osx-arm64',
        'clangxx_impl_osx-arm64',
        'libcxx',
        'libcxx-devel',
        'llvm-openmp',
        'eigen',
        'sleef',
    },
}
TESTED = ('lib/libcrysta_core.a', 'bin/crysta')  # the qualified bytes the manifest's hashes bind
RUNTIME = 'lib/crysta-runtime'  # The env libraries the SDK's CLI carries


def untested_allowed() -> bool:
    """Whether this local build may use an SDK packed without its tests; never in CI."""
    allowed = os.environ.get('EDI_ALLOW_UNTESTED_SDK', '')
    if allowed not in {'', '1'}:
        refuse(f'EDI_ALLOW_UNTESTED_SDK is {allowed!r}: it is 1 or unset')
    if allowed and (os.environ.get('CI') or os.environ.get('GITHUB_ACTIONS')):
        refuse('EDI_ALLOW_UNTESTED_SDK=1 is for a local trial: CI never builds on an untested SDK')
    return allowed == '1'


def qualified(sdk_dir: Path, tested: dict) -> None:
    """Refuse a tier that missed a case, and an untested one without the local switch."""
    allow_untested = untested_allowed()
    for tier in ('cpp_tier', 'corpus'):
        t = tested.get(tier) or {}
        # An SDK packed for a local trial without its tests says so, whatever counts sit beside the
        # marker; only that trial may use it.
        if 'untested' in t:
            if t['untested'] is not True:
                refuse(f'{sdk_dir}: the {tier} untested marker is malformed ({t})')
            if not allow_untested:
                refuse(
                    f'{sdk_dir}: the {tier} qualification never ran (an untested SDK); '
                    'EDI_ALLOW_UNTESTED_SDK=1 lets a local build use it'
                )
            continue
        if not (
            isinstance(t.get('total'), int) and t['total'] > 0 and t.get('passed') == t['total']
        ):
            refuse(f'{sdk_dir}: the {tier} qualification is not complete ({t})')


def shape(sdk_dir: Path, manifest: dict, platform: str) -> None:
    """F15: schema, clean identity, edi's required fingerprint set, the qualified binaries."""
    sha, tree = manifest.get('source_sha', ''), manifest.get('source_tree', '')
    hexes = all(re.fullmatch(r'[0-9a-f]{40}', v) for v in (sha, tree))
    if manifest.get('schema') != 1 or not hexes:
        refuse(f'{sdk_dir}: manifest schema/source identity is malformed')
    if manifest.get('identity') != f'git:{sha}':
        refuse(f'{sdk_dir}: identity {manifest.get("identity")!r} is not the clean git:{sha}')
    names = sorted(p.get('name') for p in manifest.get('fingerprint', {}).get('packages', []))
    if names != sorted(REQUIRED[platform]):
        refuse(f'{sdk_dir}: fingerprint {names} is not the required {sorted(REQUIRED[platform])}')
    tested = manifest.get('tested') or {}
    qualified(sdk_dir, tested)
    # Absent bytes and an absent record never qualify each other
    for rel in TESTED:
        want = (tested.get('sha256') or {}).get(rel)
        if not (isinstance(want, str) and re.fullmatch(r'[0-9a-f]{64}', want)):
            refuse(f'{sdk_dir}: the manifest records no sha256 for the tested {rel}')
        if not (sdk_dir / rel).is_file() or sha256(sdk_dir / rel) != want:
            refuse(f'{sdk_dir}: {rel} is missing or not the qualified binary the manifest records')
    # The runtime the CLI loads is the qualified one, nothing else beside it
    carried = {
        k: v for k, v in (tested.get('sha256') or {}).items() if k.startswith(RUNTIME + '/')
    }
    present = {p.relative_to(sdk_dir).as_posix() for p in (sdk_dir / RUNTIME).glob('*')}
    if present != set(carried):
        refuse(
            f'{sdk_dir}: {RUNTIME} holds {sorted(present)}, not the qualified {sorted(carried)}'
        )
    for rel, want in carried.items():
        if sha256(sdk_dir / rel) != want:
            refuse(f'{sdk_dir}: {rel} is not the qualified runtime the manifest records')


def compatible(sdk: dict, got: tuple[str, str] | None) -> bool:
    """I25: a fingerprint package must resolve identically in the consuming environment."""
    return got == (sdk['version'], sdk['build'])


def check(sdk_dir: Path, platform: str) -> dict:
    """Refuse an SDK built for another platform or toolchain (I25); return its manifest."""
    manifest = json.loads((sdk_dir / MANIFEST).read_text(encoding='utf-8'))
    if manifest.get('platform') != platform:
        refuse(f'{sdk_dir} is a {manifest.get("platform")} SDK, not {platform}')
    shape(sdk_dir, manifest, platform)
    env = os.environ.get('PIXI_ENVIRONMENT_NAME') or 'default'
    locked = lock_packages(env, platform)
    bad = [
        f'{p["name"]} {p["version"]} {p["build"]} (locked {locked.get(p["name"])})'
        for p in manifest['fingerprint']['packages']
        if not compatible(p, locked.get(p['name']))
    ]
    target = manifest['fingerprint'].get('macos_deployment_target')
    if target != (os.environ.get('MACOSX_DEPLOYMENT_TARGET') or None):
        here = os.environ.get('MACOSX_DEPLOYMENT_TARGET')
        bad.append(f'deployment target {target} (this environment {here})')
    if bad:
        refuse(f'the SDK fingerprint does not resolve in environment {env!r}: {"; ".join(bad)}')
    return manifest


def fetch(platform: str) -> Path:
    """The pinned commit's unpacked SDK: reused when present, else unpacked from its archive."""
    sha = pinned()
    home = ROOT / 'build' / 'crysta-sdk' / f'{sha}-{platform}'
    home.parent.mkdir(parents=True, exist_ok=True)
    # One acquisition at a time into the cache every environment shares
    with (home.parent / '.lock').open('w') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        marker = home / '.sdk-sha256'
        if marker.is_file() and (home / MANIFEST).is_file():
            kept = json.loads((home / MANIFEST).read_text(encoding='utf-8'))
            if kept.get('source_sha') == sha and kept.get('platform') == platform:
                return home
        archives = Path(
            os.environ.get('CRYSTA_SDK_ARCHIVES') or ROOT / 'build' / 'crysta-sdk-archives'
        )
        tarball = archives / archive_name(sha, platform)
        if not tarball.is_file():
            refuse(
                f'{tarball} is missing: CI takes it from the crysta-sdk workflow; at a desk, '
                'pack it '
                f'in a crysta checkout at {sha} (pixi run -e cpp-ci sdk-pack {sha} {platform} '
                f'{archives}) or set CRYSTA_SDK_DIR'
            )
        shutil.rmtree(home, ignore_errors=True)
        home.mkdir(parents=True)
        with tarfile.open(tarball) as tar:
            tar.extractall(home, filter='data')
        manifest = json.loads((home / MANIFEST).read_text(encoding='utf-8'))
        if not isinstance(manifest, dict):
            refuse(f'{tarball}: SDK manifest is not an object; requested {sha} on {platform}')
        if manifest.get('source_sha') != sha or manifest.get('platform') != platform:
            refuse(
                f'{tarball}: SDK source {manifest.get("source_sha")!r} on '
                f'{manifest.get("platform")!r} differs from requested source {sha} on {platform}'
            )
        marker.write_text(sha256(tarball) + '\n', encoding='utf-8')
        return home


def main(argv: list[str]) -> int:
    """Dispatch a subcommand; a refusal exits 1."""
    parser = argparse.ArgumentParser(prog='crysta_sdk.py', description=__doc__)
    sub = parser.add_subparsers(dest='cmd', required=True)
    sub.add_parser('fetch').add_argument('--platform', required=True, choices=PLATFORMS)
    # The pinned commit
    sub.add_parser('pins').add_argument('pixi_toml', type=Path)
    p = sub.add_parser('check')
    p.add_argument('--sdk', required=True, type=Path)
    p.add_argument('--platform', required=True, choices=PLATFORMS)
    a = parser.parse_args(argv)
    try:
        run(a)
    except (RefusedError, OSError, KeyError, ValueError) as refusal:
        print(f'crysta_sdk.py {a.cmd}: REFUSED — {refusal}', file=sys.stderr)
        return 1
    return 0


def run(a: argparse.Namespace) -> None:
    """Run one subcommand; `fetch` and `check` print the provenance line the CI evidence reads."""
    if a.cmd == 'pins':
        print(pinned(a.pixi_toml.read_text(encoding='utf-8')))
        return
    home = fetch(a.platform) if a.cmd == 'fetch' else a.sdk.resolve()
    manifest = check(home, a.platform)
    digest = (home / '.sdk-sha256').read_text().strip() if a.cmd == 'fetch' else 'diagnostic'
    print(  # line 1: the provenance line build-crysta.sh prints; line 2: the SDK's directory
        f'crysta: using SDK build-{manifest["source_sha"]} tree {manifest["source_tree"]} '
        f'sha256 {digest} platform {a.platform}'
    )
    print(home)


if __name__ == '__main__':
    raise SystemExit(main(sys.argv[1:]))
