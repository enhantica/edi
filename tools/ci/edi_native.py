# SPDX-License-Identifier: BSD-3-Clause
"""edi's native code, built once per platform per CI run (I34).

  edi_native.py pack --out DIR    (the `native · <platform>` job) prove build/ci loads, then write
                                  edi-native.tar (build/ci; a tar keeps the executable bits
                                  upload-artifact drops) and edi-native.json, which binds it
  edi_native.py restore           (every consumer, via core-build with EDI_NATIVE_ARTIFACT=1) check
                                  every bound field against values read here — never from the
                                  manifest, and that the checkout's sources are that commit's;
                                  unpack into build/ci, give the unpacked files this restore's
                                  time, prove the import, compile nothing

The artifact binds this run, commit/tree, workspace, platform, locked Python ABI, and exact
qualified SDK manifest/library. Every consumer validates those facts locally before restoring.
Retry attempts may reuse a successful producer from the same run and source. Source drift,
foreign SDKs, changed file modes/bytes and escaping archive paths all refuse; restore compiles
nothing and proves the imported module's source identity before returning.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import posixpath
import shutil
import subprocess
import sys
import sysconfig
import tarfile
import time
from pathlib import Path
from typing import NoReturn

sys.path.insert(0, str(Path(__file__).resolve().parent))
import crysta_sdk  # THE pin reader, beside this file

ROOT = Path(__file__).resolve().parents[2]
TREE = ROOT / 'build' / 'ci'
MARK = TREE / '.edi-native.json'
TAR, MANIFEST = 'edi-native.tar', 'edi-native.json'
# What the native build reads: the root CMakeLists.txt, its subdirectories core, cli and lib, and
# the probe and test sources core/CMakeLists.txt names. A CMake source added elsewhere joins it.
SOURCES = (
    'CMakeLists.txt',
    'pixi.toml',
    'pixi.lock',
    'pyproject.toml',
    'data',
    'tools/ci/crysta_sdk.py',
    'tools/ci/core-build.sh',
    'tools/ci/build-crysta.sh',
    'tools/ci/edi_native.py',
    'cmake',
    'core',
    'cli',
    'lib',
    'tests/unit/cpp',
    'tests/integration/cpp',
    'tests/fixtures',
    'tools/probes',
)


class RefusedError(Exception):
    """The native artifact cannot be proven to be this run's build: nothing runs on it."""


def refuse(message: str) -> NoReturn:
    """Stop with ``message`` as the refusal."""
    raise RefusedError(message)


def git(*args: str) -> str:
    """Return a git answer about this checkout; a failure refuses."""
    r = subprocess.run(['git', *args], cwd=ROOT, capture_output=True, text=True, check=False)
    return r.stdout.strip() if r.returncode == 0 else refuse(f'git {" ".join(args)} failed')


def sdk_platform() -> str:
    """Return the task's pixi platform (PIXI_PLATFORM), else the runner's, else the host's."""
    host = f'{os.environ.get("RUNNER_OS") or platform.system()}-'
    host = os.environ.get('PIXI_PLATFORM') or host + (
        os.environ.get('RUNNER_ARCH') or platform.machine()
    )
    table = {'linux-64': 'linux-64', 'linux-64-app': 'linux-64', 'osx-arm64': 'osx-arm64'}
    table |= {'osx-arm64-app': 'osx-arm64'}
    table |= {'Linux-X64': 'linux-64', 'Linux-x86_64': 'linux-64'}
    table |= {'macOS-ARM64': 'osx-arm64', 'Darwin-arm64': 'osx-arm64'}
    return table.get(host) or refuse(f'no edi native platform for {host}')


def observed() -> dict:
    """Read the current run, source, ABI and qualified SDK identities independently."""
    name = sdk_platform()
    run_id, workspace = os.environ.get('GITHUB_RUN_ID'), os.environ.get('GITHUB_WORKSPACE')
    if not run_id or not workspace or Path(workspace).resolve() != ROOT.resolve():
        refuse('native artifacts require this run and its exact checked-out workspace')
    abi = sysconfig.get_config_var('SOABI')
    if not isinstance(abi, str) or not abi:
        refuse('the native Python interpreter has no declared SOABI')
    pin = crysta_sdk.pinned(git('show', 'HEAD:pixi.toml'))
    prefix = ROOT / 'build/crysta-prefix'
    manifest_path = prefix / crysta_sdk.MANIFEST
    manifest = crysta_sdk.check(prefix, name)
    if manifest['source_sha'] != pin:
        refuse('the native artifact requires the committed SDK pin, never a diagnostic override')
    return {
        'source_sha': git('rev-parse', 'HEAD'),
        'source_tree': git('rev-parse', 'HEAD^{tree}'),
        'run_id': run_id,
        'platform': name,
        'workspace': workspace,
        'python_abi': abi,
        'pixi_lock_sha256': sha256(ROOT / 'pixi.lock'),
        'crysta_source_sha': pin,
        'crysta_sdk_sha256': sha256(manifest_path),
        'crysta_library_sha256': sha256(prefix / crysta_sdk.TESTED[0]),
    }


def sha256(path: Path) -> str:
    """Return the hex sha256 of the file at ``path``."""
    digest = hashlib.sha256()
    with path.open('rb') as fh:
        for block in iter(lambda: fh.read(1 << 20), b''):
            digest.update(block)
    return digest.hexdigest()


def prove_import() -> None:
    """Refuse unless build/ci's own extension imports at HEAD (edi.__build_commit__).

    Lib/edi selects its extension from the environment (EDI_EXTENSION_DIR, the consumer
    selectors), so the import names build/ci's directory itself, and the module that loaded must
    be a file of build/ci: no selector left in the environment can make another build answer for
    this one.
    """
    head = git('rev-parse', 'HEAD')
    code = 'import edi, edi._edi; print(edi.__build_commit__); print(edi._edi.__file__)'
    # This checkout's package (lib/edi), ahead of another checkout's install, on build/ci's module.
    path = os.pathsep.join(filter(None, [str(ROOT / 'lib'), os.environ.get('PYTHONPATH')]))
    unselected = ('EDI_USE_CONSUMER_BUILD', 'CRYSTA_CONSUMER_SRC')
    env = {name: value for name, value in os.environ.items() if name not in unselected}
    env |= {'PYTHONPATH': path, 'EDI_EXTENSION_DIR': str(TREE / 'python' / 'edi')}
    r = subprocess.run(
        [sys.executable, '-c', code],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
        env=env,
    )
    answer = r.stdout.split('\n')
    loaded = Path(answer[1]).resolve() if len(answer) > 1 and answer[1] else None
    if r.returncode or answer[0] != head:
        refuse(f'edi._edi does not import at HEAD {head}: {(r.stdout + r.stderr).strip()[-300:]}')
    if loaded is None or TREE.resolve() not in loaded.parents:
        refuse(f'edi._edi loaded from {loaded}, not from build/ci')


def prove() -> None:
    """Prove the imported source identity, CLI response and both declared test runners."""
    prove_import()
    cli = subprocess.run(
        [str(TREE / 'cli' / 'easydiffraction'), '--version'],
        capture_output=True,
        text=True,
        check=False,
    )
    if cli.returncode or not cli.stdout.startswith('edi '):
        refuse(f'the CLI gives no version line: {(cli.stdout + cli.stderr).strip()[:200]}')
    runnable()


def runnable() -> None:
    """Refuse unless the CLI and both declared test runners are executable files."""
    for rel in ('cli/easydiffraction', 'core/edi_tests', 'core/edi_integration_tests'):
        if not ((TREE / rel).is_file() and os.access(TREE / rel, os.X_OK)):
            refuse(f'build/ci/{rel} is not built or not executable')


def digest_tree() -> dict:
    """Every file of build/ci but the marker -> its sha256 and mode, a link -> its target.

    F04: a dropped execute bit is a different state. The mode is masked to 0o755, what tar's 'data'
    filter keeps.
    """
    found = {}
    for path in sorted(TREE.rglob('*')):
        if path != MARK and (path.is_symlink() or path.is_file()):
            found[path.relative_to(ROOT).as_posix()] = (
                f'link:{path.readlink()}'
                if path.is_symlink()
                else f'{sha256(path)} {path.stat().st_mode & 0o755:o}'
            )
    return found


def contained(member: tarfile.TarInfo) -> bool:
    """F15: a member, and any link's target, stays inside build/ci after normalisation."""
    inside = lambda p: p == 'build/ci' or p.startswith('build/ci/')  # noqa: E731
    name = posixpath.normpath(member.name)
    if member.name.startswith('/') or not inside(name):
        return False
    if member.issym() or member.islnk():
        base = posixpath.dirname(name) if member.issym() else ''
        target = posixpath.normpath(posixpath.join(base, member.linkname))
        return not member.linkname.startswith('/') and inside(target)
    return member.isfile() or member.isdir()


def source_drift() -> list[str]:
    """The build's source paths whose CONTENT is not HEAD's: changed, deleted or untracked.

    git compares content here, so a file a checkout rewrote with the same bytes and a new time is
    not drift. Ignored files (caches) are not listed.
    """
    lines = git('status', '--porcelain', '--untracked-files=all', '--', *SOURCES).splitlines()
    return [line.split(maxsplit=1)[-1] for line in lines if line.strip()]


def stamp() -> None:
    """Give every file of the restored build/ci this restore's time.

    The tar keeps the times of the native job's build. A consumer job checks out afterwards, and
    on a persistent runner workspace a tracked file carries the time of whichever checkout last
    changed it: after another run's job had the workspace at a different commit, a source this
    commit changed is newer than the build made from it. A reader that compares the two times
    then calls a current build stale (the pre-built probes' freshness check did, on main's push
    run 37007329677). restore() has just proven the tree is this commit's build, byte for byte,
    so it is current as of now, and its times say so. That holds only while the checkout's
    sources are that commit's, which restore() refuses to go on without (source_drift): a source
    edited after the build must keep reading as newer than it. Links are left alone: a time set
    through one lands on its target.
    """
    now = time.time()
    for path in TREE.rglob('*'):
        if not path.is_symlink():
            os.utime(path, (now, now))


def pack(out: Path) -> None:
    """Prove build/ci, then write edi-native.tar and the edi-native.json that binds it."""
    if drift := source_drift():
        refuse(f'the native producer source differs from HEAD: {drift[:3]}')
    prove()
    mine = observed()
    linked = (TREE / '.crysta-linked-sha').read_text(encoding='utf-8').strip()
    if linked != mine['crysta_source_sha']:
        refuse(f'build/ci linked crysta {linked}, not the committed SDK pin')
    out.mkdir(parents=True, exist_ok=True)
    with tarfile.open(out / TAR, 'w', format=tarfile.PAX_FORMAT) as tar:
        tar.add(TREE, arcname='build/ci')  # repo-relative members, restored at the checkout root
    record = mine | {
        'run_attempt': os.environ.get('GITHUB_RUN_ATTEMPT'),
        'job': os.environ.get('GITHUB_JOB'),
        'sha256': sha256(out / TAR),
        'crysta_linked_sha': linked,
        'files': digest_tree(),
    }
    (out / MANIFEST).write_text(json.dumps(record, indent=1, sort_keys=True) + '\n', 'utf-8')
    print(f'edi-native: packed build/ci for {record["platform"]} at {record["source_sha"]}')


def restore(where: Path) -> None:
    """Check every bound field against this job's own values, unpack, and prove the import."""
    for name in (TAR, MANIFEST):
        if not (where / name).is_file():
            refuse(f'the native artifact is missing: no {where / name}')
    record = json.loads((where / MANIFEST).read_text(encoding='utf-8'))
    mine = observed() | {'sha256': sha256(where / TAR)}
    for field, value in mine.items():
        if record.get(field) != value:
            refuse(
                f"the native artifact's {field} is {record.get(field)!r}, this job's is {value!r}"
            )
    linked = record.get('crysta_linked_sha')
    if linked != mine['crysta_source_sha']:
        refuse(f'the native artifact linked crysta {linked!r}, not the committed SDK pin')
    if not isinstance(record.get('files'), dict) or not record['files']:
        refuse('the native artifact records no file digests')
    # The artifact is HEAD's build. A checkout whose sources differ from HEAD in content is another
    # tree, and stamping its build as current would hide exactly the staleness the times exist for.
    if drift := source_drift():
        refuse(
            f'the checkout differs from {mine["source_sha"]} in what the native build reads '
            f"({', '.join(drift[:3])}): the artifact is not this tree's build"
        )
    # F15: every call re-proves the bytes on disk, a cache hit included; a mismatch re-extracts
    if not (
        MARK.is_file()
        and json.loads(MARK.read_text(encoding='utf-8')) == record
        and digest_tree() == record['files']
    ):
        with tarfile.open(where / TAR) as tar:
            outside = [m.name for m in tar.getmembers() if not contained(m)]
            if outside:
                refuse(f'the native artifact carries members outside build/ci: {outside[:3]}')
            shutil.rmtree(TREE, ignore_errors=True)
            tar.extractall(ROOT, filter='data')
        if digest_tree() != record['files']:
            refuse('the restored build/ci is not the bytes the native artifact recorded')
        MARK.write_text(json.dumps(record, indent=1, sort_keys=True) + '\n', encoding='utf-8')
    stamp()  # a cache hit included: a checkout may have run since the tree was unpacked
    runnable()
    prove_import()
    print(f'edi-native: restored and validated build/ci, {mine["platform"]} {mine["source_sha"]}')


def main(argv: list[str]) -> int:
    """Dispatch a subcommand; a refusal exits 1."""
    parser = argparse.ArgumentParser(prog='edi_native.py', description=__doc__)
    sub = parser.add_subparsers(dest='cmd', required=True)
    sub.add_parser('pack').add_argument('--out', required=True, type=Path)
    sub.add_parser('restore')
    a = parser.parse_args(argv)
    where = Path(os.environ.get('EDI_NATIVE_ARCHIVES') or ROOT / 'build/edi-native-artifact')
    try:
        pack(a.out) if a.cmd == 'pack' else restore(where)
    except (RefusedError, crysta_sdk.RefusedError, OSError, KeyError, ValueError) as refusal:
        print(f'edi_native.py {a.cmd}: REFUSED — {refusal}', file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    raise SystemExit(main(sys.argv[1:]))
