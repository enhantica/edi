# SPDX-License-Identifier: BSD-3-Clause
"""Fail a nightly run whose system shards run more than 20 % longer than the previous night's.

    system_shard_time.py --current RUN.json --main RUN.json --run-id ID --head-sha SHA

Each file is a GitHub Actions run with its jobs: the run's fields plus a `jobs` list as the
REST API returns it, and `expected_system_shards`, each platform's part count from the workflow
matrix. The current document must be run ID at its head SHA, so a stale or foreign record is
refused. Every `system · <platform> · <part>/<parts>` job is compared with the job of the same
name in a scheduled run on main that started before this one and passed its system shards.
Other jobs are ignored. Evidence that cannot be compared (a missing or unfinished shard, a
duplicate, a bad timestamp, a zero baseline, a baseline not started first) is refused with
exit 2; a shard over the limit exits 1 and names the shard and main's time.

When the collector found no earlier scheduled run that passed its system shards, the main
document is exactly `{"no_baseline": true, "before": <this run's created_at>}`. It passes only
when the current run is itself a complete, valid record created at that time.
"""

from __future__ import annotations

import argparse
import json
import re
from datetime import datetime
from fractions import Fraction
from pathlib import Path

LIMIT = Fraction(6, 5)
SHARD = re.compile(r'system · (\S+) · ([1-9]\d*)/([1-9]\d*)')
SHARD_LIKE = re.compile(r'system · .* · .*/.*')


class RefusedError(Exception):
    """The evidence cannot be compared."""


def read(path: Path, what: str) -> object:
    try:
        return json.loads(path.read_text(encoding='utf-8'))
    except (OSError, ValueError) as e:
        raise RefusedError(f'cannot read the {what} run {path}: {e}') from e


def require_jobs(run: object, path: Path, what: str) -> dict:
    if not isinstance(run, dict) or not isinstance(run.get('jobs'), list):
        raise RefusedError(f'the {what} run {path} has no job list')
    return run


def load(path: Path, what: str) -> dict:
    return require_jobs(read(path, what), path, what)


def instant(value: object, what: str) -> datetime:
    """A GitHub timestamp with its time zone (a trailing Z is UTC)."""
    text = value if isinstance(value, str) else ''
    try:
        when = datetime.fromisoformat(text[:-1] + '+00:00' if text.endswith('Z') else text)
    except ValueError as e:
        raise RefusedError(f'{what} is no valid time: {value!r}') from e
    if when.tzinfo is None:
        raise RefusedError(f'{what} has no time zone: {value!r}')
    return when


def stamp(job: dict, field: str) -> datetime:
    return instant(job.get(field), f'{job.get("name")!r} {field}')


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
    """The current document is this run, at its head."""
    if str(current.get('id')) != run_id or current.get('head_sha') != head_sha:
        raise RefusedError(
            f'the current record is run {current.get("id")} at {current.get("head_sha")}, '
            f'not this run {run_id} at the head {head_sha}'
        )


def compare(current: dict, main: dict) -> list[str]:
    """The shards over the limit, one line each."""
    if main.get('head_branch') != 'main' or main.get('event') != 'schedule':
        raise RefusedError(
            'the baseline must be a scheduled run on main, '
            f'not {main.get("event")} on {main.get("head_branch")}'
        )
    if main.get('status') != 'completed':
        raise RefusedError('the baseline main run has not finished')
    # The baseline started before this run: an overlapping later run is no baseline.
    started = instant(current.get('created_at'), 'this run created_at')
    base_started = instant(main.get('created_at'), 'the baseline created_at')
    if base_started >= started:
        raise RefusedError(
            f'the baseline run started at {base_started.isoformat()}, '
            f'not before this run at {started.isoformat()}'
        )
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


def no_baseline(current: dict, record: dict) -> str:
    """Check an explicit lack of a baseline; the line to print."""
    if set(record) != {'no_baseline', 'before'} or record['before'] != current.get('created_at'):
        raise RefusedError(
            'the no-baseline record must be exactly '
            '{no_baseline: true, before: <this run created_at>}'
        )
    instant(record['before'], 'the no-baseline before')
    shards(current, 'current')  # this night's own shards are complete and valid
    return f'no scheduled run on main before {record["before"]} passed its system shards'


def evidence(args: argparse.Namespace) -> tuple[dict, object]:
    """Read the current record, checked as this run, and the main document."""
    current = load(args.current, 'current')
    require_identity(current, args.run_id, args.head_sha)
    return current, read(args.main, 'main')


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split('\n\n')[0])
    parser.add_argument('--current', type=Path, required=True)
    parser.add_argument('--main', type=Path, required=True)
    parser.add_argument('--run-id', required=True)
    parser.add_argument('--head-sha', required=True)
    args = parser.parse_args(argv)
    try:
        current, record = evidence(args)
        first = isinstance(record, dict) and record.get('no_baseline') is True
        # The first night: nothing to compare with, said explicitly and checked.
        line = no_baseline(current, record) if first else None
        main_run = None if first else require_jobs(record, args.main, 'main')
    except RefusedError as e:
        print(f'system shard time: cannot compare with main: {e}')
        return 2
    if main_run is None:
        print(f'system shard time: {line}; nothing to compare')
        return 0
    try:
        over = compare(current, main_run)
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
