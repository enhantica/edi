# SPDX-License-Identifier: BSD-3-Clause
"""Fail a pull request whose system shards run more than 20 % longer than main's.

    system_shard_time.py --current RUN.json --main RUN.json --run-id ID --head-sha SHA

Each file is a GitHub Actions run with its jobs: the run's fields plus a `jobs` list as the
REST API returns it, and `expected_system_shards`, each platform's part count from the workflow
matrix. The current document must be run ID at this pull request's source head SHA (not its
merge commit), so a stale or foreign record is refused. Every `system · <platform> ·
<part>/<parts>` job is compared with the job of the same name in a main push run whose system
shards passed. Other jobs
are ignored. Evidence that cannot be compared (a missing or unfinished shard, a duplicate, a bad
timestamp, a zero baseline) is refused with exit 2; a shard over the limit exits 1 and names the
shard and main's time.
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


def compare(current: dict, main: dict) -> list[str]:
    """The shards over the limit, one line each."""
    if main.get('head_branch') != 'main' or main.get('event') != 'push':
        raise RefusedError(
            'the baseline must be a push run on main, '
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


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split('\n\n')[0])
    parser.add_argument('--current', type=Path, required=True)
    parser.add_argument('--main', type=Path, required=True)
    parser.add_argument('--run-id', required=True)
    parser.add_argument('--head-sha', required=True)
    args = parser.parse_args(argv)
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
