# SPDX-License-Identifier: BSD-3-Clause
"""List the CI runs whose logs quote a line of crysta's source; nothing is shown or changed.

    python3 tools/ci/scan_run_logs.py --repo OWNER/NAME --crysta CHECKOUT [--since DATE] [RUN...]

Each run is compared with the crysta commit its own edi commit pins, read from CHECKOUT, a clone
with the whole history; `gh` must be signed in. One line a log file with hits: the run, the commit,
the file and how many lines. A run that cannot be judged is listed with the reason (its logs are
gone, its edi commit has no pin, the clone lacks the pin) and makes the exit status 1.
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

ROOT = Path(__file__).resolve().parents[2]
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
        self.sources: dict[str, source_lists.Source] = {}

    def pin(self, commit: str) -> str:
        """The crysta commit an edi commit pins."""
        if commit not in self.pins:
            answer = json.loads(gh(f'repos/{self.repo}/contents/pixi.toml?ref={commit}'))
            found = PIN.search(base64.b64decode(answer['content']))
            if not found:
                raise UnjudgedError('its edi commit has no pin')
            self.pins[commit] = found[1].decode()
        return self.pins[commit]

    def source(self, pin: str) -> source_lists.Source:
        """The lists of one crysta commit."""
        if pin not in self.sources:
            folder = self.scratch / pin
            folder.mkdir()
            try:
                blobs, listed = crysta_fetch.lists(self.crysta, pin, ROOT)
            except crysta_fetch.RefusedError as error:
                raise UnjudgedError(f'the clone lacks {pin[:12]}') from error
            os.environ.update(crysta_fetch.write_lists(blobs, listed, folder))
            self.sources[pin] = source_lists.Source()
        return self.sources[pin]

    def hits(self, run: str) -> list[str]:
        """One line for each log file of a run that quotes a source line."""
        commit = json.loads(gh(f'repos/{self.repo}/actions/runs/{run}'))['head_sha']
        pin = self.pin(commit)
        source = self.source(pin)
        found = []
        with zipfile.ZipFile(io.BytesIO(gh(f'repos/{self.repo}/actions/runs/{run}/logs'))) as logs:
            for entry in logs.infolist():
                lines = logs.read(entry).splitlines()
                if count := sum(source.quoted_in_line(line) for line in lines):
                    found.append(f'{run}\t{pin[:12]}\t{entry.filename}\t{count}')
        return found


def runs(repo: str, since: str | None) -> list[str]:
    """Every run's id, newest first."""
    query = f'repos/{repo}/actions/runs?per_page=100' + (f'&created=>={since}' if since else '')
    return gh('--paginate', query, '--jq', '.workflow_runs[].id').decode().split()


def main() -> int:
    """Scan the named runs, or all of them."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--repo', required=True)
    parser.add_argument('--crysta', required=True, type=Path)
    parser.add_argument('--since')
    parser.add_argument('runs', nargs='*')
    args = parser.parse_args()
    unjudged = {}
    with tempfile.TemporaryDirectory() as scratch:
        scanner = Scanner(args.repo, args.crysta, Path(scratch))
        listed = args.runs or runs(args.repo, args.since)
        for run in listed:
            try:
                for line in scanner.hits(run):
                    print(line)
            except (UnjudgedError, zipfile.BadZipFile, ValueError, KeyError) as error:
                reason = str(error) if isinstance(error, UnjudgedError) else type(error).__name__
                unjudged[run] = reason
                print(f'{run}\tnot judged\t{reason}')
    judged = len(listed) - len(unjudged)
    print(f'{judged} runs judged, {len(unjudged)} not judged', file=sys.stderr)
    return 1 if unjudged else 0


if __name__ == '__main__':
    raise SystemExit(main())
