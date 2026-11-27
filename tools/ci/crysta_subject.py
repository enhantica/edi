# SPDX-License-Identifier: BSD-3-Clause
"""Print a crysta job's subject line from its own checkout (edi ADR-0083).

    python3 tools/ci/crysta_subject.py --sha SHA [--checkout DIR]

    crysta-ci subject sha=<C> tree=<T> edi=<E> pr=<n> run=<run id>/<attempt>

C is the checkout's HEAD (default $CRYSTA_SRC), which has to be SHA, the commit the job was given;
T its tree; E the edi commit the run is at, a pull request's head or else GITHUB_SHA; n the pull
request's number, empty without one. A job prints it once: a second call in the same job refuses.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from pathlib import Path

COMMIT = re.compile(r'[0-9a-f]{40}')
NUMBER = re.compile(r'[1-9][0-9]*')


class RefusedError(Exception):
    """The line would not name what the job tested."""


def run_of() -> str:
    """The run and attempt, as `<id>/<attempt>`."""
    run, attempt = os.environ.get('GITHUB_RUN_ID', ''), os.environ.get('GITHUB_RUN_ATTEMPT', '')
    if not (NUMBER.fullmatch(run) and NUMBER.fullmatch(attempt)):
        raise RefusedError('GITHUB_RUN_ID and GITHUB_RUN_ATTEMPT name no run')
    return f'{run}/{attempt}'


def edi_of() -> tuple[str, str]:
    """The edi commit the run is at and its pull request's number, empty without one."""
    path = os.environ.get('GITHUB_EVENT_PATH', '')
    event = json.loads(Path(path).read_bytes()) if path else {}
    request = event.get('pull_request') if isinstance(event, dict) else None
    if isinstance(request, dict):
        commit, number = (request.get('head') or {}).get('sha', ''), str(request.get('number', ''))
    else:
        commit, number = os.environ.get('GITHUB_SHA', ''), ''
    if not COMMIT.fullmatch(commit) or (number and not NUMBER.fullmatch(number)):
        raise RefusedError('the event names no edi commit')
    return commit, number


def git(checkout: Path, *args: str) -> str:
    """One line of git's output; a failure names the command, never its output."""
    run = subprocess.run(
        ['git', '-C', str(checkout), *args], capture_output=True, text=True, check=False
    )
    if run.returncode:
        raise RefusedError(f'git {args[0]} exited {run.returncode}')
    return run.stdout.strip()


def subject(sha: str, checkout: Path) -> str:
    """The line, after checking the checkout is the commit asked for."""
    if not COMMIT.fullmatch(sha):
        raise RefusedError(f'{sha!r} is not a full commit id')
    listed = os.environ.get('CRYSTA_LISTED_SHA')
    if listed is not None and listed != sha:
        raise RefusedError(f'the source on the runner is {listed}, not {sha}')
    head = git(checkout, 'rev-parse', '--verify', 'HEAD^{commit}')
    if head != sha:
        raise RefusedError(f'the checkout is {head}, not {sha}')
    tree = git(checkout, 'rev-parse', '--verify', 'HEAD^{tree}')
    edi, number = edi_of()
    return f'crysta-ci subject sha={sha} tree={tree} edi={edi} pr={number} run={run_of()}'


def once(sha: str, checkout: str | None) -> str:
    """The line, the first time this job asks for it."""
    if checkout is None:
        raise RefusedError('no checkout: CRYSTA_SRC is unset')
    line = subject(sha, Path(checkout))
    # The runner's temporary folder lasts one job, so the mark allows one line a job.
    mark = Path(os.environ.get('RUNNER_TEMP', '.')) / 'crysta-subject-printed'
    if mark.exists():
        raise RefusedError('this job has printed its subject line already')
    mark.write_text(line + '\n', encoding='utf-8')
    return line


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--sha', required=True)
    parser.add_argument('--checkout', default=os.environ.get('CRYSTA_SRC'))
    args = parser.parse_args()
    try:
        line = once(args.sha, args.checkout)
    except (RefusedError, OSError, ValueError) as refusal:
        print(f'crysta-subject: REFUSED: {refusal}', file=sys.stderr)
        return 1
    print(line)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
