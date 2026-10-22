#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-3-Clause
"""Fit one example in diffraction-lib and write its curves for the fit-quality page.

Run it with a Python that has diffraction-lib installed, never from a test:

    python tools/comparison/run_diffraction_lib.py <case> --commit SHA [--incompatible REASON]

The case's committed project is copied into the schema diffraction-lib reads (schema 1, its
profile names, positional numbers, its Levenberg-Marquardt minimizer), fitted from the committed
start and written to ``knowledge/comparison/<case>/diffraction-lib/``: one ``<bank>.csv`` per
experiment and ``reference.json``. A scan is fitted on its template file only, as FullProf's
reference is. ``--incompatible`` records why the model cannot be expressed and fits nothing.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import json
import re
import shutil
import sys
import tempfile
import time
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
CLI_DIR = ROOT / 'docs' / 'user' / 'cli'
OUT_DIR = ROOT / 'knowledge' / 'comparison'
# edi's profile names and the names diffraction-lib gives the same profiles.
PEAK = {
    'cwl-tch-pseudo-voigt': 'cwl-pseudo-voigt',
    'cwl-tch-pseudo-voigt-fcj': 'cwl-thompson-cox-hastings',
}
# diffraction-lib computes TCH with FCJ asymmetry in its crysfml calculator only.
CALCULATOR = {'cwl-thompson-cox-hastings': 'crysfml'}
# diffraction-lib reads no exponent, so such numbers are written out positionally.
EXPONENT = re.compile(r'(?<![\w.])[-+]?\d+(?:\.\d*)?[eE][-+]?\d+(?![\w.])')
MINIMIZER = 'lmfit (leastsq)'


def convert(text: str, *, analysis: bool) -> str:
    text = re.sub(r'(?m)^_edi\.schema_version 3$', '_edi.schema_version 1', text)
    text = re.sub(r'(?m)^(_peak\.type) (\S+)$', lambda m: f'{m[1]} {PEAK.get(m[2], m[2])}', text)
    text = EXPONENT.sub(
        lambda m: np.format_float_positional(float(m[0]), unique=True, trim='-'), text
    )
    for peak, calculator in CALCULATOR.items():
        if f'_peak.type {peak}\n' in text and '_calculator.type' not in text:
            text = text.replace(
                f'_peak.type {peak}\n', f'_peak.type {peak}\n\n_calculator.type {calculator}\n', 1
            )
    # diffraction-lib ids are letters, digits and underscores; edi also allows a dot.
    text = re.sub(
        r'(?m)(^loop_\n_background\.id\n(?:_background\.\S+\n)*)((?:\S+ .*\n)+)',
        lambda m: m[1] + re.sub(r'(?m)^(\S+)', lambda r: r[1].replace('.', '_'), m[2]),
        text,
    )
    if analysis:
        # The scan's template file is fitted alone, so the scan settings go.
        text = re.sub(r'(?m)^_(minimizer|sequential_fit)\.\S+ .*\n', '', text)
        text = re.sub(r'(?m)^_fitting_mode\.type sequential$', '_fitting_mode.type single', text)
        text = text.replace(
            '_fitting_mode.type', f'_minimizer.type "{MINIMIZER}"\n\n_fitting_mode.type', 1
        )
    return text


def copy_project(case: str, into: Path) -> Path:
    project = into / case
    shutil.copytree(CLI_DIR / case / 'project', project)
    for path in sorted(project.rglob('*.edi')):
        text = path.read_text(encoding='utf-8')
        path.write_text(convert(text, analysis=path.parent.name == 'analysis'), encoding='utf-8')
    return project


def write_curves(experiment, path: Path) -> None:
    data = experiment.data
    status = np.asarray(data.calc_status, dtype=str)
    included = status != 'excl'
    columns = {
        'x': np.asarray(data.unfiltered_x, dtype=float),
        'observed': np.full(status.size, np.nan),
        'sigma': np.full(status.size, np.nan),
        'calculated': np.full(status.size, np.nan),
        'background': np.full(status.size, np.nan),
    }
    # diffraction-lib returns its arrays on the included points only.
    for name, source in (
        ('observed', 'intensity_meas'),
        ('sigma', 'intensity_meas_su'),
        ('calculated', 'intensity_calc'),
        ('background', 'intensity_bkg'),
    ):
        columns[name][included] = np.asarray(getattr(data, source), dtype=float)
    with path.open('w', encoding='utf-8') as handle:
        handle.write(','.join([*columns, 'included']) + '\n')
        for row in range(status.size):
            values = [f'{columns[name][row]:.10g}' for name in columns]
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


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split('\n\n', 1)[0])
    parser.add_argument('case')
    parser.add_argument('--commit', required=True, help='the diffraction-lib commit installed')
    parser.add_argument('--incompatible', metavar='REASON')
    args = parser.parse_args(argv)
    out = OUT_DIR / args.case / 'diffraction-lib'
    shutil.rmtree(out, ignore_errors=True)
    out.mkdir(parents=True)
    record = {
        'program': 'diffraction-lib',
        'version': importlib.metadata.version('easydiffraction'),
        'commit': args.commit,
        'model_compatible': args.incompatible is None,
    }
    if args.incompatible:
        record['reason'] = args.incompatible
    else:
        import easydiffraction as ed  # noqa: PLC0415

        with tempfile.TemporaryDirectory() as scratch:
            project = ed.Project.load(str(copy_project(args.case, Path(scratch))))
            n_free = sum(
                1 for parameter in project.parameters if getattr(parameter, 'free', False)
            )
            started = time.perf_counter()
            project.analysis.fit()
            elapsed = time.perf_counter() - started
            result = project.analysis.fit_result
            for experiment in project.experiments:
                write_curves(experiment, out / f'{experiment.name}.csv')
            banks = [experiment.name for experiment in project.experiments]
            cell = cells(project)
        record.update(
            minimizer=MINIMIZER,
            n_free=n_free,
            success=bool(result.success.value),
            iterations=int(result.iterations.value),
            fit_seconds=round(elapsed, 1),
            banks=banks,
            cells=cell,
            artifacts_sha256={path.name: digest(path) for path in sorted(out.glob('*.csv'))},
        )
    (out / 'reference.json').write_text(
        json.dumps(record, indent=2, ensure_ascii=False) + '\n', encoding='utf-8'
    )
    print(json.dumps(record))
    return 0


if __name__ == '__main__':
    sys.exit(main())
