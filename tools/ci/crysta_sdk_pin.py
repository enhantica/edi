# SPDX-License-Identifier: BSD-3-Clause
"""Pin a crysta SDK build in edi's pixi.toml (ADR-0017; D3).

  crysta_sdk_pin.py <sha>      pin build-<sha> for every platform
  crysta_sdk_pin.py --check    is the pin in this checkout exactly its release's assets?

`<sha>` takes each platform's sha256 from build-<sha>'s release (GitHub's own asset digests) when
crysta has one, and otherwise from the tested packages of crysta's pull-request run at that
commit (I8). `--check` is the ship step: a pin whose build
has no release, or differs from it, exits 1.

The `crysta-sdk-pin` task and the scheduled update workflow run this on a desk or a hosted runner,
where `gh` is installed; the CI fleet never runs it. Only the pin lines change. Every refusal
exits 1 naming its cause.
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import NoReturn

sys.path.insert(0, str(Path(__file__).resolve().parent))
import crysta_sdk  # THE pin reader and the pull-request-run package route, beside this file

ROOT = Path(__file__).resolve().parents[2]
PLATFORMS = ('linux-64', 'osx-arm64')


class RefusedError(Exception):
    """A precondition failed: pixi.toml is not changed."""


def refuse(message: str) -> NoReturn:
    """Stop with ``message`` as the refusal."""
    raise RefusedError(message)


def token() -> str:
    """Return the token that reads crysta's releases."""
    return os.environ.get('GITHUB_TOKEN') or os.environ.get('GH_TOKEN') or ''


def gh(*args: str, absent_ok: bool = False) -> bytes | None:
    """Read crysta through `gh`: the pin is written on a hosted runner or a desk, not the fleet.

    With ``absent_ok`` a 404, and only a 404, returns None: what was asked for does not exist.
    """
    env = {**os.environ, 'GH_TOKEN': token()}
    r = subprocess.run(['gh', 'api', *args], capture_output=True, check=False, env=env)
    if r.returncode:
        why = r.stderr.decode(errors='replace')[:200]
        if absent_ok and 'HTTP 404' in why:
            return None
        refuse(f'gh api {args[-1]} failed ({r.returncode}): {why}')
    return r.stdout


def run_digests(sha: str) -> dict[str, str]:
    """Return each platform's sha256 from crysta's pull-request run at ``sha``."""
    if not token():  # crysta_sdk reads crysta with curl and a token; a desk has gh's own login
        login = subprocess.run(
            ['gh', 'auth', 'token'], capture_output=True, check=False, text=True
        )
        os.environ['GH_TOKEN'] = login.stdout.strip()
    digests = {}
    try:
        for platform in PLATFORMS:
            with tempfile.TemporaryDirectory() as tmp:
                digests[platform] = crysta_sdk.sha256(
                    crysta_sdk.run_package(sha, platform, Path(tmp))
                )
    except crysta_sdk.RefusedError as refusal:
        refuse(str(refusal))
    return digests


def pin_digests(sha: str, *, released: bool = False) -> dict[str, str]:
    """Return each platform's sha256 for build-<sha>: its release's, else its run's packages'."""
    tag = f'build-{sha}'
    found = gh(f'repos/enhantica/crysta/releases/tags/{tag}', absent_ok=True)
    if found is None:
        if released:
            refuse(f'crysta has no release {tag}: dispatch its sdk-publish.yml for {sha}')
        return run_digests(sha)
    release = json.loads(found)
    by_name = {a.get('name'): a for a in release.get('assets', [])}
    assets = {}
    for platform in PLATFORMS:  # GitHub's own asset digest, else the tarball's .sha256 sidecar
        name = f'crysta-sdk-{sha}-{platform}.tar.gz'
        asset, side = by_name.get(name), by_name.get(f'{name}.sha256')
        digest = (asset or {}).get('digest') or ''
        if digest.startswith('sha256:'):
            digest = digest[len('sha256:') :]
        elif asset and side:
            text = gh('-H', 'Accept: application/octet-stream', side['url']).decode()
            digest = text.split()[0] if text.split() else ''
        if not re.fullmatch(r'[0-9a-f]{64}', digest):
            refuse(f'release {tag} gives no sha256 for {name}')
        assets[platform] = digest
    return assets


def check_pin() -> None:
    """Refuse unless this checkout's pin is its build's release, asset for asset."""
    try:
        pins = {platform: crysta_sdk.pin(platform) for platform in PLATFORMS}
    except crysta_sdk.RefusedError as refusal:
        refuse(str(refusal))
    tags = sorted({tag for tag, _ in pins.values()})
    if len(tags) != 1:
        refuse(f'pixi.toml pins {tags}, not one build')
    assets = pin_digests(tags[0][6:], released=True)
    wrong = {p: (pins[p][1], assets[p]) for p in PLATFORMS if pins[p][1] != assets[p]}
    if wrong:
        refuse(f'the pin is not release {tags[0]}: {wrong} (pinned, released)')
    print(f'crysta-sdk-pin: the pin is release {tags[0]}, asset for asset')


def write_pin(sha: str) -> None:
    """Pin build-<sha> for every platform (the crysta-sdk-pin task)."""
    tag, digests = f'build-{sha}', pin_digests(sha)
    lines = (ROOT / 'pixi.toml').read_text(encoding='utf-8').split('\n')
    note = '# crysta pack from a failed job, its package steps passed; failed:'
    for platform in PLATFORMS:  # only the pin lines change: every other byte of pixi.toml is kept
        header = f'[target.{platform}.activation.env]'
        if header not in lines:
            refuse(f'pixi.toml has no {header} to carry the pin')
        h = lines.index(header)
        for key, value in (('CRYSTA_SDK_TAG', tag), ('CRYSTA_SDK_SHA256', digests[platform])):
            end = next(
                (k for k in range(h + 1, len(lines)) if lines[k].startswith('[')), len(lines)
            )
            found = [k for k in range(h + 1, end) if re.match(rf'{key}\s*=', lines[k])]
            if len(found) > 1:
                refuse(f'{header} declares {key} {len(found)} times')
            if found:
                lines[found[0]] = f'{key} = "{value}"'
            else:
                last = max([k for k in range(h + 1, end) if lines[k].strip()] or [h])
                lines.insert(last + 1, f'{key} = "{value}"')
        # The pin's provenance: the failed steps of a job whose package was taken, else nothing.
        end = next((k for k in range(h + 1, len(lines)) if lines[k].startswith('[')), len(lines))
        for k in reversed([k for k in range(h + 1, end) if lines[k].startswith(note)]):
            del lines[k]
        failed = crysta_sdk.FAILED_STEPS.get((sha, platform))
        if failed:
            at = next(
                k for k in range(h + 1, len(lines)) if lines[k].startswith('CRYSTA_SDK_SHA256')
            )
            lines.insert(at + 1, f'{note} {"; ".join(failed)}')
    (ROOT / 'pixi.toml').write_text('\n'.join(lines), encoding='utf-8')
    print(f'crysta-sdk-pin: pixi.toml pins {tag} for {", ".join(PLATFORMS)}')


def main(argv: list[str]) -> int:
    """Pin build-<sha>, or check the pin with --check; a refusal exits 1."""
    try:
        if argv == ['--check']:
            check_pin()
            return 0
        if len(argv) != 1 or not re.fullmatch(r'[0-9a-f]{40}', argv[0]):
            refuse(f'usage: crysta_sdk_pin.py <40-hex sha> | --check (got {argv})')
        write_pin(argv[0])
    except (RefusedError, OSError, KeyError, ValueError) as refusal:
        print(f'crysta_sdk_pin.py: REFUSED — {refusal}', file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    raise SystemExit(main(sys.argv[1:]))
