# SPDX-License-Identifier: BSD-3-Clause
"""The crysta SDK update branch (ADR-0017).

  crysta_sdk_update.py --crysta-clone K

Finds the newest build-<sha> prerelease on crysta main that is newer than edi's pin, pushes
`crysta-sdk/<sha12>` from edi main with only the pin lines changed, and dispatches ci.yml on it (a
run started by the job token's push triggers no pull_request run; the dispatched run is a full
one). A maintainer opens the PR and merges it on that CI evidence.
Superseded `crysta-sdk/*` branches are deleted only when a complete open-PR listing proves no open
PR uses them. crysta reads use CRYSTA_TOKEN (the App token); edi's push, dispatch and PR listing
use GH_TOKEN (the workflow's own token). Every refusal exits 1 naming its cause.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import NoReturn

sys.path.insert(0, str(Path(__file__).resolve().parent))
import crysta_sdk  # THE pin reader, beside this file

ROOT = Path(__file__).resolve().parents[2]
PIN = re.compile(r'^CRYSTA_SDK_(TAG|SHA256)\s*=')


class RefusedError(Exception):
    """A precondition failed: no branch is pushed and nothing is deleted."""


def refuse(message: str) -> NoReturn:
    """Stop with ``message`` as the refusal."""
    raise RefusedError(message)


def run(*argv: str, cwd: Path = ROOT, token: str | None = None) -> str:
    """Run a git or gh operation (gh as ``token`` when given); a failure refuses, naming it."""
    env = {**os.environ, 'GH_TOKEN': token} if token else None
    r = subprocess.run(argv, cwd=cwd, capture_output=True, text=True, check=False, env=env)
    if r.returncode:
        refuse(f'{" ".join(argv[:3])} … failed ({r.returncode}): {r.stderr.strip()[:300]}')
    return r.stdout


def pinned_sha() -> str:
    """Return the one crysta build edi main pins, per crysta_sdk.py's contract (class B)."""
    try:
        shas = {
            s for s in crysta_sdk.declared_shas(run('git', 'show', 'origin/main:pixi.toml')) if s
        }
    except crysta_sdk.RefusedError as refusal:
        refuse(str(refusal))
    if len(shas) != 1:
        refuse(f'edi main pins {sorted(shas) or "no"} crysta build(s); expected one')
    return shas.pop()


def releases(slurped: list) -> list[dict]:
    """Return release records from `gh api --paginate --slurp` (pages, or one flat array)."""
    return [r for item in slurped for r in (item if isinstance(item, list) else [item])]


def newest_build(crysta: Path, pin: str) -> str | None:
    """Return the newest build-<sha> on crysta main that descends from the pin, or None."""
    token = os.environ.get('CRYSTA_TOKEN') or refuse(
        'no CRYSTA_TOKEN: crysta releases are unreadable'
    )
    pages = json.loads(
        run('gh', 'api', '--paginate', '--slurp', 'repos/enhantica/crysta/releases', token=token)
    )
    shas = {
        r['tag_name'][6:]
        for r in releases(pages)
        if re.fullmatch(r'build-[0-9a-f]{40}', r['tag_name'])
    }
    order = run('git', 'rev-list', 'origin/main', cwd=crysta).split()  # newest first
    landed = pin if pin in order else landed_as(crysta, pin, token)
    if (
        landed is None
    ):  # a paired PR-head pin whose crysta PR has not landed: nothing newer to propose
        print(f'crysta-sdk-update: the pinned crysta {pin} has not landed on crysta main yet')
        return None
    newer = order[: order.index(landed)]
    return next((sha for sha in newer if sha in shas), None)


def landed_as(crysta: Path, pin: str, token: str) -> str | None:
    """Return the crysta main commit carrying a squashed paired pin's tree (None: not landed).

    F17: a paired PR-head pin is no main ancestor after its squash. The guard merged it only with
    main inside the head, so the squash commit carries exactly the head's tree. The head is read
    through its retained build-<sha> tag.
    """
    url = f'https://x-access-token:{token}@github.com/enhantica/crysta.git'
    run('git', 'fetch', '--quiet', url, f'refs/tags/build-{pin}:refs/tags/build-{pin}', cwd=crysta)
    tree = run('git', 'rev-parse', f'{pin}^{{tree}}', cwd=crysta).strip()
    trees = run('git', 'log', '--format=%H %T', 'origin/main', cwd=crysta).split('\n')
    return next((c for c, t in (ln.split() for ln in trees if ln.strip()) if t == tree), None)


def open_pr_heads() -> set[str]:
    """Return every open PR's head branch, from a complete listing (a partial one refuses)."""
    q = 'repo:enhantica/edi is:pr is:open'
    pages = json.loads(
        run('gh', 'api', '--paginate', '--slurp', '-X', 'GET', 'search/issues', '-f', f'q={q}')
    )
    pages = pages if isinstance(pages, list) else [pages]  # `--slurp` pages, or one response
    items = {i['number']: i for page in pages for i in page['items']}
    if (
        not pages
        or any(p['total_count'] != len(items) for p in pages)
        or any(p.get('incomplete_results') for p in pages)
    ):
        refuse('the open-PR listing is incomplete; no branch is deleted')
    return {  # a search item carries no head branch on GitHub; read the PR when it is not inline
        (item.get('head') or {}).get('ref')
        or json.loads(run('gh', 'api', f'repos/enhantica/edi/pulls/{number}'))['head']['ref']
        for number, item in items.items()
    }


def main(argv: list[str]) -> int:
    """Push the update branch for the newest build, then prune superseded update branches."""
    parser = argparse.ArgumentParser(prog='crysta_sdk_update.py', description=__doc__)
    parser.add_argument('--crysta-clone', required=True, type=Path)
    a = parser.parse_args(argv)
    try:
        update(a.crysta_clone)
    except (RefusedError, OSError, KeyError, ValueError) as refusal:
        print(f'crysta-sdk-update: REFUSED — {refusal}', file=sys.stderr)
        return 1
    return 0


def dispatched(branch: str) -> None:
    """F17: a published proposal still needs a dispatched CI run at its head."""
    head = run('git', 'rev-parse', f'refs/remotes/origin/{branch}').strip()
    flags = '--workflow ci.yml --event workflow_dispatch --json headSha --limit 50'
    runs = json.loads(run('gh', 'run', 'list', *flags.split(), '--branch', branch))
    if any(r.get('headSha') == head for r in runs):
        print(f'crysta-sdk-update: {branch} is already proposed and its CI run exists')
    else:
        run('gh', 'workflow', 'run', 'ci.yml', '--ref', branch)
        print(f'crysta-sdk-update: {branch} was pushed without a CI run — dispatched ci.yml')


def propose(branch: str, sha: str, *, held: bool) -> None:
    """Publish ``branch`` pinning ``sha`` once its diff is exactly the pin lines for ``sha``.

    The branch is built on origin/main, or, when ``held``, it is the local commit an earlier failed
    push left.
    """
    if held:
        run('git', 'switch', branch)
        if (
            run('git', 'rev-parse', 'HEAD^').strip()
            != run('git', 'rev-parse', 'origin/main').strip()
        ):
            refuse(f'the local {branch} is not one commit on origin/main: remove it, then retry')
    else:
        run('git', 'switch', '-c', branch, 'origin/main')
        env_token = os.environ['CRYSTA_TOKEN']
        r = subprocess.run(
            [sys.executable, 'tools/ci/crysta_sdk_pin.py', sha],
            cwd=ROOT,
            env={**os.environ, 'GITHUB_TOKEN': env_token, 'GH_TOKEN': env_token},
            check=False,
        )
        if r.returncode:
            refuse(f'crysta-sdk-pin {sha} failed')
    diff = run('git', 'diff', '--unified=0', 'origin/main', '--', '.').splitlines()
    changed = [ln[1:] for ln in diff if ln[:1] in {'+', '-'} and not ln.startswith(('+++', '---'))]
    try:  # the proposal pins exactly this build, as THE contract reads the proposed file (class B)
        tags = {
            t
            for t in crysta_sdk.declared_shas((ROOT / 'pixi.toml').read_text(encoding='utf-8'))
            if t
        }
    except crysta_sdk.RefusedError as refusal:
        refuse(f'the proposed pixi.toml: {refusal}')
    files = run('git', 'diff', '--name-only', 'origin/main').split()
    if files != ['pixi.toml'] or not all(PIN.match(ln) for ln in changed) or tags != {sha}:
        refuse(f'the update diff is not exactly the pin lines for {sha}: {files} {changed}')
    if not held:
        run('git', 'commit', '-qam', f'Pin crysta build-{sha} (crysta SDK update)')
    run('git', 'push', 'origin', f'HEAD:refs/heads/{branch}')
    run('gh', 'workflow', 'run', 'ci.yml', '--ref', branch)
    print(f'crysta-sdk-update: pushed {branch} and dispatched ci.yml on it')


def update(crysta: Path) -> None:
    """Propose the newest build, then delete superseded update branches no open PR uses."""
    sha = newest_build(crysta, pinned_sha())
    branch = f'crysta-sdk/{sha[:12]}' if sha else None
    # F08: origin's update branches (published proposals, as the checkout fetched them) and local
    # heads (a commit whose push failed) are two states, never one
    refs = ('refs/remotes/origin/crysta-sdk/', 'refs/heads/crysta-sdk/')
    listed = run('git', 'for-each-ref', '--format=%(refname)', *refs).split()
    published = {r.split('/crysta-sdk/', 1)[1] for r in listed if r.startswith(refs[0])}
    local = {r.split('/crysta-sdk/', 1)[1] for r in listed if r.startswith(refs[1])}
    name = branch.split('/', 1)[1] if branch else None
    if sha is None:
        print('crysta-sdk-update: edi main pins the newest crysta main build')
    elif name in published:
        dispatched(branch)
    else:
        propose(branch, sha, held=name in local)
    stale = sorted(f'crysta-sdk/{n}' for n in published if n != name)  # never a local-only name
    if stale:
        used = open_pr_heads()
        for name in stale:
            if name in used:
                print(f'crysta-sdk-update: {name} kept — an open PR uses it')
            else:
                run('git', 'push', 'origin', '--delete', name)
                print(f'crysta-sdk-update: deleted superseded {name}')


if __name__ == '__main__':
    raise SystemExit(main(sys.argv[1:]))
