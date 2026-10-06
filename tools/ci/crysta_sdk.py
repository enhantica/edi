# SPDX-License-Identifier: BSD-3-Clause
"""edi's one crysta source: the pinned, prebuilt C++ SDK crysta's CI tested (ADR-0017).

  crysta_sdk.py fetch --platform P    reuse or download the pinned build, verify, unpack, check
  crysta_sdk.py check --sdk DIR --platform P    the fingerprint check alone (CRYSTA_SDK_DIR)

The pin is `CRYSTA_SDK_TAG` and `CRYSTA_SDK_SHA256` under `[target.<platform>.activation.env]` in
pixi.toml. The pinned build comes from its release when crysta has one, and
otherwise from the tested package of crysta's pull-request run at that commit (I8): the same
bytes either way, bound by the pinned sha256. One case builds another commit than the pin: a CI
run paired with a crysta branch whose head the pin does not name builds that head, from the
tested package of crysta's pull-request run at it, bound to that run as I8 says and to no
committed sha256. The final CI evidence never counts such a run. Downloads use curl against the
REST API (no `gh` on the CI fleet) with GITHUB_TOKEN or GH_TOKEN (CI's crysta App token, or a
desk run's export). Every refusal exits 1 naming its cause.
"""

from __future__ import annotations

import argparse
import fcntl
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tarfile
import tempfile
import tomllib
import zipfile
from pathlib import Path
from typing import NoReturn

ROOT = Path(__file__).resolve().parents[2]
API = 'https://api.github.com/repos/enhantica/crysta'
PLATFORMS = ('linux-64', 'osx-arm64')
MANIFEST = 'share/crysta-sdk/manifest.json'
JSON = 'application/vnd.github+json'
# Crysta's pull-request workflow and the job that packs each platform's SDK
WORKFLOW = '.github/workflows/ci.yml'
PRODUCERS = {'linux-64': 'checks (Linux)', 'osx-arm64': 'checks (macOS)'}
REPAIR = 're-run that job in the run, then re-pin (pixi run crysta-sdk-pin)'
# A producing job that failed still yields its package when the steps that make and test it
# passed: it was packed, qualified and smoke-tested like any other. The failed steps are recorded
# with the pin (FAILED_STEPS, keyed by commit and platform).
PACKAGE_STEPS = (
    'Pack and qualify the crysta SDK',
    'SDK consumer smoke',
    'Upload the SDK artifact',
)
FAILED_STEPS: dict[tuple[str, str], list[str]] = {}


class RefusedError(Exception):
    """A precondition failed: edi builds against no crysta."""


def refuse(message: str) -> NoReturn:
    """Stop with ``message`` as the refusal."""
    raise RefusedError(message)


# THE pin line (edi ADR-0017): what crysta_sdk_pin.py writes, private to declared_shas, which
# every pin reader goes through (no second text reader)
_TAG_LINE = re.compile(r'CRYSTA_SDK_TAG *= *"build-([0-9a-f]{40})" *')
# class B, review-18 F01: the declaration keys are private; a consumer reads an effective
# result's tag through pin_tag, which refuses any table pin_fields did not select
_TAG_FIELD, _SHA_FIELD = 'CRYSTA_SDK_TAG', 'CRYSTA_SDK_SHA256'


def declared_shas(text: str) -> list[str]:
    """Return each platform's pinned sha ('' where none is declared) — THE pin contract.

    The file parses as TOML, every line mentioning CRYSTA_SDK_TAG outside a comment is a whole
    _TAG_LINE carrying a parsed value, and the declared pins name one build, so no reader admits a
    pin another reader cannot see.
    """
    targets = tomllib.loads(text).get('target', {})
    tags = [
        targets.get(p, {}).get('activation', {}).get('env', {}).get('CRYSTA_SDK_TAG')
        for p in PLATFORMS
    ]
    mentions = [ln for ln in text.splitlines() if 'CRYSTA_SDK_TAG' in ln.split('#', 1)[0]]
    canon = sorted(m.group(1) for m in map(_TAG_LINE.fullmatch, mentions) if m)
    parsed = sorted(t[6:] for t in tags if isinstance(t, str) and t.startswith('build-'))
    if len(canon) != len(mentions) or canon != parsed or len(parsed) != len(mentions):
        refuse(f'pixi.toml declares a crysta pin outside the one pin line form: {mentions}')
    if len(set(parsed)) > 1:
        refuse(f'pixi.toml pins {sorted(set(parsed))}, not one build')
    return [t[6:] if isinstance(t, str) else '' for t in tags]


def pin_fields(text: str, platform: str) -> dict:
    """``platform``'s declared tag and sha256 (None where absent), once THE pin contract passes."""
    declared_shas(text)  # F07/class B: a pin outside the one line form refuses for every reader
    targets = tomllib.loads(text).get('target', {})
    env = targets.get(platform, {}).get('activation', {}).get('env', {})
    return _Pin({k: env.get(k) for k in (_TAG_FIELD, _SHA_FIELD)})


class _Pin(dict):  # noqa: FURB189 - a dict to every consumer (merged, dumped as JSON)
    """An effective pin: only pin_fields makes one, after THE pin contract and its selection."""


def pin_tag(fields: dict) -> str | None:
    """Return an effective ``pin_fields`` result's tag; a raw table refuses."""
    if type(fields) is not _Pin:
        refuse('pin_tag reads only a pin_fields result, never a table its caller selected')
    return fields[_TAG_FIELD]


def pin(platform: str) -> tuple[str, str]:
    """Return the committed pin (tag, sha256) for ``platform``; a platform without one refuses."""
    got = pin_fields((ROOT / 'pixi.toml').read_text(encoding='utf-8'), platform)
    tag, digest = got[_TAG_FIELD], got[_SHA_FIELD]
    if not (isinstance(tag, str) and re.fullmatch(r'build-[0-9a-f]{40}', tag)):
        refuse(f'pixi.toml pins no crysta SDK for {platform} (CRYSTA_SDK_TAG {tag!r})')
    if not (isinstance(digest, str) and re.fullmatch(r'[0-9a-f]{64}', digest)):
        refuse(f'pixi.toml has no sha256 for {tag} on {platform}')
    return tag, digest


def token() -> str:
    """Return the token that reads crysta's releases: CI's App token, or one a desk run exports."""
    found = os.environ.get('GITHUB_TOKEN') or os.environ.get('GH_TOKEN')
    return found or refuse(
        'no GITHUB_TOKEN or GH_TOKEN reads crysta releases (a desk run exports its own token)'
    )


def curl(
    url: str, *, accept: str, out: Path | None = None, absent_ok: bool = False
) -> bytes | None:
    """GET ``url`` with the crysta token; a failure refuses, naming the URL (never the token).

    With ``absent_ok`` a 404, and only a 404, returns None: what was asked for does not exist.
    """
    argv = [
        'curl',
        '-fsSL',
        '--retry',
        '3',
        '-H',
        f'Authorization: Bearer {token()}',
        '-H',
        f'Accept: {accept}',
    ]
    argv += ['-o', str(out)] if out else []
    r = subprocess.run([*argv, url], capture_output=True, check=False)
    if r.returncode:
        why = r.stderr.decode(errors='replace').strip()[:200]
        # curl's own statement of the status decides, never its exit code: for one GitHub 404
        # the Linux runners' curl exits 22 and the macOS runners' 56 (edi run 36983765261).
        if absent_ok and re.search(r'The requested URL returned error: 404\b', why):
            return None
        refuse(f'GET {url} failed (curl {r.returncode}): {why}')
    return r.stdout


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
    for tier in ('cpp_tier', 'corpus'):
        t = tested.get(tier) or {}
        if not (
            isinstance(t.get('total'), int) and t['total'] > 0 and t.get('passed') == t['total']
        ):
            refuse(f'{sdk_dir}: the {tier} qualification is not complete ({t})')
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


def paired_head() -> str:
    """Return the head of the crysta branch this CI run is paired with, or '' when it is unpaired.

    The rule and its lookups are crysta-source.sh's: one implementation answers the currency check
    and the build. Outside a pull-request or dispatched run nothing is looked up. A job asks once
    and keeps the answer in RUNNER_TEMP, so no job links two builds because the branch moved under
    it. An answer that cannot be read refuses.
    """
    if os.environ.get('GITHUB_EVENT_NAME') not in {'pull_request', 'workflow_dispatch'}:
        return ''
    kept = os.environ.get('RUNNER_TEMP')
    memo = Path(kept) / 'crysta-paired-head' if kept else None
    if memo and memo.is_file():
        head, why = memo.read_text(encoding='utf-8').strip(), f'{memo} holds no answer'
    else:
        asked = ['bash', str(ROOT / 'tools' / 'ci' / 'crysta-source.sh'), '--paired-head']
        r = subprocess.run(asked, capture_output=True, text=True, check=False)
        head, why = ('unread' if r.returncode else r.stdout.strip()), r.stderr.strip()[-300:]
    if not re.fullmatch(r'([0-9a-f]{40})?', head):
        refuse(f'the paired crysta branch could not be read: {why}')
    if memo:
        memo.write_text(head + '\n', encoding='utf-8')
    return head


def native_dir() -> Path:
    """Return where a consumer job finds its run's native artifact (edi_native.py)."""
    return Path(
        os.environ.get('EDI_NATIVE_DIR') or Path(os.environ.get('RUNNER_TEMP', '')) / 'edi-native'
    )


def run_head() -> str:
    """Return the crysta commit a paired run builds, or '' when the run builds its pin.

    One run builds one crysta. The job that builds the native artifact asks for the paired head
    (`paired_head`), and the artifact records the crysta it linked. A job that restores the
    artifact (EDI_NATIVE_ARTIFACT=1) builds that recorded crysta when it is a commit of the
    paired branch, so the jobs of a run hold one build even when the crysta branch moves under
    the run. Any other record is left to edi_native's restore, which refuses it; this job then
    builds what it finds itself.
    """
    record = native_dir() / 'edi-native.json'
    if os.environ.get('EDI_NATIVE_ARTIFACT') == '1' and record.is_file():
        linked = json.loads(record.read_text(encoding='utf-8')).get('crysta_linked_sha')
        if isinstance(linked, str) and re.fullmatch(r'[0-9a-f]{40}', linked):
            kept = os.environ.get('RUNNER_TEMP')
            memo = Path(kept) / 'crysta-linked-commit' if kept else None
            if memo and memo.is_file() and memo.read_text(encoding='utf-8').strip() == linked:
                return linked
            if paired_commit(linked):
                if memo:
                    memo.write_text(linked + '\n', encoding='utf-8')
                return linked
    return paired_head()


def paired_commit(sha: str) -> bool:
    """Whether ``sha`` is a commit of the paired crysta branch that crysta main lacks.

    The rule and its lookups are crysta-source.sh's. An answer that cannot be read refuses.
    """
    asked = ['bash', str(ROOT / 'tools' / 'ci' / 'crysta-source.sh'), '--paired-commit', sha]
    r = subprocess.run(asked, capture_output=True, text=True, check=False)
    if r.returncode not in {0, 1}:
        refuse(
            f"whether {sha} is the paired crysta branch's could not be read: "
            f'{r.stderr.strip()[-300:]}'
        )
    return r.returncode == 0


def fetch(platform: str) -> Path:
    """Return the unpacked dir of the SDK this run builds: reused when present, else downloaded.

    That is the pinned SDK, bound by its committed sha256. A paired run whose pin does not name
    the crysta branch's head builds that head instead, from its pull-request run: the pin then
    matters at the final green, which this build is not.
    """
    tag, digest = pin(platform)
    head = run_head()
    if head and head != tag[6:]:
        print(
            f'crysta: the pin {tag} is stale; building the paired crysta branch head build-{head} '
            'from its pull-request run (no final green counts this build)',
            file=sys.stderr,
        )
        tag, digest = f'build-{head}', ''
    home = ROOT / 'build' / 'crysta-sdk' / f'{tag[6:]}-{platform}'
    home.parent.mkdir(parents=True, exist_ok=True)
    # One acquisition at a time into the cache every environment shares
    with (home.parent / '.lock').open('w') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        return _fetch(home, tag, digest, platform)


def listing(url: str, key: str) -> list[dict]:
    """Return the ``key`` rows of one REST listing; one that does not fit a page refuses."""
    page = json.loads(curl(f'{url}{"&" if "?" in url else "?"}per_page=100', accept=JSON))
    rows = page.get(key) or []
    if page.get('total_count', len(rows)) != len(rows):
        refuse(f'GET {url} lists {page.get("total_count")} {key}, more than one page holds')
    return rows


def executed_attempt(made: list[dict], last: dict) -> int:
    """Return the attempt in which the execution that the record ``last`` describes ran.

    A re-run of ANOTHER job of the run copies this job's record into the new attempt, with a new
    id and the execution's own start and end times. So the execution is the earliest record of
    the job with those times. A record without both times is its own attempt.
    """
    times = (last.get('started_at'), last.get('completed_at'))
    if None in times:
        return last.get('run_attempt') or 0
    same = [j for j in made if (j.get('started_at'), j.get('completed_at')) == times]
    return min(j.get('run_attempt') or 0 for j in same)


def tested_artifact(sha: str, platform: str) -> tuple[int, int, dict]:
    """Return the run, the attempt of its producing job's latest execution and its artifact (I8).

    The run is the one pull-request run of ci.yml at ``sha``; the event, the path and the head are
    read from the record, never trusted to the query. The producing job's latest execution
    succeeded, or at least packed, smoke-tested and uploaded its package (PACKAGE_STEPS). The
    artifact is that run's own, made at that head, and has not expired.
    """
    runs = listing(f'{API}/actions/runs?head_sha={sha}&event=pull_request', 'workflow_runs')
    wanted = (WORKFLOW, sha, 'pull_request')
    mine = [r for r in runs if (r.get('path'), r.get('head_sha'), r.get('event')) == wanted]
    if len(mine) != 1:
        refuse(f'crysta has no release build-{sha} and {len(mine)} pull-request runs at it')
    run_id, job = mine[0]['id'], PRODUCERS[platform]
    jobs = listing(f'{API}/actions/runs/{run_id}/jobs?filter=all', 'jobs')
    made = [j for j in jobs if j.get('name') == job]
    last = max(made, key=lambda j: j.get('run_attempt') or 0, default={})
    if last.get('conclusion') != 'success':
        steps = last.get('steps') or []
        packaged = last.get('status') == 'completed' and all(
            any(
                (s.get('name') or '').startswith(step) and s.get('conclusion') == 'success'
                for s in steps
            )
            for step in PACKAGE_STEPS
        )
        if not packaged:
            refuse(
                f'crysta run {run_id}: the latest execution of {job!r} is '
                f'{last.get("conclusion")} and did not pack, smoke-test and upload its package'
            )
        FAILED_STEPS[sha, platform] = sorted(
            s.get('name') or '' for s in steps if s.get('conclusion') == 'failure'
        )
    held = [
        a
        for a in listing(f'{API}/actions/runs/{run_id}/artifacts', 'artifacts')
        if a.get('name') == f'crysta-sdk-{platform}'
        and a.get('expired') is False
        and (a.get('workflow_run') or {}).get('id') == run_id
        and (a.get('workflow_run') or {}).get('head_sha') == sha
    ]
    if not held:
        refuse(f'crysta run {run_id} holds no unexpired crysta-sdk-{platform} artifact: {REPAIR}')
    newest = max(held, key=lambda a: a.get('created_at') or '')
    return run_id, executed_attempt(made, last), newest


def named(manifest: dict) -> tuple:
    """Return the commit, run, execution and job an SDK's manifest says it was tested in."""
    tested = manifest.get('tested') or {}
    return (
        manifest.get('source_sha'),
        str(tested.get('run_id')),
        str(tested.get('run_attempt')),
        tested.get('job_name'),
    )


def run_package(
    sha: str, platform: str, tmp: Path, proof: tuple[int, int, dict] | None = None
) -> Path:
    """Download ``platform``'s tested package from crysta's pull-request run at ``sha`` (I8).

    The package is the one `tested_artifact` selects (``proof``, when the caller has it). Its
    manifest names that commit, that run and that execution, and the tarball matches its .sha256
    file. The caller binds the tarball to the committed sha256 when there is one, and `check`
    binds its files (I25).
    """
    run_id, attempt, newest = proof or tested_artifact(sha, platform)
    curl(f'{API}/actions/artifacts/{newest["id"]}/zip', accept=JSON, out=tmp / 'package.zip')
    name = f'crysta-sdk-{sha}-{platform}.tar.gz'
    with zipfile.ZipFile(tmp / 'package.zip') as packed:
        if sorted(packed.namelist()) != [name, f'{name}.sha256']:
            refuse(
                f'crysta run {run_id}: the artifact holds {sorted(packed.namelist())}, not {name}'
            )
        side = packed.read(f'{name}.sha256').decode().split()
        (tmp / name).write_bytes(packed.read(name))
    if side[:1] != [sha256(tmp / name)]:
        refuse(f'crysta run {run_id}: {name} does not match its .sha256')
    with tarfile.open(tmp / name) as tar:
        names = named(json.load(tar.extractfile(MANIFEST)))
    if names != (sha, str(run_id), str(attempt), PRODUCERS[platform]):
        refuse(
            f'crysta run {run_id}: {name} names {names}, not {sha} from execution '
            f'{attempt} of {PRODUCERS[platform]!r}: {REPAIR}'
        )
    return tmp / name


def _fetch(home: Path, tag: str, digest: str, platform: str) -> Path:
    """Reuse ``home`` when it is proven to be the build ``tag``, else download and unpack it.

    ``digest`` is the committed sha256 of a pinned build: an unpacked SDK whose marker holds it is
    that build. It is empty for a paired branch head, which has none. That build comes from its
    pull-request run alone, so every call proves the run first (I8: the one run at the commit, the
    producing job's package steps passed, an unexpired artifact of that run), and an
    unpacked SDK is reused only when its manifest names that commit, run and execution. A failed
    re-run, a newer execution or an expired artifact therefore never leaves a kept SDK in use. The
    marker holds the tarball's sha256.
    """
    marker, sha = home / '.sdk-sha256', tag[6:]
    proof = None if digest else tested_artifact(sha, platform)
    if digest and marker.is_file() and marker.read_text().strip() == digest:
        return home
    if proof and marker.is_file() and (home / MANIFEST).is_file():
        kept = named(json.loads((home / MANIFEST).read_text(encoding='utf-8')))
        if kept == (sha, str(proof[0]), str(proof[1]), PRODUCERS[platform]):
            return home
    name = f'crysta-sdk-{sha}-{platform}.tar.gz'
    found = curl(f'{API}/releases/tags/{tag}', accept=JSON, absent_ok=True) if digest else None
    with tempfile.TemporaryDirectory(dir=os.environ.get('RUNNER_TEMP') or None) as tmp:
        if found is None:  # No release, so the pull-request run's tested package
            tarball = run_package(sha, platform, Path(tmp), proof)
        else:
            assets = [a for a in json.loads(found).get('assets', []) if a.get('name') == name]
            if len(assets) != 1:
                refuse(f'release {tag} carries {len(assets)} asset(s) named {name}')
            tarball = Path(tmp) / name
            curl(
                f'{API}/releases/assets/{assets[0]["id"]}',
                accept='application/octet-stream',
                out=tarball,
            )
        got = sha256(tarball)
        if digest and got != digest:
            refuse(f'{name} has sha256 {got}, not the pinned {digest}')
        shutil.rmtree(home, ignore_errors=True)
        home.mkdir(parents=True)
        with tarfile.open(tarball) as tar:
            tar.extractall(home, filter='data')
    marker.write_text(got + '\n', encoding='utf-8')
    return home


def main(argv: list[str]) -> int:
    """Dispatch a subcommand; a refusal exits 1."""
    parser = argparse.ArgumentParser(prog='crysta_sdk.py', description=__doc__)
    sub = parser.add_subparsers(dest='cmd', required=True)
    sub.add_parser('fetch').add_argument('--platform', required=True, choices=PLATFORMS)
    # The declared shas, one line per platform ('' where none is declared)
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
        print('\n'.join(declared_shas(a.pixi_toml.read_text(encoding='utf-8'))))
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
