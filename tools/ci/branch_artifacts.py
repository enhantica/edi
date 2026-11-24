# SPDX-License-Identifier: BSD-3-Clause
"""Delete a merged pull request's run artifacts, keeping what a release or a live ref still needs.

    branch_artifacts.py --repo OWNER/NAME --pr N [--dry-run]

Only a merged pull request from this repository is cleaned: a closed, unmerged one can be reopened,
so its runs stay until GitHub's retention removes them.

Branch and commit alone do not say whose run it is: an earlier pull request may have used both, and
a manual run may have been started there. A `pull_request` run is started by a pull request whose
head is the run's head repository and branch. So a run belongs to this pull request when

- its event is `pull_request`, on this repository's branch of that name;
- no other pull request, in any state, ever had that branch as its head (a closed one can still
  start runs, when it is edited or labeled);
- it ran at one of this pull request's commits, and was created and last started while the pull
  request was open;
- it finished, and where GitHub still names its pull requests, names only this one.

A run that fails any of these, or whose record does not show it, keeps its artifacts. Nothing is
deleted while another open pull request uses the branch, and a run whose commit is still another
open pull request's head is kept; an open pull request without a readable head refuses. An artifact
is deleted only when its own record names the run and its commit. Release inputs and the crysta SDK
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
from collections import Counter
from collections.abc import Callable
from datetime import datetime

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
    token = os.environ.get('GH_TOKEN')
    if not token:
        raise RefusedError('no GH_TOKEN: GitHub cannot be read')
    request = urllib.request.Request(url)  # noqa: S310 - GitHub's API
    request.add_header('Authorization', f'Bearer {token}')
    request.add_header('Accept', 'application/vnd.github+json')
    request.add_header('X-GitHub-Api-Version', '2022-11-28')
    try:
        with urllib.request.urlopen(request, timeout=120) as answer:  # noqa: S310
            body, link = json.loads(answer.read()), answer.headers.get('Link', '')
    except (OSError, ValueError) as error:
        raise RefusedError(f'cannot read {url}: {error}') from error
    found = re.search(r'<([^>]+)>;\s*rel="next"', link)
    return body, found.group(1) if found else ''


def text(value: object) -> bool:
    """Whether the value is a name GitHub could mean: a string that is not empty."""
    return isinstance(value, str) and bool(value)


def commit_id(value: object) -> bool:
    """Whether the value is a commit's full name: 40 lowercase hexadecimal digits."""
    return isinstance(value, str) and re.fullmatch(r'[0-9a-f]{40}', value) is not None


def repository(value: object) -> bool:
    """Whether the value names a repository as GitHub does: owner/name."""
    return isinstance(value, str) and re.fullmatch(r'[\w.-]+/[\w.-]+', value) is not None


def whole_number(value: object) -> bool:
    """Whether the value is an integer, which a JSON true or false is not."""
    return isinstance(value, int) and not isinstance(value, bool)


def moment(record: dict, field: str) -> datetime | None:
    """Return the record's timestamp, or None unless it names its time zone."""
    value = record.get(field)
    try:
        when = datetime.fromisoformat(value) if isinstance(value, str) else None
    except ValueError:
        return None
    return when if when is not None and when.tzinfo is not None else None


def number_in(field: str) -> Callable[[dict], object]:
    """Identify an entry by its whole number."""
    return lambda entry: entry[field] if whole_number(entry.get(field)) else None


def listing(fetch: Fetch, path: str, key: str | None, ident: Callable[[dict], object]) -> list:
    """Every entry of a paged listing, each identity once.

    A listing with a total_count (``key`` names its rows) must keep that total on every page and
    end with exactly that many entries; a plain array listing is read until GitHub names no next
    page. A page that names a next one must have entries, and no page is read twice.
    """
    rows, seen, totals, pages, url = [], set(), set(), set(), path
    while url:
        if url in pages:
            raise RefusedError(f'{path}: page {url} comes after itself')
        pages.add(url)
        body, url = fetch(url)
        if key is None:
            items = body
        else:
            items = body.get(key) if isinstance(body, dict) else None
            total = body.get('total_count') if isinstance(body, dict) else None
            if not whole_number(total):
                raise RefusedError(f'{path}: a page has no total_count')
            totals.add(total)
        if not isinstance(items, list) or not all(isinstance(i, dict) for i in items):
            raise RefusedError(f'{path}: a page is not a list of entries')
        if url and not items:
            raise RefusedError(f'{path}: an empty page names a next one')
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
    if not whole_number(count) or count >= PR_COMMITS_CAP:
        raise RefusedError(f'#{number} has {count} commits; GitHub lists only {PR_COMMITS_CAP}')
    commits = listing(
        fetch,
        f'repos/{repo}/pulls/{number}/commits?per_page=100',
        None,
        lambda c: c['sha'] if commit_id(c.get('sha')) else None,
    )
    if len(commits) != count:
        raise RefusedError(f'#{number} has {count} commits, {len(commits)} were read')
    return {c['sha'] for c in commits}


def head_of(pr: dict) -> tuple[str, str, str] | None:
    """Return the pull request's head repository, branch and commit; None if unreadable."""
    head = pr.get('head')
    repo = head.get('repo') if isinstance(head, dict) else None
    if not isinstance(repo, dict):
        return None
    name, ref, sha = repo.get('full_name'), head.get('ref'), head.get('sha')
    return (name, ref, sha) if repository(name) and text(ref) and commit_id(sha) else None


def merged_pull(fetch: Fetch, repo: str, number: int) -> dict | None:
    """Return the pull request's record, or None when it is another repository's or not merged."""
    pr = fetch(f'repos/{repo}/pulls/{number}')[0]
    if not isinstance(pr, dict) or pr.get('number') != number or not whole_number(pr['number']):
        raise RefusedError(f'pull request {number} could not be read')
    head = head_of(pr)
    if head is None:
        raise RefusedError(f'#{number} has no readable head repository, branch and commit')
    if head[0] != repo:
        print(f'branch artifacts: #{number} comes from another repository: nothing to delete')
        return None
    state, merged = pr.get('state'), pr.get('merged_at', '')
    if not text(state) or state not in {'open', 'closed'}:
        raise RefusedError(f'#{number} is {state!r}')
    if state == 'open' and merged is not None:
        raise RefusedError(f'#{number} is {state!r} with merged_at {merged!r}')
    if merged is None:
        print(f'branch artifacts: #{number} is not merged, it may be reopened: nothing deleted')
        return None
    opened, closed = moment(pr, 'created_at'), moment(pr, 'merged_at')
    if opened is None or closed is None or closed < opened:
        raise RefusedError(f'#{number} has no readable created_at and merged_at')
    return pr


def only_user(fetch: Fetch, repo: str, number: int, head: tuple[str, str, str]) -> bool:
    """Whether no other pull request has, or ever had, this one's head branch.

    Two listings say so: the open pull requests, and every pull request with that head. The second
    must name this pull request too, and only that branch: GitHub ignores a filter it cannot read.
    """
    owner = urllib.parse.quote(repo.split('/', maxsplit=1)[0], safe='')
    branch = urllib.parse.quote(head[1], safe='')
    users = listing(
        fetch,
        f'repos/{repo}/pulls?state=all&head={owner}:{branch}&per_page=100',
        None,
        number_in('number'),
    )
    for pr in users:
        found = pr.get('head')
        if not isinstance(found, dict) or found.get('ref') != head[1]:
            raise RefusedError(f'#{pr["number"]} is listed under {head[1]} but does not name it')
    mine = [pr for pr in users if pr['number'] == number]
    if len(mine) != 1 or head_of(mine[0]) != head:
        raise RefusedError(
            f'the pull requests with the head {head[1]} do not include #{number} as read'
        )
    others = sorted(pr['number'] for pr in users if pr['number'] != number)
    if others:
        print(f'branch artifacts: {others} used {head[1]} too: nothing deleted')
    return not others


def open_heads(fetch: Fetch, repo: str, number: int) -> set[tuple[str, str, str]]:
    """Return every other open pull request's head; one that is unreadable refuses."""
    heads = set()
    for pr in listing(
        fetch, f'repos/{repo}/pulls?state=open&per_page=100', None, number_in('number')
    ):
        head = head_of(pr)
        if head is None:
            raise RefusedError(f'open pull request #{pr["number"]} has no readable head')
        if pr['number'] == number:
            raise RefusedError(f'#{number} is merged and listed as open')
        heads.add(head)
    return heads


def why_kept(run: dict, pr: dict, own: set[str], live: set[str]) -> str | None:
    """Why the run's artifacts stay, or None when it is provably this pull request's."""
    repo, branch, _ = head_of(pr)
    source, named = run.get('head_repository'), run.get('pull_requests')
    created, started = moment(run, 'created_at'), moment(run, 'run_started_at')
    opened, merged = moment(pr, 'created_at'), moment(pr, 'merged_at')
    reason = None
    if run.get('event') != 'pull_request':
        reason = 'not started by a pull request'
    elif not isinstance(source, dict) or source.get('full_name') != repo:
        reason = 'not from this repository'
    elif run.get('head_branch') != branch:
        reason = 'not on this branch'
    elif not text(run.get('head_sha')) or run['head_sha'] not in own:
        reason = "not at this pull request's commits"
    elif run['head_sha'] in live:
        reason = "at another open pull request's head"
    elif run.get('status') != 'completed':
        reason = 'not finished'
    elif created is None or started is None or not opened <= created <= started <= merged:
        reason = 'not started while this pull request was open'
    # GitHub empties this list once the pull request closes, so it can only contradict.
    elif named is not None and (
        not isinstance(named, list)
        or any(number_in('number')(p) != pr['number'] for p in named if isinstance(p, dict))
        or not all(isinstance(p, dict) for p in named)
    ):
        reason = 'naming another pull request'
    return reason


def why_artifact_kept(artifact: dict, run: dict, keep_sdk: Callable[[dict], bool]) -> str | None:
    """Why the artifact stays, or None when it is this run's and nothing still reads it."""
    name, source = artifact.get('name'), artifact.get('workflow_run')
    reason = None
    if artifact.get('expired') is True:
        reason = 'already expired'
    elif artifact.get('expired') is not False or not text(name):
        reason = 'not readable'
    elif (
        not isinstance(source, dict)
        or not whole_number(source.get('id'))
        or (source['id'], source.get('head_sha')) != (run['id'], run['head_sha'])
    ):
        reason = "not shown to be the run's"
    elif KEEP.match(name):
        reason = 'release inputs'
    elif SDK.match(name) and keep_sdk(run):
        reason = 'a crysta SDK still needed'
    return reason


def own_artifacts(
    fetch: Fetch, repo: str, run: dict, keep_sdk: Callable[[dict], bool], kept: Counter
) -> list[dict]:
    """Return the run's artifacts that may be deleted, counting the others in ``kept``."""
    doomed = []
    for artifact in listing(
        fetch,
        f'repos/{repo}/actions/runs/{run["id"]}/artifacts?per_page=100',
        'artifacts',
        number_in('id'),
    ):
        reason = why_artifact_kept(artifact, run, keep_sdk)
        if reason is None:
            doomed.append(artifact)
        else:
            kept[f'artifacts {reason}'] += 1
    return doomed


def select(fetch: Fetch, repo: str, number: int, keep_sdk: Callable[[dict], bool]) -> list[dict]:
    """The artifacts the closed pull request ``number`` leaves that may be deleted."""
    pr = merged_pull(fetch, repo, number)
    if pr is None:
        return []
    head = head_of(pr)
    branch = head[1]
    own = own_commits(fetch, repo, number, pr.get('commits'))
    if head[2] not in own:
        raise RefusedError(f'#{number} does not list its own head commit')
    others = open_heads(fetch, repo, number)
    if any(other[:2] == (repo, branch) for other in others):
        print(f'branch artifacts: another open pull request uses {branch}: nothing deleted')
        return []
    if not only_user(fetch, repo, number, head):
        return []
    live = {sha for _, _, sha in others}

    runs = listing(
        fetch,
        f'repos/{repo}/actions/runs?branch={urllib.parse.quote(branch, safe="")}&per_page=100',
        'workflow_runs',
        number_in('id'),
    )
    if len(runs) >= RUNS_CAP:
        raise RefusedError(f'{branch} has {len(runs)} runs; GitHub lists only {RUNS_CAP}')
    doomed, mine, kept = [], 0, Counter()
    for run in runs:
        reason = why_kept(run, pr, own, live)
        if reason is not None:
            kept[f'runs {reason}'] += 1
            continue
        mine += 1
        doomed += own_artifacts(fetch, repo, run, keep_sdk, kept)
    for reason, count in sorted(kept.items()):
        print(f'branch artifacts: kept {count} {reason}')
    print(
        f'branch artifacts: {branch}: {len(runs)} run(s) listed, {mine} of this pull '
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
