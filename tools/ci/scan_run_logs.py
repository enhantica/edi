# SPDX-License-Identifier: BSD-3-Clause
"""List the CI runs whose logs quote a line of crysta's source; nothing is shown or changed.

    python3 tools/ci/scan_run_logs.py --repo OWNER/NAME --crysta CHECKOUT [--since DATE] [RUN...]

Each attempt of each run is compared with the crysta commit its own edi commit pins, read from
CHECKOUT, a clone with the whole history, without what that edi commit itself published; `gh` must
be signed in. One line a log file with hits: the run, the attempt, the commit, the file and how
many lines. An attempt that cannot be judged is listed with the reason (its logs are gone, its edi
commit has no pin or is gone, the clone lacks the pin) and makes the exit status 1.
"""

from __future__ import annotations

import argparse
import base64
import io
import json
import os
import re
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path

import crysta_fetch
import source_lists

PIN = re.compile(rb'^CRYSTA_COMMIT = "([0-9a-f]{40})"', flags=re.MULTILINE)


class UnjudgedError(Exception):
    """A run the scanner has no reference or no logs for."""


def gh(*args: str) -> bytes:
    """What `gh api` answers."""
    run = subprocess.run(['gh', 'api', *args], capture_output=True, check=False)
    if run.returncode:
        status = re.search(rb'HTTP (\d{3})', run.stderr)
        raise UnjudgedError(f'HTTP {status[1].decode()}' if status else 'no answer')
    return run.stdout


class Scanner:
    """Runs against the source each one built."""

    def __init__(self, repo: str, crysta: Path, scratch: Path) -> None:
        self.repo, self.crysta, self.scratch = repo, crysta, scratch
        self.pins: dict[str, str] = {}
        self.source: tuple[str, source_lists.Source] | None = None
        self.edi = scratch / 'edi'
        self.edi.mkdir()
        crysta_fetch.git(self.edi, 'init', '-q')

    def pin(self, commit: str) -> str:
        """The crysta commit an edi commit pins."""
        if commit not in self.pins:
            answer = json.loads(gh(f'repos/{self.repo}/contents/pixi.toml?ref={commit}'))
            found = PIN.search(base64.b64decode(answer['content']))
            if not found:
                raise UnjudgedError('its edi commit has no pin')
            self.pins[commit] = found[1].decode()
        return self.pins[commit]

    def lists(self, commit: str) -> source_lists.Source:
        """The lists of the crysta commit an edi commit pins, as that commit published edi."""
        if self.source is None or self.source[0] != commit:
            pin, folder = self.pin(commit), self.scratch / commit
            folder.mkdir(exist_ok=True)
            address = f'{crysta_fetch.SERVER}/{self.repo}'
            try:
                crysta_fetch.git(self.edi, 'fetch', '-q', '--depth', '1', address, commit)
                made = crysta_fetch.lists(self.crysta, {pin}, [(self.edi, commit)])
            except crysta_fetch.RefusedError as error:
                raise UnjudgedError(f'{commit[:12]} or its {pin[:12]} cannot be read') from error
            os.environ.update(crysta_fetch.write_lists(made, folder))
            self.source = commit, source_lists.Source()
        return self.source[1]

    def hits(self, run: str, attempt: int) -> list[str]:
        """One line for each log file of an attempt that quotes a source line."""
        where = f'repos/{self.repo}/actions/runs/{run}/attempts/{attempt}'
        commit = json.loads(gh(where))['head_sha']
        source, pin = self.lists(commit), self.pin(commit)
        found = []
        with zipfile.ZipFile(io.BytesIO(gh(f'{where}/logs'))) as logs:
            for entry in logs.infolist():
                lines = logs.read(entry).splitlines()
                if count := sum(source.quoted_in_line(line) for line in lines):
                    found.append(f'{run}\t{attempt}\t{pin[:12]}\t{entry.filename}\t{count}')
        return found

    def attempts(self, run: str) -> int:
        """How often a run was attempted."""
        return json.loads(gh(f'repos/{self.repo}/actions/runs/{run}'))['run_attempt']


def runs(repo: str, since: str | None) -> list[str]:
    """Every run's id, newest first."""
    query = f'repos/{repo}/actions/runs?per_page=100' + (f'&created=>={since}' if since else '')
    return gh('--paginate', query, '--jq', '.workflow_runs[].id').decode().split()


def attempts(scanner: Scanner, run: str) -> range:
    """A run's attempts; one whose record is gone is one that cannot be judged."""
    try:
        return range(1, scanner.attempts(run) + 1)
    except UnjudgedError:
        return range(1, 2)


def main() -> int:
    """Scan the named runs, or all of them."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--repo', required=True)
    parser.add_argument('--crysta', required=True, type=Path)
    parser.add_argument('--since')
    parser.add_argument('runs', nargs='*')
    args = parser.parse_args()
    judged, unjudged = 0, 0
    with tempfile.TemporaryDirectory() as scratch:
        scanner = Scanner(args.repo, args.crysta, Path(scratch))
        for run in args.runs or runs(args.repo, args.since):
            for attempt in attempts(scanner, run):
                try:
                    for line in scanner.hits(run, attempt):
                        print(line)
                    judged += 1
                except (UnjudgedError, zipfile.BadZipFile, ValueError, KeyError) as error:
                    unjudged += 1
                    known = isinstance(error, UnjudgedError)
                    print(
                        f'{run}\t{attempt}\tnot judged\t{error if known else type(error).__name__}'
                    )
    print(f'{judged} attempts judged, {unjudged} not judged', file=sys.stderr)
    return 1 if unjudged else 0


if __name__ == '__main__':
    raise SystemExit(main())
