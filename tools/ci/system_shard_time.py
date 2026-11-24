# SPDX-License-Identifier: BSD-3-Clause
"""Fail a run whose system shards take more than 20 % longer than an earlier run's.

    system_shard_time.py --current RUN.json --main RUN.json --run-id ID --head-sha SHA
    system_shard_time.py --nightly (--repo OWNER/NAME | --history FILE) --run-id ID --head-sha SHA
        [--save FILE] [--fetch-only] [--record FILE]

Each file is a GitHub Actions run with its jobs: the run's fields plus a `jobs` list as the
REST API returns it, and `expected_system_shards`, each platform's part count from the workflow
matrix. The current document must be run ID at this pull request's source head SHA (not its
merge commit), so a stale or foreign record is refused. Every `system · <platform> ·
<part>/<parts>` job is compared with the job of the same name in a main push run whose system
shards passed. Other jobs
are ignored. Evidence that cannot be compared (a missing or unfinished shard, a duplicate, a bad
timestamp, a zero baseline) is refused with exit 2; a shard over the limit exits 1 and names the
shard and main's time.

With --nightly the run is a scheduled one and the baseline is the newest earlier scheduled run of
ci.yml on main that the comparison accepts: every declared shard once and a finished success, and
the same shards as this run. The search reads GitHub's listing newest first, every page, and each
candidate's whole job list; a candidate that does not qualify is skipped with its reason. A fully
read history with no qualifying run prints "no baseline", writes that record (this run's id, head,
created_at and shards, and every candidate with its reason) and judges nothing. Any read that
fails or comes back short, or a listing GitHub caps before the search ends, refuses with exit 2.
--history replays a recorded listing (a JSON file: `runs` by id, `list` pages, `jobs` pages by
run id, `shards` by head SHA) instead of asking GitHub; --save writes what a search read in that
form, and --fetch-only stops after the search, so CI fetches in one step and judges in the next.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
from collections.abc import Callable, Iterator
from datetime import datetime
from fractions import Fraction
from pathlib import Path

import yaml

LIMIT = Fraction(6, 5)
# GitHub returns at most this many runs for a filtered listing.
LISTING_CAP = 1000
PAGE = 100
SHARD = re.compile(r'system · (\S+) · ([1-9]\d*)/([1-9]\d*)')
SHARD_LIKE = re.compile(r'system · .* · .*/.*')


class RefusedError(Exception):
    """The evidence cannot be compared."""


def load(path: Path, what: str) -> dict:
    try:
        run = json.loads(path.read_text(encoding='utf-8'))
    except (OSError, ValueError) as e:
        raise RefusedError(f'cannot read the {what} run {path}: {e}') from e
    if not isinstance(run, dict) or not isinstance(run.get('jobs'), list):
        raise RefusedError(f'the {what} run {path} has no job list')
    return run


def stamp(job: dict, field: str) -> datetime:
    try:
        when = datetime.fromisoformat(str(job[field]))
    except (KeyError, ValueError) as e:
        raise RefusedError(f'{job.get("name")!r} has no valid {field}') from e
    if when.tzinfo is None:
        raise RefusedError(f'{job.get("name")!r} has a {field} without a time zone')
    return when


def shards(run: dict, what: str) -> dict[str, Fraction]:
    """Each system shard's wall time in seconds, by job name."""
    out, parts = {}, {}
    for job in run['jobs']:
        name = str(job.get('name', ''))
        if not SHARD.fullmatch(name):
            if SHARD_LIKE.fullmatch(name):
                raise RefusedError(f'the {what} run has a malformed shard name {name!r}')
            continue
        platform, part, total = SHARD.fullmatch(name).groups()
        parts.setdefault(platform, []).append((int(part), int(total)))
        if name in out:
            raise RefusedError(f'the {what} run has {name!r} twice')
        if job.get('status') != 'completed' or job.get('conclusion') != 'success':
            raise RefusedError(
                f'{what} {name!r} is {job.get("status")}/{job.get("conclusion")}, '
                'not a finished success'
            )
        took = stamp(job, 'completed_at') - stamp(job, 'started_at')
        out[name] = Fraction(took.days * 86400 + took.seconds) + Fraction(took.microseconds, 10**6)
        if out[name] <= 0:
            raise RefusedError(f'{what} {name!r} has no positive wall time')
    declared = run.get('expected_system_shards')
    if (
        not isinstance(declared, dict)
        or not declared
        or not all(
            isinstance(n, int) and not isinstance(n, bool) and n > 0 for n in declared.values()
        )
    ):
        raise RefusedError(f'the {what} run declares no system shards per platform')
    # every declared platform has each part 1..n once, and no other platform has any
    for platform in sorted(set(declared) | set(parts)):
        total = declared.get(platform, 0)
        if sorted(parts.get(platform, [])) != [(i, total) for i in range(1, total + 1)]:
            raise RefusedError(
                f'the {what} run does not have each declared {platform} shard 1..{total} once: '
                f'{sorted(parts.get(platform, []))}'
            )
    return out


def minutes(seconds: Fraction) -> str:
    whole = round(seconds)
    return f'{whole // 60}m{whole % 60:02d}s'


def require_identity(current: dict, run_id: str, head_sha: str) -> None:
    """The current document is this run, at this pull request's source head."""
    if str(current.get('id')) != run_id or current.get('head_sha') != head_sha:
        raise RefusedError(
            f'the current record is run {current.get("id")} at {current.get("head_sha")}, '
            f'not this run {run_id} at the pull request head {head_sha}'
        )


def compare(current: dict, main: dict, event: str = 'push') -> list[str]:
    """The shards over the limit, one line each."""
    if main.get('head_branch') != 'main' or main.get('event') != event:
        raise RefusedError(
            f'the baseline must be a {event} run on main, '
            f'not {main.get("event")} on {main.get("head_branch")}'
        )
    if main.get('status') != 'completed':
        raise RefusedError('the baseline main run has not finished')
    if current.get('expected_system_shards') != main.get('expected_system_shards'):
        raise RefusedError('this run and main declare different system shards')
    now, base = shards(current, 'current'), shards(main, 'main')
    if set(now) != set(base):
        raise RefusedError(
            f'the shards differ from main: only here {sorted(set(now) - set(base))}, '
            f'only on main {sorted(set(base) - set(now))}'
        )
    return [
        f'{name} took {minutes(now[name])}, main took {minutes(base[name])}: '
        f'{float(now[name] / base[name]):.2f}x, over the {float(LIMIT):.1f}x limit'
        for name in sorted(now)
        if now[name] > base[name] * LIMIT
    ]


def when(run: dict, what: str) -> datetime:
    try:
        created = datetime.fromisoformat(str(run['created_at']))
    except (KeyError, ValueError) as e:
        raise RefusedError(f'the {what} has no valid created_at') from e
    if created.tzinfo is None:
        raise RefusedError(f'the {what} has a created_at without a time zone')
    return created


class History:
    """GitHub's records of ci.yml runs, read through `fetch` (a REST path to its JSON)."""

    def __init__(self, fetch: Callable[[str], object], declare: Callable[[str], dict]) -> None:
        self.fetch, self.declare = fetch, declare

    def page(self, path: str, field: str) -> tuple[int, list]:
        data = self.fetch(path)
        total = data.get('total_count') if isinstance(data, dict) else None
        items = data.get(field) if isinstance(data, dict) else None
        if not isinstance(total, int) or isinstance(total, bool) or not isinstance(items, list):
            raise RefusedError(f'{path} is not a listing of {field} with a total_count')
        return total, items

    def run(self, run_id: str) -> dict:
        """One run with its whole job list and its declared shards."""
        run = self.fetch(f'runs/{run_id}')
        if not isinstance(run, dict) or str(run.get('id')) != str(run_id):
            raise RefusedError(f'run {run_id} could not be read')
        jobs, number = [], 1
        while True:
            total, items = self.page(f'runs/{run_id}/jobs?per_page={PAGE}&page={number}', 'jobs')
            jobs += items
            if len(jobs) >= total:
                break
            if not items:
                raise RefusedError(f'run {run_id} lists {total} jobs, only {len(jobs)} were read')
            number += 1
        if len(jobs) != total:
            raise RefusedError(f'run {run_id} lists {total} jobs, {len(jobs)} were read')
        return run | {
            'jobs': jobs,
            'expected_system_shards': self.declare(str(run.get('head_sha'))),
        }

    def candidates(self) -> Iterator[dict]:
        """Scheduled ci.yml runs on main, newest first, every one GitHub lists."""
        seen, number = 0, 1
        while True:
            query = (
                f'workflows/ci.yml/runs?branch=main&event=schedule&per_page={PAGE}&page={number}'
            )
            total, items = self.page(query, 'workflow_runs')
            for run in items:
                seen += 1
                yield run
            if seen >= total:
                return
            if not items:
                raise RefusedError(f'the listing has {total} runs, only {seen} were read')
            if seen >= LISTING_CAP:
                raise RefusedError(f'GitHub caps the listing at {LISTING_CAP} of its {total} runs')
            number += 1


def unlike(candidate: dict, current: dict, now: dict) -> str | None:
    """Why the comparison would refuse this candidate, or None if it would accept it."""
    if candidate.get('expected_system_shards') != current.get('expected_system_shards'):
        return 'it declares different system shards'
    try:
        names = set(shards(candidate, f'run {candidate.get("id")}'))
    except RefusedError as e:
        return str(e)
    return None if names == set(now) else 'its shards differ from this run'


def baseline(current: dict, history: History) -> tuple[dict | None, list[dict]]:
    """The newest earlier scheduled run the comparison accepts, and every run skipped before it."""
    now, created = shards(current, 'current'), when(current, 'current run')
    skipped = []
    for listed in history.candidates():
        run_id, reason = listed.get('id'), None
        if str(run_id) == str(current.get('id')):
            continue
        if listed.get('event') != 'schedule' or listed.get('head_branch') != 'main':
            reason = f'{listed.get("event")} on {listed.get("head_branch")}'
        elif str(listed.get('path', '')).split('@')[0] != '.github/workflows/ci.yml':
            reason = f'a run of {listed.get("path")}'
        elif when(listed, f'run {run_id}') >= created:
            reason = 'not earlier than this run'
        elif listed.get('status') != 'completed':
            reason = f'{listed.get("status")}, not finished'
        else:
            candidate = history.run(str(run_id))
            reason = unlike(candidate, current, now)
            if reason is None:
                return candidate, skipped
        skipped.append({'id': run_id, 'created_at': listed.get('created_at'), 'skipped': reason})
    return None, skipped


def gh_fetch(repo: str) -> Callable[[str], object]:
    def fetch(path: str) -> object:
        done = subprocess.run(
            ['gh', 'api', f'repos/{repo}/actions/{path}'],
            capture_output=True,
            text=True,
            check=False,
        )
        if done.returncode:
            raise RefusedError(f'reading {path} failed: {done.stderr.strip()}')
        try:
            return json.loads(done.stdout)
        except ValueError as e:
            raise RefusedError(f'{path} did not return JSON: {e}') from e

    return fetch


def git_declare(sha: str) -> dict:
    """Each platform's system part count, from the matrix of the workflow at that commit."""
    for command in (
        ['git', 'fetch', '-q', '--depth=1', 'origin', sha],
        ['git', 'show', f'{sha}:.github/workflows/ci.yml'],
    ):
        done = subprocess.run(command, capture_output=True, text=True, check=False)
        if done.returncode:
            raise RefusedError(f'{" ".join(command[:2])} at {sha} failed: {done.stderr.strip()}')
    try:
        rows = yaml.safe_load(done.stdout)['jobs']['system']['strategy']['matrix']['include']
        counts: dict = {}
        for row in rows:
            counts[row['platform']] = counts.get(row['platform'], 0) + 1
    except (KeyError, TypeError, ValueError) as e:
        raise RefusedError(f'the workflow at {sha} declares no system matrix: {e}') from e
    return counts


def replay(path: Path) -> History:
    """A recorded history: `runs` by id, `list` pages, `jobs` pages by run id, `shards` by head."""
    try:
        data = json.loads(path.read_text(encoding='utf-8'))
    except (OSError, ValueError) as e:
        raise RefusedError(f'cannot read the history {path}: {e}') from e

    def fetch(request: str) -> object:
        where, _, query = request.partition('?')
        number = int(dict(p.split('=') for p in query.split('&')).get('page', 1)) if query else 1
        try:
            if where == 'workflows/ci.yml/runs':
                return data['list'][number - 1]
            if where.endswith('/jobs'):
                return data['jobs'][where.split('/')[1]][number - 1]
            return data['runs'][where.split('/')[1]]
        except (KeyError, IndexError, TypeError) as e:
            raise RefusedError(f'reading {request} failed: not in the history') from e

    def declare(sha: str) -> dict:
        try:
            return data['shards'][sha]
        except (KeyError, TypeError) as e:
            raise RefusedError(f'the history declares no shards at {sha}') from e

    return History(fetch, declare)


def recorded(history: History, saved: dict) -> History:
    """The same history, keeping each answer in the --history form."""

    def fetch(request: str) -> object:
        data = history.fetch(request)
        where = request.partition('?')[0]
        if where == 'workflows/ci.yml/runs':
            saved['list'].append(data)
        elif where.endswith('/jobs'):
            saved['jobs'].setdefault(where.split('/')[1], []).append(data)
        else:
            saved['runs'][where.split('/')[1]] = data
        return data

    def declare(sha: str) -> dict:
        saved['shards'][sha] = history.declare(sha)
        return saved['shards'][sha]

    return History(fetch, declare)


def judge(args: argparse.Namespace) -> list[str] | None:
    """The shards over the limit against the last nightly, or None when no nightly qualifies."""
    history = replay(args.history) if args.history else History(gh_fetch(args.repo), git_declare)
    saved: dict = {'runs': {}, 'list': [], 'jobs': {}, 'shards': {}}
    if args.save:
        history = recorded(history, saved)
    current = history.run(args.run_id)
    require_identity(current, args.run_id, args.head_sha)
    base, skipped = baseline(current, history)
    if args.save:
        args.save.write_text(json.dumps(saved, indent=1) + '\n', encoding='utf-8')
    if args.fetch_only:
        print(f'system shard time: read {len(saved["runs"])} runs, {len(skipped)} skipped')
        return []
    for seen in skipped:
        print(f'system shard time: skipped run {seen["id"]}: {seen["skipped"]}')
    if base is not None:
        print(f'system shard time: baseline is run {base.get("id")} at {base.get("head_sha")}')
        return compare(current, base, event='schedule')
    if args.record:
        record = {
            'baseline': None,
            'run': current.get('id'),
            'head_sha': current.get('head_sha'),
            'created_at': current.get('created_at'),
            'shards': sorted(shards(current, 'current')),
            'candidates': skipped,
        }
        args.record.write_text(json.dumps(record, indent=2) + '\n', encoding='utf-8')
    return None


def nightly(args: argparse.Namespace) -> int:
    try:
        over = judge(args)
    except RefusedError as e:
        print(f'system shard time: cannot compare with an earlier nightly: {e}')
        return 2
    if args.fetch_only:
        return 0
    if over is None:
        print('system shard time: no baseline, no earlier nightly qualifies; nothing judged')
        return 0
    for line in over:
        print(f'system shard time: {line}')
    if over:
        print('system shard time: FAIL, the system tests are slower than the last nightly allows')
        return 1
    print('system shard time: every system shard is within 1.2x of the last nightly')
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split('\n\n')[0])
    parser.add_argument('--nightly', action='store_true')
    parser.add_argument('--current', type=Path)
    parser.add_argument('--main', type=Path)
    parser.add_argument('--repo')
    parser.add_argument('--history', type=Path)
    parser.add_argument('--record', type=Path)
    parser.add_argument('--save', type=Path)
    parser.add_argument('--fetch-only', action='store_true')
    parser.add_argument('--run-id', required=True)
    parser.add_argument('--head-sha', required=True)
    args = parser.parse_args(argv)
    if args.nightly:
        if bool(args.repo) == bool(args.history) or args.current or args.main:
            parser.error(
                '--nightly takes exactly one of --repo and --history, and no --current/--main'
            )
        return nightly(args)
    if not args.current or not args.main:
        parser.error('--current and --main are required without --nightly')
    try:
        current = load(args.current, 'current')
        require_identity(current, args.run_id, args.head_sha)
        over = compare(current, load(args.main, 'main'))
    except RefusedError as e:
        print(f'system shard time: cannot compare with main: {e}')
        return 2
    for line in over:
        print(f'system shard time: {line}')
    if over:
        print('system shard time: FAIL, the system tests are slower than main allows')
        return 1
    print('system shard time: every system shard is within 1.2x of main')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
