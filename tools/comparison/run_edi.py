#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-3-Clause
"""Fit one example with edi and write its curves for the fit-quality page.

    python tools/comparison/run_edi.py <case>...

Each case's committed project is fitted from its committed start, a scan on its template file
only (FullProf's reference fits that file alone). The result goes to
``knowledge/comparison/<case>/edi/``: one ``<bank>.csv`` per experiment and ``reference.json``
with the edi commit and the crysta SDK it ran on. An authoring command; no test runs it.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import edi
import numpy as np

ROOT = Path(__file__).resolve().parents[2]
CLI_DIR = ROOT / 'docs' / 'user' / 'cli'
OUT_DIR = ROOT / 'knowledge' / 'comparison'


def template_only(project: Path) -> None:
    """Make a scan copy fit its template file alone: its experiment holds that file's points."""
    analysis = project / 'analysis' / 'analysis.edi'
    text = analysis.read_text(encoding='utf-8')
    text = re.sub(r'(?m)^_sequential_fit\.\S+ .*\n', '', text)
    text = re.sub(r'(?m)^_fitting_mode\.type sequential$', '_fitting_mode.type single', text)
    analysis.write_text(text, encoding='utf-8')


def write_curves(experiment, path: Path) -> None:
    data = experiment.data
    included = np.asarray(data.calc_status) == 'incl'
    columns = [
        np.asarray(data.axis(), dtype=float),
        np.asarray(data.intensity_meas, dtype=float),
        np.asarray(data.intensity_meas_su, dtype=float),
        np.asarray(data.intensity_calc, dtype=float),
        np.asarray(data.intensity_bkg, dtype=float),
    ]
    with path.open('w', encoding='utf-8') as handle:
        handle.write('x,observed,sigma,calculated,background,included\n')
        for row in range(included.size):
            values = [f'{column[row]:.10g}' for column in columns]
            handle.write(','.join([*values, str(int(included[row]))]) + '\n')


def cells(project) -> dict[str, dict[str, list[float | None]]]:
    """Each structure's fitted cell lengths with their uncertainties."""
    return {
        structure.name: {
            axis: [
                float(getattr(structure.cell, f'length_{axis}').value),
                getattr(structure.cell, f'length_{axis}').uncertainty,
            ]
            for axis in 'abc'
        }
        for structure in project.structures
    }


def sdk_tag() -> str:
    match = re.search(r'(?m)^CRYSTA_SDK_TAG = "(\S+)"', (ROOT / 'pixi.toml').read_text('utf-8'))
    return match[1] if match else ''


def run(case: str) -> dict:
    out = OUT_DIR / case / 'edi'
    shutil.rmtree(out, ignore_errors=True)
    out.mkdir(parents=True)
    with tempfile.TemporaryDirectory() as scratch:
        copy = Path(scratch) / 'project'
        shutil.copytree(CLI_DIR / case / 'project', copy)
        template_only(copy)
        project = edi.Project.load(copy)
        n_free = len(project.free_parameters)
        result = project.analysis.fit()
        for experiment in project.experiments:
            write_curves(experiment, out / f'{experiment.name}.csv')
        banks = [experiment.name for experiment in project.experiments]
        cell = cells(project)
    head = subprocess.run(
        ['git', '-C', str(ROOT), 'rev-parse', 'HEAD'], capture_output=True, text=True, check=True
    ).stdout.strip()
    record = {
        'program': 'edi',
        'commit': head,
        'crysta_sdk': sdk_tag(),
        'banks': banks,
        'n_free': n_free,
        'status': result.status.name.lower(),
        'converged': bool(result.converged),
        'iterations': int(result.iterations),
        'rwp': float(result.rwp),
        'reduced_chi_square': float(result.reduced_chi_square),
        'cells': cell,
        'artifacts_sha256': {
            path.name: hashlib.sha256(path.read_bytes()).hexdigest()
            for path in sorted(out.glob('*.csv'))
        },
    }
    (out / 'reference.json').write_text(json.dumps(record, indent=2) + '\n', encoding='utf-8')
    return record


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split('\n\n', 1)[0])
    parser.add_argument('cases', nargs='+')
    args = parser.parse_args(argv)
    for case in args.cases:
        record = run(case)
        print(case, record['status'], record['iterations'], f'{100 * record["rwp"]:.3f} %')
    return 0


if __name__ == '__main__':
    sys.exit(main())
