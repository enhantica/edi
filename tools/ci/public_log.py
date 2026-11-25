# SPDX-License-Identifier: BSD-3-Clause
"""Run a CI step's script and withhold crysta source lines from what it prints.

    python3 tools/ci/public_log.py SCRIPT

The shell of every step that runs after crysta's source is on the runner. Standard output, standard
error and the step summary pass through line by line. Without readable lists the step does not run.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile
import threading
from pathlib import Path

import source_lists

WITHHELD = b'[source line withheld]'
UNAVAILABLE = 97


def bash() -> str:
    """The shell GitHub's own `shell: bash` uses; on Windows Git's, never the Linux subsystem's."""
    if os.name == 'nt' and (git := shutil.which('git')):
        for home in Path(git).resolve().parents:
            if (found := home / 'bin/bash.exe').is_file():
                return str(found)
    return 'bash'


def passed(line: bytes, known: frozenset[str]) -> bytes:
    """``line`` as it may be shown, its ending kept."""
    body = line.rstrip(b'\r\n')
    parts = body.split(b'\r')
    shown = [WITHHELD if source_lists.quotes_source(part, known) else part for part in parts]
    return b'\r'.join(shown) + line[len(body) :]


def forward(source, sink, known: frozenset[str]) -> None:
    """Copy one stream, a line at a time."""
    for line in iter(source.readline, b''):
        sink.write(passed(line, known))
        sink.flush()


def main() -> int:
    """Run the script; its own exit code is the step's."""
    try:
        known = source_lists.lines()
    except source_lists.UnavailableError:
        return UNAVAILABLE
    environment = dict(os.environ)
    with tempfile.TemporaryDirectory() as scratch:
        summary = Path(scratch) / 'summary'
        summary.touch()
        if 'GITHUB_STEP_SUMMARY' in environment:
            environment['GITHUB_STEP_SUMMARY'] = str(summary)
        step = subprocess.Popen(
            [bash(), '--noprofile', '--norc', '-eo', 'pipefail', *sys.argv[1:]],
            env=environment,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        copies = [
            threading.Thread(target=forward, args=(step.stdout, sys.stdout.buffer, known)),
            threading.Thread(target=forward, args=(step.stderr, sys.stderr.buffer, known)),
        ]
        for copy in copies:
            copy.start()
        for copy in copies:
            copy.join()
        status = step.wait()
        if 'GITHUB_STEP_SUMMARY' in os.environ:
            with Path(os.environ['GITHUB_STEP_SUMMARY']).open('ab') as output:
                written = summary.read_bytes().splitlines(keepends=True)
                output.writelines(passed(line, known) for line in written)
    return status if status >= 0 else 128 - status


if __name__ == '__main__':
    raise SystemExit(main())
