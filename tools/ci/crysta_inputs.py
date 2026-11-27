# SPDX-License-Identifier: BSD-3-Clause
"""Decide whether crysta's jobs may run only their marker step (edi ADR-0083).

They may when every path of tools/ci/crysta-inputs.txt has the same Git object id at the head and
at the event's comparison commit: a pull request's base tip, which has to be an ancestor of the
head, or a main push's first parent. The nightly and manual runs always run them, as does any other
event, and so does a run whose comparison commit is not in the checkout.

    python3 tools/ci/crysta_inputs.py --event EVENT --head SHA [--base SHA]
        prints `run=true` or `run=false`, then `compare=<sha>` (empty without one); the reason
        goes to stderr
    python3 tools/ci/crysta_inputs.py --list
        prints the list, a path a line
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
LIST = ROOT / 'tools/ci/crysta-inputs.txt'
COMMIT = re.compile(r'[0-9a-f]{40}')
PLAIN = re.compile(r'[\w.-]+(?:/[\w.-]+)*')


class RefusedError(Exception):
    """The list is not one this script can trust."""


def inputs(path: Path = LIST) -> list[str]:
    """The listed paths: plain, relative, unique and sorted, so two copies compare line by line."""
    lines = path.read_text(encoding='utf-8').splitlines()
    found = [line.strip() for line in lines if line.strip() and not line.startswith('#')]
    for entry in found:
        if not PLAIN.fullmatch(entry) or {'.', '..'} & set(entry.split('/')):
            raise RefusedError(f'{entry!r} is not a plain path of the repository')
    if not found or found != sorted(set(found)):
        raise RefusedError(f'{path.name} is empty, or not sorted and unique')
    return found


def covers(entries: list[str], path: str) -> bool:
    """Whether a repository path is listed, itself or in a listed folder."""
    return any(path == entry or path.startswith(f'{entry}/') for entry in entries)


def git(*args: str, stdin: str | None = None) -> subprocess.CompletedProcess:
    return subprocess.run(
        ['git', '-C', str(ROOT), *args],
        input=stdin,
        capture_output=True,
        text=True,
        check=False,
    )


def known(commit: str) -> bool:
    """Whether the checkout holds this commit."""
    return git('cat-file', '-e', f'{commit}^{{commit}}').returncode == 0


def object_ids(commit: str, entries: list[str]) -> list[str]:
    """Each entry's object id at a commit, or `missing`."""
    asked = ''.join(f'{commit}:{entry}\n' for entry in entries)
    run = git('cat-file', '--batch-check=%(objectname)', stdin=asked)
    found = run.stdout.splitlines()
    if run.returncode or len(found) != len(entries):
        raise RefusedError(f'git cat-file exited {run.returncode}')
    return ['missing' if line.endswith(' missing') else line for line in found]


def comparison(event: str, head: str, base: str) -> tuple[str, str]:
    """The commit this event compares with, or none and why."""
    if event == 'push':
        parent = git('rev-parse', '--verify', '--quiet', f'{head}^1^{{commit}}').stdout.strip()
        if COMMIT.fullmatch(parent):
            return parent, ''
        return '', 'the first parent of the head is not in the checkout'
    if event != 'pull_request':
        return '', f'a {event} run always runs them'
    if not COMMIT.fullmatch(base) or not known(base):
        reason = f'the base {base!r} is not a commit of the checkout'
    elif git('merge-base', '--is-ancestor', base, head).returncode:
        reason = f'the base {base} is not an ancestor of the head'
    else:
        return base, ''
    return '', reason


def decide(event: str, head: str, base: str = '') -> tuple[bool, str, str]:
    """Whether crysta's jobs run, the commit compared with, and why."""
    entries = inputs()
    if not COMMIT.fullmatch(head) or not known(head):
        return True, '', f'the head {head!r} is not a commit of the checkout'
    compare, reason = comparison(event, head, base)
    if not compare:
        return True, '', reason
    changed = [
        entry
        for entry, now, then in zip(
            entries, object_ids(head, entries), object_ids(compare, entries), strict=True
        )
        if now != then
    ]
    if changed:
        return True, compare, f'{len(changed)} crysta input(s) changed, the first {changed[0]}'
    return False, compare, f'none of the {len(entries)} crysta inputs changed since {compare}'


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--list', action='store_true')
    parser.add_argument('--event', default='')
    parser.add_argument('--head', default='')
    parser.add_argument('--base', default='')
    args = parser.parse_args()
    try:
        if args.list:
            print('\n'.join(inputs()))
            return 0
        run, compare, reason = decide(args.event, args.head, args.base)
    except (RefusedError, OSError, UnicodeDecodeError) as refusal:
        print(f'crysta-inputs: REFUSED: {refusal}', file=sys.stderr)
        return 1
    print(f'run={str(run).lower()}')
    print(f'compare={compare}')
    print(f'crysta-inputs: {reason}', file=sys.stderr)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
