# SPDX-License-Identifier: BSD-3-Clause
"""List the CI runs whose logs quote a line of crysta's source; nothing is shown or changed.

    python3 tools/ci/scan_run_logs.py --repo enhantica/edi [--since DATE] [RUN...]

Needs the lists crysta_fetch.py writes (CRYSTA_SOURCE_BLOB_LIST, CRYSTA_SOURCE_LINE_LIST) and `gh`
signed in. Prints one line per log file with hits: the run, the file and how many lines. A run
whose logs are gone is counted; one that cannot be read exits 1 after the rest.
"""

from __future__ import annotations

import argparse
import io
import subprocess
import sys
import zipfile

import source_lists


def gh(*args: str) -> bytes | None:
    """What `gh api` answers; None when the server says it is gone."""
    run = subprocess.run(['gh', 'api', *args], capture_output=True, check=False)
    if run.returncode and (b'HTTP 404' in run.stderr or b'HTTP 410' in run.stderr):
        return None
    run.check_returncode()
    return run.stdout


def runs(repo: str, since: str | None) -> list[str]:
    """Every run's id, newest first."""
    query = f'repos/{repo}/actions/runs?per_page=100' + (f'&created=>={since}' if since else '')
    listed = gh('--paginate', query, '--jq', '.workflow_runs[].id') or b''
    return listed.decode().split()


def hits(data: bytes, known: frozenset[str]) -> dict[str, int]:
    """How many source lines each log file of a run quotes."""
    found = {}
    with zipfile.ZipFile(io.BytesIO(data)) as logs:
        for entry in logs.infolist():
            lines = logs.read(entry).splitlines()
            count = sum(not known.isdisjoint(source_lists.readings(line)) for line in lines)
            if count:
                found[entry.filename] = count
    return found


def main() -> int:
    """Scan the named runs, or all of them."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--repo', required=True)
    parser.add_argument('--since')
    parser.add_argument('runs', nargs='*')
    args = parser.parse_args()
    known = source_lists.lines()
    gone = read = 0
    unreadable = []
    for run in args.runs or runs(args.repo, args.since):
        try:
            data = gh(f'repos/{args.repo}/actions/runs/{run}/logs')
            if data is None:
                gone += 1
                continue
            found = hits(data, known)
        except (subprocess.CalledProcessError, zipfile.BadZipFile):
            unreadable.append(run)
            continue
        read += 1
        for name, count in sorted(found.items()):
            print(f'{run}\t{name}\t{count}')
    print(f'{read} runs read, {gone} without logs, {len(unreadable)} unreadable', file=sys.stderr)
    return 1 if unreadable else 0


if __name__ == '__main__':
    raise SystemExit(main())
