#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-3-Clause
"""The fit-quality comparison of edi, FullProf and diffraction-lib (ADR-0048).

For every example with measured data, the fitted curves of edi and diffraction-lib are read from
``knowledge/comparison/<case>/`` and FullProf's from its fitting reference under
``knowledge/fitting/fullprof/<case>/``. Every factor is recomputed here, pooled over banks, on the
points edi fits, with the measured sigma, w = 1/sigma^2, N the points and P the program's free
parameters:

- R_p = sum |y_o - y_c| / sum y_o
- R_wp = sqrt(sum w (y_o - y_c)^2 / sum w y_o^2)
- R_exp = sqrt((N - P) / sum w y_o^2)
- reduced chi^2 = sum w (y_o - y_c)^2 / (N - P)

The tables go into ``docs/user/guides/fit-quality.md`` between its markers; ``--check``
recomputes them from the committed curves and fails when the page differs.
"""

from __future__ import annotations

import argparse
import csv
import itertools
import json
import math
import re
import sys
from collections.abc import Iterable, Mapping
from pathlib import Path

import numpy as np
import yaml

ROOT = Path(__file__).resolve().parents[2]
REGISTRY = Path('docs/user/cli/projects.yml')
COMPARISON = Path('knowledge/comparison')
FULLPROF = Path('knowledge/fitting/fullprof')
PAGE = Path('docs/user/guides/fit-quality.md')
BEGIN = '<!-- fit-quality tables: written by tools/comparison/fit_quality.py -->'
END = '<!-- end of the fit-quality tables -->'
FIELDS = ('observed', 'calculated', 'sigma', 'included')
# FullProf writes its profile with x to three decimals.
X_TOLERANCE = 2e-3
# A row where edi's R_wp exceeds FullProf's by more than this relative amount needs an issue.
WORSE = 0.05


def agreement_factors(banks: Iterable[Mapping], n_free: int) -> dict[str, float | int]:
    """R_p, R_wp, R_exp, reduced chi^2 and N over the banks' included points.

    Each bank maps ``observed``, ``calculated``, ``sigma`` and ``included`` to equal-length
    sequences. Raises ValueError for unequal lengths, a non-finite included value, an included
    sigma that is not positive, no included point, or a free count that leaves no degree of
    freedom.
    """
    if isinstance(n_free, bool) or not isinstance(n_free, int) or n_free < 0:
        raise ValueError(f'the free-parameter count must be a non-negative integer: {n_free!r}')
    residual = observed = weighted_residual = weighted_observed = 0.0
    n_points = 0
    for index, bank in enumerate(banks):
        try:
            yo, yc, sigma = (np.asarray(bank[name], dtype=float) for name in FIELDS[:3])
            included = np.asarray(bank['included'], dtype=bool)
        except (KeyError, TypeError, ValueError) as error:
            raise ValueError(f'bank {index}: {error}') from error
        if any(array.ndim != 1 for array in (yo, yc, sigma, included)) or not (
            yo.size == yc.size == sigma.size == included.size
        ):
            raise ValueError(f'bank {index}: observed, calculated, sigma and included differ')
        yo, yc, sigma = yo[included], yc[included], sigma[included]
        if not (np.isfinite(yo).all() and np.isfinite(yc).all() and np.isfinite(sigma).all()):
            raise ValueError(f'bank {index}: an included value is not finite')
        if (sigma <= 0).any():
            raise ValueError(f'bank {index}: an included sigma is not positive')
        weight = 1.0 / sigma**2
        residual += float(np.abs(yo - yc).sum())
        observed += float(yo.sum())
        weighted_residual += float((weight * (yo - yc) ** 2).sum())
        weighted_observed += float((weight * yo**2).sum())
        n_points += int(yo.size)
    if n_points == 0:
        raise ValueError('no included observation')
    if n_points <= n_free:
        raise ValueError(f'{n_points} points leave no degree of freedom for {n_free} parameters')
    if observed == 0 or weighted_observed == 0:
        raise ValueError('the included observations sum to zero')
    dof = n_points - n_free
    return {
        'r_p': residual / observed,
        'r_wp': math.sqrt(weighted_residual / weighted_observed),
        'r_exp': math.sqrt(dof / weighted_observed),
        'reduced_chi_square': weighted_residual / dof,
        'n_points': n_points,
    }


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding='utf-8'))


def read_curves(path: Path) -> dict[str, np.ndarray]:
    with path.open(encoding='utf-8', newline='') as handle:
        rows = list(csv.DictReader(handle))
    columns = {name: np.array([float(row[name]) for row in rows]) for name in rows[0]}
    columns['included'] = columns['included'].astype(bool)
    return columns


def read_prf(path: Path) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """x, observed and calculated from a FullProf IGOR profile."""
    lines = path.read_text(encoding='utf-8').splitlines()
    rows = []
    for line in lines[lines.index('BEGIN') + 1 : lines.index('END')]:
        # Four 12-character fields; large intensities can run together.
        fields = [line[i : i + 12] for i in range(0, 48, 12)] if len(line) >= 48 else line.split()
        rows.append([float(field) for field in fields])
    data = np.array(rows)
    return data[:, 0], data[:, 1], data[:, 2]


def measured_cases(root: Path) -> list[str]:
    """The catalogue's cases with measured data, in registry order."""
    rows = yaml.safe_load((root / REGISTRY).read_text(encoding='utf-8'))['projects']
    cases = []
    for row in rows:
        if row.get('user-facing') is not True:
            continue
        project = root / REGISTRY.parent / row['id'] / 'project' / 'project.edi'
        if not re.search(r'(?m)^_metadata\.purpose "?simulation"?$', project.read_text('utf-8')):
            cases.append(str(row['id']))
    return cases


def fullprof_banks(root: Path, case: str, banks: list[str], grids: dict) -> dict:
    """FullProf's calculated curve on each bank's points; the points it lacks are left out."""
    home = root / FULLPROF / case
    names = read_json(home / 'reference.json')['banks']
    if names != banks:
        raise ValueError(f'{case}: FullProf banks {names} differ from edi banks {banks}')
    out = {}
    for index, bank in enumerate(banks, start=1):
        x, observed, calculated = read_prf(
            home / ('fit.prf' if len(banks) == 1 else f'fit_{index}.prf')
        )
        grid = grids[bank]
        nearest = np.clip(np.searchsorted(x, grid['x']), 1, x.size - 1)
        nearest -= (grid['x'] - x[nearest - 1]) < (x[nearest] - grid['x'])
        found = np.abs(x[nearest] - grid['x']) <= X_TOLERANCE
        values = np.where(found, calculated[nearest], np.nan)
        out[bank] = {
            'calculated': values,
            'found': found,
            'observed': np.where(found, observed[nearest], np.nan),
        }
    return out


def fullprof_cells(root: Path, case: str) -> dict[str, list[float]]:
    """Each phase's a, b, c in FullProf's fitted ``.new``."""
    lines = (root / FULLPROF / case / 'fit.new').read_text(encoding='utf-8').splitlines()
    cells, phase = {}, None
    for index, line in enumerate(lines):
        if line.startswith('!  Data for PHASE number'):
            names = (text.strip() for text in lines[index + 1 :] if not text.startswith('!'))
            phase = next(names, None)
        elif '# Cell Info' in line and phase is not None:
            cells[phase] = [float(value) for value in lines[index + 1].split()[:3]]
            phase = None
    return cells


def compare(root: Path, case: str) -> dict:
    """Every program's factors for one case, on the points edi fits that FullProf also has."""
    edi_dir = root / COMPARISON / case / 'edi'
    edi = read_json(edi_dir / 'reference.json')
    banks = edi['banks']
    grids = {bank: read_curves(edi_dir / f'{bank}.csv') for bank in banks}
    fullprof = read_json(root / FULLPROF / case / 'reference.json')
    fp_curves = fullprof_banks(root, case, banks, grids)
    for bank in banks:
        grids[bank]['included'] &= fp_curves[bank]['found']
        both = grids[bank]['included']
        apart = np.abs(fp_curves[bank]['observed'][both] - grids[bank]['observed'][both])
        if (apart > 0.01 + 1e-6 * np.abs(grids[bank]['observed'][both])).any():
            raise ValueError(f'{case}: FullProf and edi observed counts differ in {bank}')
    calculated = {'edi': {bank: grids[bank]['calculated'] for bank in banks}}
    free = {'edi': edi['n_free'], 'FullProf': fullprof['n_free']}
    calculated['FullProf'] = {bank: fp_curves[bank]['calculated'] for bank in banks}
    dl_dir = root / COMPARISON / case / 'diffraction-lib'
    dl = read_json(dl_dir / 'reference.json')
    if dl['model_compatible']:
        free['diffraction-lib'] = dl['n_free']
        dl_curves = {bank: read_curves(dl_dir / f'{bank}.csv') for bank in banks}
        for bank in banks:
            if not np.allclose(dl_curves[bank]['x'], grids[bank]['x'], rtol=0, atol=1e-6):
                raise ValueError(f'{case}: diffraction-lib and edi points differ in {bank}')
        calculated['diffraction-lib'] = {bank: dl_curves[bank]['calculated'] for bank in banks}
    rows = {}
    for program, curves in calculated.items():
        rows[program] = agreement_factors(
            [
                {
                    'observed': grids[bank]['observed'],
                    'calculated': curves[bank],
                    'sigma': grids[bank]['sigma'],
                    'included': grids[bank]['included'],
                }
                for bank in banks
            ],
            free[program],
        ) | {'n_free': free[program]}
    cells = {'edi': edi['cells'], 'FullProf': fullprof_cells(root, case)}
    if dl['model_compatible']:
        cells['diffraction-lib'] = dl['cells']
    return {'rows': rows, 'dl': dl, 'fullprof': fullprof, 'edi': edi, 'cells': cells}


def percent(value: float) -> str:
    return f'{100 * value:.2f}'


def with_su(value: float, su: float | None) -> str:
    """A value with its standard uncertainty in parentheses, to the uncertainty's two digits."""
    if not su or not math.isfinite(su) or su <= 0:
        return f'{value:.5f}'
    decimals = max(0, 1 - math.floor(math.log10(su)))
    return f'{value:.{decimals}f}({round(su * 10**decimals)})'


FACTOR_HEADER = (
    '| example | program | N | P | R<sub>p</sub> (%) | R<sub>wp</sub> (%) '
    '| R<sub>exp</sub> (%) | reduced χ² |'
)
CELL_HEADER = '| example | phase | edi a, b, c (Å) | FullProf | diffraction-lib |'
NONE = '\u2013'  # an en dash: nothing to show


def factor_row(link: str, program: str, row: dict | None) -> str:
    if row is None:
        return f'| {link} | {program} |' + f' {NONE} |' * 5 + ' not compared¹ |'
    numbers = [
        str(row['n_points']),
        str(row['n_free']),
        percent(row['r_p']),
        percent(row['r_wp']),
        percent(row['r_exp']),
        f'{row["reduced_chi_square"]:.4g}',
    ]
    return f'| {link} | {program} | ' + ' | '.join(numbers) + ' |'


def cell_text(cell: dict | list | None) -> str:
    if not cell:
        return NONE
    if isinstance(cell, dict):
        return ', '.join(itertools.starmap(with_su, cell.values()))
    return ', '.join(f'{value:.5f}' for value in cell)


def tables(root: Path) -> str:
    factors = [FACTOR_HEADER, '|' + ' --- |' * 8]
    cell_rows = [CELL_HEADER, '|' + ' --- |' * 5]
    worse, marked = [], []
    for case in measured_cases(root):
        result = compare(root, case)
        link = f'[`{case}`](../cli/{case}/index.md)'
        for program in ('edi', 'FullProf', 'diffraction-lib'):
            row = result['rows'].get(program)
            if row is None:
                marked.append(f'- {link}: {result["dl"]["reason"]}')
            factors.append(factor_row(link, program, row))
            link = ''
        edi_rwp, fp_rwp = result['rows']['edi']['r_wp'], result['rows']['FullProf']['r_wp']
        if edi_rwp > fp_rwp * (1 + WORSE):
            worse.append(f'- `{case}`: edi {percent(edi_rwp)} %, FullProf {percent(fp_rwp)} %')
        cells = result['cells']
        for phase, edi_cell in cells['edi'].items():
            fp = cells['FullProf'].get(phase)
            dl = cells.get('diffraction-lib', {}).get(phase)
            cell_rows.append(
                f'| `{case}` | {phase} | {cell_text(edi_cell)} | {cell_text(fp)} '
                f'| {cell_text(dl)} |'
            )
    worse_title = (
        f"Examples where edi's R<sub>wp</sub> exceeds FullProf's by more than {100 * WORSE:.0f} %:"
    )
    lines = [BEGIN, '', *factors, '', '¹ diffraction-lib cannot express the model:', '', *marked]
    lines += ['', worse_title, '', *(worse or ['- none']), '', '### Cell lengths', '']
    lines += [*cell_rows, '', END]
    return '\n'.join(lines)


def page_with_tables(page: str, block: str) -> str:
    start, end = page.find(BEGIN), page.find(END)
    if start < 0 or end < start:
        raise ValueError(f'{PAGE} has no {BEGIN!r} … {END!r} block')
    return page[:start] + block + page[end + len(END) :]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split('\n\n', 1)[0])
    parser.add_argument('--root', type=Path, default=ROOT)
    parser.add_argument('--check', action='store_true', help='recompute and compare the page')
    args = parser.parse_args(argv)
    path = args.root / PAGE
    page = path.read_text(encoding='utf-8')
    try:
        updated = page_with_tables(page, tables(args.root))
    except (OSError, ValueError, KeyError) as error:
        print(f'fit quality: {error}', file=sys.stderr)
        return 1
    if args.check:
        if updated != page:
            print(f'fit quality: {PAGE} differs from the committed curves', file=sys.stderr)
            return 1
        print('fit quality: every number recomputes from the committed curves')
        return 0
    path.write_text(updated, encoding='utf-8')
    print(f'fit quality: wrote {PAGE}')
    return 0


if __name__ == '__main__':
    sys.exit(main())
