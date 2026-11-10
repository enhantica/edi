#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-3-Clause
"""Write the single-crystal catalogue cases' FullProf ``reference.json`` records (ADR-0048).

    python tools/cli_projects/catalogue_sc_references.py [case ...]

Each case's folder ``knowledge/fitting/fullprof/<case>/`` holds FullProf's fit from the
project's own start: ``start.pcr`` (the input as written, never rewritten), ``start.int`` (the
reflections), and the run's outputs ``fit.*`` with ``run.log``. FullProf runs once, when a
reference is written, never here: this reads the committed outputs. The record keeps FullProf's
final parameters as it prints them and, beside them, the same values in the labels and units
edi's report uses (``report_values``): FullProf's beta tensors converted to the project's own ADP
type, Pr2NiO4's scale times FullProf's occupancy normalisation.
``tools/cli_projects/catalogue_expected.py`` turns them into ``expected.json``.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CLI = ROOT / 'docs' / 'user' / 'cli'
FULLPROF = ROOT / 'knowledge' / 'fitting' / 'fullprof'
VERSION = '8.40 Feb2026'
PARAMETER = re.compile(
    r'->\s+Parameter number\s+(\d+)\s*:\s+(\S+)\s+(\S+)\s*\(\s*\+/-\s+(\S+)\s*\)'
)
ARTIFACTS = ('start.pcr', 'start.int', 'fit.pcr', 'fit.out', 'fit.sum', 'fit.prf', 'run.log')

# Per case: the cell (for the beta conversions), the project's ADP type, FullProf's scale factor to
# edi's, and the experiment labels FullProf's scales and extinction terms belong to.
CASES = {
    'sc-neut-cwl_pr2nio4-5c2': {
        'cell': (5.417799, 5.4146, 12.483399),
        'adp': 'Bani',
        # FullProf's occupancy normalisation is 8 times the project's per-site occupancy: its scale
        # is the project's over 64 (tests/fixtures/single_crystal/README.md).
        'scale_factor': 64.0,
        'scales': {'Scale1': 'scale'},
        'extinction': {},
    },
    'sc-neut-tof_taurine-senju': {
        'cell': None,  # the project's ADPs are betas, as FullProf's
        'adp': 'beta',
        'scale_factor': 1.0,
        'scales': {f'Scale{n}': f'senju_{n}.scale' for n in range(1, 7)},
        'extinction': {
            'Ext1': 'senju_1.coefficient_11',
            'Ext2': 'senju_1.coefficient_22',
            'Ext3': 'senju_1.coefficient_33',
        },
    },
    'sc-neut-cwl_tb2ti2o7-heidi': {
        'cell': (10.13, 10.13, 10.13),
        'adp': 'Uani',
        'scale_factor': 1.0,
        'scales': {'Scale1': 'scale'},
        # FullProf's own extinction term, which has no edi counterpart.
        'extinction': {'Ext1': 'fullprof_extinction_1'},
        # edi fits the crystal-path mixed-radius Becker-Coppens extinction; FullProf has no such
        # model and fits its own empirical one (Ext-Model 1, Ext1 free).
        'models_differ': 'extinction: edi fits Becker-Coppens mixed with the crystal path, '
        'FullProf its empirical model 1',
    },
}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def parameters(out: Path) -> dict[str, dict]:
    """FullProf's final refined parameters by number: its last listing of each."""
    found = {}
    for match in PARAMETER.finditer(out.read_text(encoding='latin-1')):
        number, symbol, value, su = match.groups()
        found[number] = {'symbol': symbol, 'value': float(value), 'uncertainty': float(su)}
    return dict(sorted(found.items(), key=lambda item: int(item[0])))


def adp_factor(kind: str, cell: tuple[float, float, float] | None, i: int, j: int) -> float:
    """A beta component's factor to the project's ADP type (orthogonal cells only)."""
    if kind == 'beta':
        return 1.0
    a = cell[i] * cell[j]
    if kind == 'Bani':
        return 4.0 * a
    if kind == 'Uani':
        return a / (2.0 * math.pi**2)
    raise ValueError(kind)


def report_values(case: str, fitted: dict[str, dict]) -> dict[str, dict]:
    """FullProf's values in edi's report labels and units."""
    spec = CASES[case]
    values = {}
    for item in fitted.values():
        symbol, value, su = item['symbol'], item['value'], item['uncertainty']
        if symbol in spec['scales']:
            label, factor = spec['scales'][symbol], spec['scale_factor']
        elif symbol in spec['extinction']:
            label, factor = spec['extinction'][symbol], 1.0
        elif match := re.fullmatch(r'([XYZ])_(\w+)', symbol):
            label, factor = f'{match[2]}.fract_{match[1].lower()}', 1.0
        elif match := re.fullmatch(r'Biso_(\w+)', symbol):
            label, factor = f'{match[1]}.adp_iso', 1.0
        elif match := re.fullmatch(r'bet([123])([123])_(\w+)', symbol):
            i, j = int(match[1]) - 1, int(match[2]) - 1
            label = f'{match[3]}.adp_{match[1]}{match[2]}'
            factor = adp_factor(spec['adp'], spec['cell'], i, j)
        else:
            raise SystemExit(f'{case}: no report label for FullProf parameter {symbol}')
        values[label] = {'value': value * factor, 'uncertainty': su * factor}
    return values


def write(case: str) -> None:
    home = FULLPROF / case
    out = (home / 'fit.out').read_text(encoding='latin-1')
    summary = (home / 'fit.sum').read_text(encoding='latin-1')
    fitted = parameters(home / 'fit.out')
    observed = re.search(r'Nobserv \(I>n\*sigma\):\s+(\d+)', out)
    rf2w = re.findall(r'RF2w-factor :\s+(\S+)', summary)
    chi2 = re.findall(r'Global user-weigthed Chi2 \(Bragg contrib\.\):\s+(\S+)', summary)
    project = CLI / case / 'project'
    record = {
        'program': 'FullProf',
        'version': VERSION,
        'same_start': True,
        'start_project': f'docs/user/cli/{case}/project',
        'project_sha256': {
            str(path.relative_to(project)): sha256(path) for path in sorted(project.rglob('*.edi'))
        },
        'scope': 'fit',
        'converged': 'Convergence reached at this CYCLE' in out,
        'cycles': len(re.findall(r'=> CYCLE No\.:', out)),
        'n_free': len(fitted),
        'n_points_fitted': int(observed[1]),
        'r_wp': float(rf2w[-1]) / 100.0,
        'chi2': float(chi2[-1]),
        'exit': int(re.search(r'exit (\d+)', (home / 'run.log').read_text(encoding='latin-1'))[1]),
        'artifacts_sha256': {name: sha256(home / name) for name in ARTIFACTS},
        'fullprof_parameters': fitted,
        'report_values': report_values(case, fitted),
    }
    if 'models_differ' in CASES[case]:
        record['models_differ'] = CASES[case]['models_differ']
    (home / 'reference.json').write_text(json.dumps(record, indent=2) + '\n', encoding='utf-8')


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split('\n\n', 1)[0])
    parser.add_argument('cases', nargs='*', help='default: every single-crystal case')
    args = parser.parse_args(argv)
    for case in args.cases or CASES:
        write(case)
        print('wrote', case)
    return 0


if __name__ == '__main__':
    sys.exit(main())
