#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-3-Clause
"""The repository keeps its tutorial and verification notebooks without outputs.

A run notebook can be hundreds of megabytes, past what GitHub accepts. The site and CI run the
tutorials themselves (`pixi run notebooks-run`), so a run in a working copy is fine, but the
notebook git holds, in the index, must have no outputs and no execution counts.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def problems() -> list[str]:
    listed = subprocess.run(
        ['git', 'ls-files', '-s', '--', '*.ipynb'],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=True,
    ).stdout
    found = []
    for line in listed.splitlines():
        meta, path = line.split('\t', 1)
        blob = meta.split()[1]
        text = subprocess.run(
            ['git', 'cat-file', 'blob', blob], cwd=ROOT, capture_output=True, text=True, check=True
        ).stdout
        try:
            notebook = json.loads(text)
        except json.JSONDecodeError as error:
            found.append(f'{path}: not a readable notebook ({error})')
            continue
        cells = [c for c in notebook.get('cells', []) if c.get('cell_type') == 'code']
        if any(c.get('outputs') for c in cells):
            found.append(f'{path}: has outputs')
        elif any(c.get('execution_count') is not None for c in cells):
            found.append(f'{path}: has execution counts')
    return found


def main() -> int:
    found = problems()
    for problem in found:
        print(problem, file=sys.stderr)
    if found:
        print(
            'commit notebooks without outputs: run `pixi run notebook-strip` first',
            file=sys.stderr,
        )
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
