# SPDX-License-Identifier: BSD-3-Clause
"""Delete a merged pull request's run artifacts, keeping what a release or a live ref still needs.

    branch_artifacts.py --repo OWNER/NAME --pr N [--dry-run]

Only a merged pull request from this repository is cleaned: a closed, unmerged one can be reopened,
so its runs stay until GitHub's retention removes them. A run is in the deletion set only when it
ran on the pull request's branch in this repository, at one of the pull request's own commits, and
finished. Nothing is deleted while another open pull request uses the same branch, and a run whose
commit is still another open pull request's head is kept. Release inputs and the crysta SDK
artifacts are always kept.

Every listing is read in full before anything is deleted: each entry once, as many as GitHub
reports. A listing that cannot be proven whole refuses with exit 2 and deletes nothing.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import urllib.parse
import urllib.request
from collections.abc import Callable

API = (os.environ.get('GITHUB_API_URL') or 'https://api.github.com').rstrip('/')
# What a release or a later ship still reads.
KEEP = re.compile(
    r'^(release-plan-|qualified-release-plan-|offsite-|smartscreen-submission$|installer-)'
)
# edi's crysta SDK artifact is the build its pin needs.
SDK = re.compile(r'^crysta-sdk-')
# GitHub lists at most this many of a pull request's commits, and this many filtered runs.
PR_COMMITS_CAP = 250
RUNS_CAP = 1000

# One REST read: the JSON body and the next page's URL ('' on the last page).
Fetch = Callable[[str], tuple[object, str]]


class RefusedError(Exception):
    """A listing could not be proven whole: nothing is deleted."""


def gh_fetch(path: str) -> tuple[object, str]:
    url = path if path.startswith('https://') else f'{API}/{path}'
    request = urllib.request.Request(url)  # noqa: S310 - GitHub's API
    request.add_header('Authorization', f'Bearer {os.environ["GH_TOKEN"]}')
    request.add_header('Accept', 'application/vnd.github+json')
    request.add_header('X-GitHub-Api-Version', '2022-11-28')
    try:
        with urllib.request.urlopen(request, timeout=120) as answer:  # noqa: S310
            body, link = json.loads(answer.read()), answer.headers.get('Link', '')
    except (OSError, ValueError) as error:
        raise RefusedError(f'cannot read {url}: {error}') from error
    found = re.search(r'<([^>]+)>;\s*rel="next"', link)
    return body, found.group(1) if found else ''


def listing(fetch: Fetch, path: str, key: str | None, ident: Callable[[dict], object]) -> list:
    """Every entry of a paged listing, each identity once.

    A listing with a total_count (``key`` names its rows) must keep that total on every page and
    end with exactly that many entries; a plain array listing is read until GitHub names no next
    page.
    """
    rows, seen, totals, url = [], set(), set(), path
    while url:
        body, url = fetch(url)
        if key is None:
            items = body
        else:
            items = body.get(key) if isinstance(body, dict) else None
            total = body.get('total_count') if isinstance(body, dict) else None
            if not isinstance(total, int) or isinstance(total, bool):
                raise RefusedError(f'{path}: a page has no total_count')
            totals.add(total)
        if not isinstance(items, list) or not all(isinstance(i, dict) for i in items):
            raise RefusedError(f'{path}: a page is not a list of entries')
        for item in items:
            name = ident(item)
            if name is None or name in seen:
                raise RefusedError(f'{path}: entry {name!r} is missing its identity or repeated')
            seen.add(name)
            rows.append(item)
    if key is not None and (len(totals) != 1 or len(rows) != next(iter(totals))):
        raise RefusedError(f'{path}: {len(rows)} {key} read, totals {sorted(totals)}')
    return rows


def own_commits(fetch: Fetch, repo: str, number: int, count: object) -> set[str]:
    """Return the pull request's commits, exactly as many as it reports."""
    if not isinstance(count, int) or isinstance(count, bool) or count >= PR_COMMITS_CAP:
        raise RefusedError(f'#{number} has {count} commits; GitHub lists only {PR_COMMITS_CAP}')
    commits = listing(
        fetch, f'repos/{repo}/pulls/{number}/commits?per_page=100', None, lambda c: c.get('sha')
    )
    if len(commits) != count:
        raise RefusedError(f'#{number} has {count} commits, {len(commits)} were read')
    return {c['sha'] for c in commits}


def select(fetch: Fetch, repo: str, number: int, keep_sdk: Callable[[dict], bool]) -> list[dict]:
    """The artifacts the closed pull request ``number`` leaves that may be deleted."""
    pr = fetch(f'repos/{repo}/pulls/{number}')[0]
    if not isinstance(pr, dict) or pr.get('number') != number:
        raise RefusedError(f'pull request {number} could not be read')
    head = pr.get('head') or {}
    branch = head.get('ref')
    if (head.get('repo') or {}).get('full_name') != repo or not branch:
        print(f'branch artifacts: #{number} comes from another repository: nothing to delete')
        return []
    if pr.get('state') != 'closed' or not pr.get('merged_at'):
        print(f'branch artifacts: #{number} is not merged, it may be reopened: nothing deleted')
        return []

    own = own_commits(fetch, repo, number, pr.get('commits'))
    others = [
        p
        for p in listing(
            fetch, f'repos/{repo}/pulls?state=open&per_page=100', None, lambda p: p.get('number')
        )
        if p['number'] != number
    ]
    if any(
        (p.get('head') or {}).get('ref') == branch
        and ((p.get('head') or {}).get('repo') or {}).get('full_name') == repo
        for p in others
    ):
        print(f'branch artifacts: another open pull request uses {branch}: nothing deleted')
        return []
    live = {(p.get('head') or {}).get('sha') for p in others}

    runs = listing(
        fetch,
        f'repos/{repo}/actions/runs?branch={urllib.parse.quote(branch, safe="")}&per_page=100',
        'workflow_runs',
        lambda r: r.get('id'),
    )
    if len(runs) >= RUNS_CAP:
        raise RefusedError(f'{branch} has {len(runs)} runs; GitHub lists only {RUNS_CAP}')
    mine = [
        r
        for r in runs
        if (r.get('head_repository') or {}).get('full_name') == repo
        and r.get('head_branch') == branch
        and r.get('head_sha') in own
        and r.get('head_sha') not in live
        and r.get('status') == 'completed'
    ]
    doomed = []
    for run in mine:
        for artifact in listing(
            fetch,
            f'repos/{repo}/actions/runs/{run["id"]}/artifacts?per_page=100',
            'artifacts',
            lambda a: a.get('id'),
        ):
            name = str(artifact.get('name', ''))
            if artifact.get('expired') or KEEP.match(name) or (SDK.match(name) and keep_sdk(run)):
                continue
            doomed.append(artifact)
    print(
        f'branch artifacts: {branch}: {len(runs)} run(s) listed, {len(mine)} of this pull '
        f'request, deleting {len(doomed)} artifact(s)'
    )
    return doomed


def delete(repo: str, artifacts: list[dict]) -> None:
    for artifact in artifacts:
        url = f'{API}/repos/{repo}/actions/artifacts/{artifact["id"]}'
        request = urllib.request.Request(url, method='DELETE')  # noqa: S310 - GitHub's API
        request.add_header('Authorization', f'Bearer {os.environ["GH_TOKEN"]}')
        request.add_header('X-GitHub-Api-Version', '2022-11-28')
        with urllib.request.urlopen(request, timeout=120):  # noqa: S310
            pass


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split('\n\n')[0])
    parser.add_argument('--repo', required=True)
    parser.add_argument('--pr', type=int, required=True)
    parser.add_argument('--dry-run', action='store_true')
    args = parser.parse_args(argv)
    try:
        doomed = select(gh_fetch, args.repo, args.pr, lambda _run: True)
    except RefusedError as e:
        print(f'branch artifacts: {e} (nothing deleted)')
        return 2
    if not args.dry_run:
        delete(args.repo, doomed)
    return 0


if __name__ == '__main__':
    sys.exit(main())
