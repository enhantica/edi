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
the same shards as this run. The current record must be this scheduled ci.yml run on main at the
given head. The search reads GitHub's whole listing first: every page, each run id once, exactly
the total GitHub reports, that total unchanged between pages and under GitHub's listing cap. Every
entry must be a complete record (id, head, branch, event, path, status, conclusion, attempt,
timestamps) that agrees with the listing's own filter, and this run must be among them. The runs
are ordered by their parsed created_at, newest first. Each finished earlier run is read again in
detail, which must repeat its listing entry, and then the whole job list of that attempt: each job
must name the run, the attempt and the head. The run is read once more after its jobs, so a re-run
in between is refused.

A run is skipped, with its reason, only when complete records show that it cannot serve: it is not
earlier, not finished, declares other shards, or lacks a successful shard. A fully read history
with no qualifying run prints "no baseline", writes that record (this run's id, attempt, head,
created_at and shards, and every candidate with its reason) and judges nothing. Anything missing,
mistyped, repeated or contradictory refuses with exit 2, never "no baseline".
--history replays a recorded listing (a JSON file: `runs` by id, `list` pages, `jobs` pages by
run id, `shards` by head SHA) instead of asking GitHub, under the same checks; --save writes what a
search read in that form, and --fetch-only stops after the search, so CI fetches in one step and
judges in the next.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
from collections.abc import Callable
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
SHA = re.compile(r'[0-9a-f]{40}')


class RefusedError(Exception):
    """The evidence cannot be compared."""


class UnfitError(RefusedError):
    """The evidence is complete, and shows a run without a successful copy of every shard."""


def once(pairs: list[tuple[str, object]]) -> dict:
    """A JSON object's members; one named twice has no single value."""
    out = dict(pairs)
    if len(out) != len(pairs):
        raise ValueError('a JSON object names a member twice')
    return out


def parse(text: str) -> object:
    return json.loads(text, object_pairs_hook=once)


def whole_number(value: object) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


def load(path: Path, what: str) -> dict:
    try:
        run = parse(path.read_text(encoding='utf-8'))
    except (OSError, ValueError) as e:
        raise RefusedError(f'cannot read the {what} run {path}: {e}') from e
    if not isinstance(run, dict) or not isinstance(run.get('jobs'), list):
        raise RefusedError(f'the {what} run {path} has no job list')
    return run


def moment(record: dict, field: str, what: str) -> datetime:
    """The record's timestamp, which must name its time zone."""
    value = record.get(field)
    try:
        when = datetime.fromisoformat(value) if isinstance(value, str) else None
    except ValueError:
        when = None
    if when is None:
        raise RefusedError(f'{what} has no valid {field}')
    if when.tzinfo is None:
        raise RefusedError(f'{what} has a {field} without a time zone')
    return when


# The values GitHub documents. A status or conclusion outside them cannot be judged, so it is
# refused instead of being read as "not finished" or "not a success".
STATUSES = {'queued', 'in_progress', 'completed', 'waiting', 'requested', 'pending'}
CONCLUSIONS = {
    'success',
    'failure',
    'neutral',
    'cancelled',
    'skipped',
    'timed_out',
    'action_required',
    'stale',
    'startup_failure',
}


def outcome(record: dict, what: str) -> tuple[str, str | None]:
    """The status and conclusion, which a finished record has and an unfinished one does not."""
    status, conclusion = record.get('status'), record.get('conclusion')
    if not isinstance(status, str) or status not in STATUSES:
        raise RefusedError(f'{what} has no known status: {status!r}')
    if 'conclusion' not in record:
        raise RefusedError(f'{what} has no conclusion field')
    known = isinstance(conclusion, str) and conclusion in CONCLUSIONS
    if not (known if status == 'completed' else conclusion is None):
        raise RefusedError(f'{what} is {status} with conclusion {conclusion!r}')
    return status, conclusion


def declared_shards(declared: object, what: str) -> dict:
    if (
        not isinstance(declared, dict)
        or not declared
        or not all(isinstance(p, str) and p for p in declared)
        or not all(whole_number(n) and n > 0 for n in declared.values())
    ):
        raise RefusedError(f'{what} declares no system shards per platform')
    return declared


def shards(run: dict, what: str) -> dict[str, Fraction]:
    """Each system shard's wall time in seconds, by job name.

    UnfitError says the complete job list lacks a successful shard. A record that cannot be read
    as a job list at all is a plain refusal, whatever else the list shows.
    """
    out: dict[str, Fraction] = {}
    parts: dict[str, list] = {}
    unfit = []
    for job in run['jobs']:
        name = job.get('name') if isinstance(job, dict) else None
        if not isinstance(name, str) or not name:
            raise RefusedError(f'the {what} run has a job without a name')
        shard = SHARD.fullmatch(name)
        if not shard:
            if SHARD_LIKE.fullmatch(name):
                # GitHub keeps the unexpanded name of a matrix job that never started.
                if '${{' not in name or outcome(job, f'{what} {name!r}')[1] not in {
                    'cancelled',
                    'skipped',
                }:
                    raise RefusedError(f'the {what} run has a malformed shard name {name!r}')
                unfit.append(f'{what} {name!r} never started')
            continue
        platform, part, total = shard.groups()
        parts.setdefault(platform, []).append((int(part), int(total)))
        if parts[platform].count((int(part), int(total))) > 1:
            raise RefusedError(f'the {what} run has {name!r} twice')
        status, conclusion = outcome(job, f'{what} {name!r}')
        if conclusion != 'success':
            unfit.append(f'{what} {name!r} is {status}/{conclusion}, not a finished success')
            continue
        took = moment(job, 'completed_at', repr(name)) - moment(job, 'started_at', repr(name))
        out[name] = Fraction(took.days * 86400 + took.seconds) + Fraction(took.microseconds, 10**6)
        if out[name] <= 0:
            raise RefusedError(f'{what} {name!r} has no positive wall time')
    declared = declared_shards(run.get('expected_system_shards'), f'the {what} run')
    # every declared platform has each part 1..n once, and no other platform has any
    for platform in sorted(set(declared) | set(parts)):
        total = declared.get(platform, 0)
        wanted = [(i, total) for i in range(1, total + 1)]
        found = sorted(parts.get(platform, []))
        if not set(found) <= set(wanted):
            raise RefusedError(f'the {what} run has undeclared {platform} shards: {found}')
        if found != wanted:
            unfit.append(
                f'the {what} run does not have each declared {platform} shard 1..{total} once: '
                f'{found}'
            )
    if unfit:
        raise UnfitError(unfit[0])
    return out


def minutes(seconds: Fraction) -> str:
    whole = round(seconds)
    return f'{whole // 60}m{whole % 60:02d}s'


def require_identity(current: dict, run_id: str, head_sha: str) -> None:
    """The current document is this run, at this pull request's source head."""
    if (
        not whole_number(current.get('id'))
        or str(current['id']) != run_id
        or current.get('head_sha') != head_sha
    ):
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
    if outcome(main, 'the baseline main run')[0] != 'completed':
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


WORKFLOW = '.github/workflows/ci.yml'
# What identifies one attempt of a run, and stays as it is while the attempt goes on.
IDENTITY = (
    'id',
    'head_sha',
    'head_branch',
    'event',
    'path',
    'run_attempt',
    'created_at',
    'run_started_at',
)
# What a finished run's every reading must repeat, so the run judged is the run listed.
BOUND = (*IDENTITY, 'status', 'conclusion')


def workflow(run: dict) -> str:
    return run['path'].split('@')[0]


def run_id_of(row: object, what: str) -> int:
    rid = row.get('id') if isinstance(row, dict) else None
    if not whole_number(rid):
        raise RefusedError(f'{what} has an entry without an id: {row!r}')
    return rid


def require_run(run: object, what: str) -> dict:
    """The record, with every field the search decides by present, well typed and consistent."""
    run_id_of(run, what)
    for field in ('head_branch', 'event', 'path'):
        if not isinstance(run.get(field), str) or not run[field]:
            raise RefusedError(f'{what} has no valid {field}')
    if not isinstance(run.get('head_sha'), str) or not SHA.fullmatch(run['head_sha']):
        raise RefusedError(f'{what} has no valid head_sha')
    if not whole_number(run.get('run_attempt')) or run['run_attempt'] < 1:
        raise RefusedError(f'{what} has no valid run_attempt')
    if moment(run, 'run_started_at', what) < moment(run, 'created_at', what):
        raise RefusedError(f'{what} started before it was created')
    outcome(run, what)
    return run


def require_same(before: dict, after: dict, fields: tuple[str, ...], what: str) -> None:
    moved = [f for f in fields if before[f] != after[f]]
    if moved:
        raise RefusedError(f'{what}: {moved}')


def require_scheduled(run: dict, what: str) -> None:
    if run['event'] != 'schedule' or run['head_branch'] != 'main' or workflow(run) != WORKFLOW:
        raise RefusedError(
            f'{what} is a {run["event"]} run of {run["path"]} on {run["head_branch"]}, '
            'not a scheduled ci.yml run on main'
        )


def require_jobs(jobs: list[dict], run: dict) -> None:
    """Every job belongs to this run's attempt and head, and fits the run's own outcome."""
    what = f'run {run["id"]} attempt {run["run_attempt"]}'
    for job in jobs:
        name = f'{what} job {job["id"]}'
        for field, wanted in (
            ('run_id', run['id']),
            ('run_attempt', run['run_attempt']),
            ('head_sha', run['head_sha']),
        ):
            got = job.get(field)
            if type(got) is not type(wanted) or got != wanted:
                raise RefusedError(f'{name} has {field} {got!r}, not {wanted!r}')
        if not isinstance(job.get('name'), str) or not job['name']:
            raise RefusedError(f'{name} has no name')
        if outcome(job, name)[0] != 'completed' and run['status'] == 'completed':
            raise RefusedError(f'{name} is {job["status"]} in a finished run')
    # A run can be cancelled or fail to start before any job exists, but not succeed or fail.
    if not jobs and run['conclusion'] in {'success', 'failure', 'timed_out'}:
        raise RefusedError(f'{what} ended in {run["conclusion"]} without any job')


class History:
    """GitHub's records of ci.yml runs, read through `fetch` (a REST path to its JSON)."""

    def __init__(self, fetch: Callable[[str], object], declare: Callable[[str], dict]) -> None:
        self.fetch, self.declare = fetch, declare

    def page(self, path: str, field: str) -> tuple[int, list]:
        data = self.fetch(path)
        total = data.get('total_count') if isinstance(data, dict) else None
        items = data.get(field) if isinstance(data, dict) else None
        if not whole_number(total) or total < 0 or not isinstance(items, list):
            raise RefusedError(f'{path} is not a listing of {field} with a total_count')
        return total, items

    def listing(self, base: str, field: str, cap: int | None = None) -> list[dict]:
        """Every entry of a paged listing, each id once, exactly as many as its total says.

        The total must not change between pages, and a page may come back short only once the
        total is reached. A total at or over GitHub's cap cannot show the listing is whole, so
        it is refused before it could read as the end of the history.
        """
        rows: list[dict] = []
        ids: set[int] = set()
        total, number, where = None, 1, base.rstrip('?&')
        while True:
            count, items = self.page(f'{base}per_page={PAGE}&page={number}', field)
            if total is None:
                total = count
                if cap is not None and total >= cap:
                    raise RefusedError(f'GitHub caps {where} at {cap}; it reports {total}')
            elif count != total:
                raise RefusedError(f'{where} changed from {total} to {count} {field} while read')
            for item in items:
                rid = run_id_of(item, where)
                if rid in ids:
                    raise RefusedError(f'{where} lists {field} id {rid} twice')
                ids.add(rid)
                rows.append(item)
            if len(rows) == total:
                return rows
            if len(rows) > total or len(items) != PAGE:
                raise RefusedError(f'{where} lists {total} {field}, {len(rows)} were read')
            number += 1

    def detail(self, run_id: str) -> dict:
        run = require_run(self.fetch(f'runs/{run_id}'), f'run {run_id}')
        if str(run['id']) != str(run_id):
            raise RefusedError(f'run {run_id} was read as run {run["id"]}')
        return run

    def run(self, run_id: str, listed: dict | None = None) -> dict:
        """One run with the whole job list of its attempt and its declared shards.

        Given its listing entry, the detail must repeat it. The jobs are those of the attempt just
        read, and the run is read once more after them, so a run that moved between the reads (a
        re-run, another head) is refused rather than judged.
        """
        run = self.detail(run_id)
        fields = IDENTITY if listed is None else BOUND
        if listed is not None:
            require_same(listed, run, fields, f'run {run_id} reads differently from its listing')
        jobs = self.listing(f'runs/{run_id}/attempts/{run["run_attempt"]}/jobs?', 'jobs')
        require_jobs(jobs, run)
        again = self.detail(run_id)
        require_same(run, again, fields, f'run {run_id} changed while its jobs were read')
        declared = declared_shards(self.declare(run['head_sha']), f'run {run_id}')
        return run | {'jobs': jobs, 'expected_system_shards': declared}

    def candidates(self) -> list[dict]:
        """Every scheduled ci.yml run on main GitHub lists, newest first by its created_at.

        Each entry is a complete record that agrees with the filter it was listed under. The order
        comes from the parsed timestamps, not from the listing's order.
        """
        rows = self.listing(
            'workflows/ci.yml/runs?branch=main&event=schedule&', 'workflow_runs', LISTING_CAP
        )
        for row in rows:
            what = f'the listing entry of run {row["id"]}'
            require_scheduled(require_run(row, what), what)
        return sorted(
            rows,
            key=lambda r: (moment(r, 'created_at', f'run {r["id"]}'), r['id']),
            reverse=True,
        )


def require_nightly(current: dict, run_id: str, head_sha: str) -> None:
    """The current record is this scheduled ci.yml run on main, at this head."""
    require_identity(current, run_id, head_sha)
    require_scheduled(current, 'the current record')


def unlike(candidate: dict, current: dict) -> str | None:
    """Why this complete record cannot serve as the baseline, or None if it can."""
    if candidate['expected_system_shards'] != current['expected_system_shards']:
        return 'it declares different system shards'
    try:
        shards(candidate, f'run {candidate["id"]}')
    except UnfitError as e:
        return str(e)
    return None


def baseline(current: dict, history: History) -> tuple[dict | None, list[dict]]:
    """The newest earlier scheduled run the comparison accepts, and every run skipped before it.

    None is returned only after the whole listing was read and every entry was judged. The listing
    must hold this run too: one that does not cannot be the whole history.
    """
    shards(current, 'current')
    created = moment(current, 'created_at', 'the current run')
    skipped = []
    rows = history.candidates()
    mine = [row for row in rows if row['id'] == current['id']]
    if not mine:
        raise RefusedError(f'the listing does not have this run {current["id"]}')
    require_same(mine[0], current, IDENTITY, 'this run reads differently from its listing')
    for listed in rows:
        run_id = listed['id']
        if run_id == current['id']:
            continue
        if moment(listed, 'created_at', f'run {run_id}') >= created:
            reason = 'not earlier than this run'
        elif listed['status'] != 'completed':
            reason = f'{listed["status"]}, not finished'
        else:
            candidate = history.run(str(run_id), listed)
            reason = unlike(candidate, current)
            if reason is None:
                return candidate, skipped
        skipped.append({'id': run_id, 'created_at': listed['created_at'], 'skipped': reason})
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
            return parse(done.stdout)
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
    except (KeyError, TypeError, ValueError, yaml.YAMLError) as e:
        raise RefusedError(f'the workflow at {sha} declares no system matrix: {e}') from e
    return counts


def replayed_page(pages: object, number: int, request: str) -> object:
    """One saved page of a listing that has exactly the pages its total needs."""
    first = pages[0] if isinstance(pages, list) and pages else None
    total = first.get('total_count') if isinstance(first, dict) else None
    if not whole_number(total) or len(pages) != max(1, -(-total // PAGE)):
        raise RefusedError(f'the history does not hold the whole listing {request}')
    if number > len(pages):
        raise RefusedError(f'reading {request} failed: not in the history')
    return pages[number - 1]


def require_saved(data: object, path: Path) -> dict:
    """The saved history, with nothing in it that its own run listing does not name."""
    for name, kind in (('runs', dict), ('list', list), ('jobs', dict), ('shards', dict)):
        if not isinstance(data, dict) or not isinstance(data.get(name), kind):
            raise RefusedError(f'the history {path} has no valid {name}')
    listed, heads = set(), set()
    for page in data['list']:
        rows = page.get('workflow_runs') if isinstance(page, dict) else None
        if not isinstance(rows, list):
            raise RefusedError(f'the history {path} has a page without a list of runs')
        for row in rows:
            listed.add(str(run_id_of(row, f'the history {path}')))
            heads.add(str(row.get('head_sha')))
    for name, known in (('runs', listed), ('jobs', set(data['runs'])), ('shards', heads)):
        extra = sorted(set(data[name]) - known)
        if extra:
            raise RefusedError(f'the history {path} has {name} its listing does not name: {extra}')
    return data


def replay(path: Path) -> History:
    """A recorded history: `runs` by id, `list` pages, `jobs` pages by run id, `shards` by head."""
    try:
        data = parse(path.read_text(encoding='utf-8'))
    except (OSError, ValueError) as e:
        raise RefusedError(f'cannot read the history {path}: {e}') from e
    data = require_saved(data, path)

    def fetch(request: str) -> object:
        where, _, query = request.partition('?')
        number = int(dict(p.split('=') for p in query.split('&')).get('page', 1)) if query else 1
        try:
            if where == 'workflows/ci.yml/runs':
                return replayed_page(data['list'], number, where)
            if where.endswith('/jobs'):
                return replayed_page(data['jobs'][where.split('/')[1]], number, where)
            return data['runs'][where.split('/')[1]]
        except KeyError as e:
            raise RefusedError(f'reading {request} failed: not in the history') from e

    def declare(sha: str) -> dict:
        try:
            return data['shards'][sha]
        except KeyError as e:
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
    require_nightly(current, args.run_id, args.head_sha)
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
            'run': current['id'],
            'run_attempt': current['run_attempt'],
            'head_sha': current['head_sha'],
            'created_at': current['created_at'],
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
