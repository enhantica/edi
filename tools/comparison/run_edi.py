#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-3-Clause
"""Fit one example with edi and write its curves for the fit-quality page.

    python tools/comparison/run_edi.py <case>...

Each case's committed project is fitted from its committed start, a scan on its template file
only (FullProf's reference fits that file alone). The result goes to
``knowledge/comparison/<case>/edi/``: one ``<bank>.csv`` per experiment and ``reference.json``
with the crysta SDK build it ran on. It names no edi commit, since a squash merge does not keep
branch commits. An authoring command; no test runs it.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import sys
import tempfile
from pathlib import Path

import edi
import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'tools' / 'checks'))
from cli_projects import fit_template_only  # noqa: E402 - the record check's own template rule

CLI_DIR = ROOT / 'docs' / 'user' / 'cli'
OUT_DIR = ROOT / 'knowledge' / 'comparison'


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
        analysis = (copy / 'analysis' / 'analysis.edi').read_text(encoding='utf-8')
        if re.search(r'(?m)^_fitting_mode\.type sequential$', analysis):
            fit_template_only(copy)
        project = edi.Project.load(copy)
        n_free = len(project.free_parameters)
        result = project.analysis.fit()
        for experiment in project.experiments:
            write_curves(experiment, out / f'{experiment.name}.csv')
        banks = [experiment.name for experiment in project.experiments]
        cell = cells(project)
    record = {
        'program': 'edi',
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
