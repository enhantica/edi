#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-3-Clause
"""The standalone `easydiffraction fit` and `python -m edi fit` print the same fit output.

Both render every line through the core's report functions (edi/report.hpp): the header, the
starting row, one row per iteration and the summary of a single fit, and a scan's progress lines
and summary. This check runs both entry points on a single fit and on a short scan, `--dry`, and
compares their standard output with the timings blanked. The executable is build/ci/cli/
easydiffraction unless EDI_CLI_BINARY names another.
"""

from __future__ import annotations

import os
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CASES = ('pd-neut-cwl_lbco-hrpt', 'pd-neut-cwl_cosio-d20_scan-3f')
# The time column of an iteration row, the summary's seconds, and a scan's elapsed time and eta.
TIMINGS = (
    (re.compile(r'^( +\d+ +)[0-9.]+'), r'\1·'),
    (re.compile(r'[0-9.]+ s$'), '· s'),
    (re.compile(r'(elapsed|eta) [0-9hms]+'), r'\1 ·'),
    (re.compile(r'· [0-9hms]+$'), '· ·'),
)


def _blanked(text: str) -> list[str]:
    lines = []
    for raw in text.replace('\r', '\n').splitlines():
        line = raw.rstrip()
        for pattern, blank in TIMINGS:
            line = pattern.sub(blank, line)
        lines.append(line)
    return lines


def _run(command: list[str]) -> str:
    done = subprocess.run(command, capture_output=True, text=True, check=False, timeout=600)
    if done.returncode:
        what = ' '.join(command)
        tail = done.stderr[-400:]
        raise SystemExit(f'cli-stream-parity: {what} exited {done.returncode}: {tail}')
    return done.stdout


def main() -> int:
    name = 'easydiffraction.exe' if os.name == 'nt' else 'easydiffraction'
    default = ROOT / 'build/ci/cli' / name
    binary = Path(os.environ.get('EDI_CLI_BINARY', default))
    if not binary.is_file():
        print(f'cli-stream-parity: no executable at {binary} (core-build)', file=sys.stderr)
        return 1
    failures = []
    for case in CASES:
        project = str(ROOT / 'docs/user/cli' / case / 'project')
        native = _blanked(_run([str(binary), 'fit', project, '--dry']))
        python = _blanked(_run([sys.executable, '-m', 'edi', 'fit', project, '--dry']))
        if native != python:
            failures.append(case)
            print(f'cli-stream-parity: {case} differs', file=sys.stderr)
            for left, right in zip(native, python, strict=False):
                if left != right:
                    print(f'  standalone: {left}\n  python:     {right}', file=sys.stderr)
                    break
            if len(native) != len(python):
                print(f'  {len(native)} lines against {len(python)}', file=sys.stderr)
        elif len(native) < 3:
            failures.append(case)
            print(f'cli-stream-parity: {case} printed {len(native)} lines', file=sys.stderr)
    if failures:
        return 1
    print(f'cli-stream-parity: both entry points print the same fit output for {len(CASES)} cases')
    return 0


if __name__ == '__main__':
    sys.exit(main())
