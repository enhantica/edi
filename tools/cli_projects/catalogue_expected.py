#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-3-Clause
"""Write the example catalogue's ``expected.json`` records (ADR-0048).

    python tools/cli_projects/catalogue_expected.py [case ...]

A fitted example takes its references from FullProf's fit of the same start
(``knowledge/fitting/fullprof/<case>/reference.json``): the number of free parameters, R_wp
within 5 % relative, and the cell lengths and angles, atomic coordinates and isotropic ADPs both
programs refine, each within two of edi's standard uncertainties. One ``python -m edi fit`` of a
copy gives the regression pins: iterations and reduced chi-square. A reference the fit misses
is kept and printed, so the check reports it. A scan is checked on its
template file's row of ``results.csv``, which has no R_wp. A simulation pins the point count and
the checksum ``python -m edi calc`` reports. The run's seconds are printed for ``runtimes.tsv``.
"""

from __future__ import annotations

import argparse
import csv
import json
import re
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
CLI = ROOT / 'docs' / 'user' / 'cli'
FULLPROF = ROOT / 'knowledge' / 'fitting' / 'fullprof'
SHARED = re.compile(
    r'^(?P<structure>[^.]+)\.(?:cell\.(?P<cell>(length|angle)_\w+)'
    r'|atom_site\.(?P<site>[^.]+)\.(?P<attr>fract_[xyz]|adp_iso))$'
)
SIGMA_MULTIPLE = 2.0
RWP_TOLERANCE = 0.05


def machine_run(project: Path, command: str = 'fit') -> tuple[dict[str, str], float]:
    argv = [sys.executable, '-m', 'edi', command, str(project), '--report', 'machine']
    started = time.perf_counter()
    run = subprocess.run(
        [*argv, '--verbosity', 'full'], capture_output=True, text=True, check=True, timeout=900
    )
    seconds = time.perf_counter() - started
    return dict(line.split('=', 1) for line in run.stdout.splitlines() if '=' in line), seconds


def setting(project: Path, name: str) -> str | None:
    for path in sorted(project.rglob('*.edi')):
        match = re.search(rf'(?m)^{re.escape(name)} "?([^"\n]+?)"?$', path.read_text('utf-8'))
        if match:
            return match[1]
    return None


def count(project: Path, folder: str) -> int:
    return len(list((project / folder).glob('*.edi')))


def label(unique: str, structures: int) -> str | None:
    """The label edi's report gives a structure parameter's unique name."""
    match = SHARED.match(unique)
    if not match:
        return None
    prefix = f'{match["structure"]}.' if structures > 1 else ''
    if match['cell']:
        return f'{prefix}cell_{match["cell"]}'
    return f'{prefix}{match["site"]}.{match["attr"]}'


def quantity(value: float, kind: str, tol_abs: float | None, tol_rel: float | None) -> dict:
    return {'value': float(value), 'kind': kind, 'tol_abs': tol_abs, 'tol_rel': tol_rel}


def references(case: str) -> tuple[dict, dict[str, tuple[float, str]]]:
    """FullProf's record and its shared values by edi unique name."""
    record = json.loads((FULLPROF / case / 'reference.json').read_text(encoding='utf-8'))
    values = {}
    for unique, code in record['parameter_codes'].items():
        if SHARED.match(unique) and code:
            values[unique] = record['fullprof_parameters'][str(code)]['value']
    return record, values


def check(case: str, name: str, spec: dict, measured: float, notes: list[str]) -> None:
    """Note a reference the fit misses: it stays in the record, as gate 4 reports it."""
    bound = spec['tol_abs'] if spec['tol_abs'] is not None else spec['tol_rel'] * spec['value']
    if not abs(measured - spec['value']) <= bound:
        notes.append(
            f'{case}: {name} edi {measured:.7g}, FullProf {spec["value"]:.7g} (bound {bound:.2g})'
        )


def template_row(case: str, project: Path, template: str, shared: dict, notes: list[str]) -> dict:
    """A scan's references and pins on its template file's row of ``results.csv``."""
    with (project / 'analysis' / 'results.csv').open(encoding='utf-8', newline='') as handle:
        (row,) = [row for row in csv.DictReader(handle) if Path(row['file_path']).name == template]
    quantities = {}
    for unique, value in shared.items():
        key = f'results[{template}].{unique}'
        su = float(row[f'{unique}.uncertainty'])
        quantities[key] = quantity(value, 'reference', SIGMA_MULTIPLE * su, None)
        check(case, key, quantities[key], float(row[unique]), notes)
    prefix = f'results[{template}].fit_result'
    chi = float(row['fit_result.reduced_chi_square'])
    quantities[f'{prefix}.reduced_chi_square'] = quantity(chi, 'regression-pin', None, 1e-5)
    iterations = float(row['fit_result.iterations'])
    quantities[f'{prefix}.iterations'] = quantity(iterations, 'regression-pin', 0.0, None)
    return quantities


def fitted(case: str, project: Path, notes: list[str]) -> tuple[dict, float]:
    record, shared = references(case)
    machine, seconds = machine_run(project)
    quantities = {'n_free': quantity(record['n_free'], 'reference', 0.0, None)}
    check(case, 'n_free', quantities['n_free'], float(machine['n_free']), notes)
    template = setting(project, '_sequential_fit.template_file')
    if template:
        quantities.update(template_row(case, project, template, shared, notes))
        return quantities, seconds
    structures = count(project, 'structures')
    quantities['rwp'] = quantity(record['r_wp'], 'reference', None, RWP_TOLERANCE)
    check(case, 'rwp', quantities['rwp'], float(machine['rwp']), notes)
    for unique, value in shared.items():
        name = f'param.{label(unique, structures)}'
        su = float(machine.get(f'{name}.uncertainty', 'nan'))
        if not su > 0:
            raise SystemExit(f'{case}: {unique} has no edi uncertainty as {name}')
        spec = quantity(value, 'reference', SIGMA_MULTIPLE * su, None)
        quantities[f'{name}.value'] = spec
        check(case, f'{name}.value', spec, float(machine[f'{name}.value']), notes)
    quantities['iterations'] = quantity(machine['iterations'], 'regression-pin', 0.0, None)
    quantities['reduced_chi_square'] = quantity(
        machine['reduced_chi_square'], 'regression-pin', 1e-6, None
    )
    return quantities, seconds


def write(case: str, notes: list[str]) -> float:
    home = CLI / case
    with tempfile.TemporaryDirectory(prefix=f'catalogue-{case}-') as scratch:
        project = Path(scratch) / 'project'
        shutil.copytree(home / 'project', project)
        if setting(project, '_metadata.purpose') == 'simulation':
            machine, seconds = machine_run(project, 'calc')
            document = {
                'schema': 1,
                'source': {
                    'engine': 'edi (regression pins; the FullProf agreement is a test of its own)',
                    'artifact': 'machine record (python -m edi calc --report machine)',
                    'provenance': 'PROVENANCE.md',
                },
                'calc': {
                    'quantities': {
                        'n_points': quantity(machine['n_points'], 'regression-pin', 0.0, None),
                        'checksum': quantity(machine['checksum'], 'regression-pin', None, 1e-6),
                    }
                },
            }
        else:
            quantities, seconds = fitted(case, project, notes)
            document = {
                'schema': 1,
                'source': {
                    'engine': 'FullProf 8.40 (references); edi (regression pins)',
                    'artifact': f'../../../../knowledge/fitting/fullprof/{case}/reference.json',
                    'provenance': 'PROVENANCE.md',
                },
                'quantities': quantities,
            }
    (home / 'expected.json').write_text(json.dumps(document, indent=2) + '\n', encoding='utf-8')
    return seconds


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split('\n\n', 1)[0])
    parser.add_argument('cases', nargs='*', help='default: every catalogue case')
    args = parser.parse_args(argv)
    rows = yaml.safe_load((CLI / 'projects.yml').read_text(encoding='utf-8'))['projects']
    cases = args.cases or [row['id'] for row in rows if row.get('user-facing') is True]
    notes: list[str] = []
    for case in cases:
        seconds = write(case, notes)
        print(f'{case}\t{seconds:.2f}')
    for note in notes:
        print(f'differs from FullProf: {note}', file=sys.stderr)
    return 0


if __name__ == '__main__':
    sys.exit(main())
