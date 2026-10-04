#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-3-Clause
"""The engine's time inside edi against crysta's CLI, as the engine-time issue measured it.

The project is the committed five-bank NCAF project
(``docs/user/cli/pd-neut-tof_ncaf-wish-5bank_start-5``) with every fitted parameter shifted by
three sigma: ``tools/probes/i0018/perturbed.diff`` applied to a copy of it. Each repetition runs
crysta's CLI and then ``python -m edi fit`` on that one project with ``--dry``, and reads the
engine's own ``elapsed_ms`` from each. Both runs are the same calculation, so their iteration
counts and reduced chi-squares must agree.

Run: ``python tools/probes/i0018_engine_time.py --crysta <crysta CLI>`` (default: the CLI of the
crysta build this checkout links, ``build/crysta-prefix/bin/crysta``). ``--bound 1.3`` is
acceptance bound (I24): exit 1 when edi's median exceeds it times the CLI's median. It prints
one Markdown table row per repetition, then the two ratios.
"""

from __future__ import annotations

import argparse
import re
import shutil
import statistics
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PROJECT = ROOT / 'docs/user/cli/pd-neut-tof_ncaf-wish-5bank_start-5/project'
PERTURBED = ROOT / 'tools/probes/i0018/perturbed.diff'
FIELDS = ('iterations', 'reduced_chi_square', 'elapsed_ms')


def perturbed_project(parent: Path) -> Path:
    """Return a copy of the committed project with the three-sigma shift applied."""
    shutil.copytree(PROJECT, parent / 'project')
    subprocess.run(['git', 'apply', '-p1', str(PERTURBED)], cwd=parent, check=True)
    return parent / 'project'


def report(command: list[str]) -> dict[str, str]:
    """Run one fit and return its ``key=value`` report fields."""
    run = subprocess.run(command, capture_output=True, text=True, cwd=ROOT, check=False)
    found = dict(re.findall(r'^(\w+)=(\S+)$', run.stdout + run.stderr, re.MULTILINE))
    missing = [field for field in FIELDS if field not in found]
    if run.returncode or missing:
        sys.exit(f'{" ".join(command)} exited {run.returncode}, without {missing}')
    return found


def main() -> int:
    """Measure, print the table and the ratios, and compare the median ratio with the bound."""
    parser = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    parser.add_argument('--crysta', type=Path, default=ROOT / 'build/crysta-prefix/bin/crysta')
    parser.add_argument('--repetitions', type=int, default=3)
    parser.add_argument('--bound', type=float, default=1.3)
    args = parser.parse_args()
    engine: dict[str, list[float]] = {'crysta': [], 'edi': []}
    head = (
        'repetition',
        'crysta CLI `elapsed_ms`',
        'edi `elapsed_ms`',
        'iterations',
        'chi-square',
    )
    sys.stdout.write('| ' + ' | '.join(head) + ' |\n| ' + ' | '.join(['---'] * 5) + ' |\n')
    with tempfile.TemporaryDirectory() as scratch:
        project = str(perturbed_project(Path(scratch)))
        crysta = [str(args.crysta), 'fit', project, '--dry']
        runs = {
            'crysta': [*crysta, '--verbosity', 'compact', '--perf-info'],
            'edi': [sys.executable, '-m', 'edi', 'fit', project, '--dry', '--report', 'machine'],
        }
        for repetition in range(1, args.repetitions + 1):
            got = {name: report(command) for name, command in runs.items()}  # crysta, then edi
            same = [got['crysta'][field] == got['edi'][field] for field in FIELDS[:2]]
            if not all(same):
                sys.exit(f'repetition {repetition}: the two runs are not one calculation: {got}')
            for name, times in engine.items():
                times.append(float(got[name]['elapsed_ms']))
            sys.stdout.write(
                f'| {repetition} | {engine["crysta"][-1]:.1f} | {engine["edi"][-1]:.1f} '
                f'| {got["edi"]["iterations"]} | {got["edi"]["reduced_chi_square"]} |\n'
            )
    medians = {name: statistics.median(times) for name, times in engine.items()}
    ratio = medians['edi'] / medians['crysta']
    worst = max(engine['edi']) / min(engine['crysta'])
    sys.stdout.write(f'| median | {medians["crysta"]:.1f} | {medians["edi"]:.1f} | | |\n\n')
    sys.stdout.write(f'edi median / crysta CLI median = {ratio:.2f} (bound {args.bound})\n')
    sys.stdout.write(f'edi slowest / crysta CLI fastest = {worst:.2f}\n')
    return 0 if ratio <= args.bound else 1


if __name__ == '__main__':
    sys.exit(main())
