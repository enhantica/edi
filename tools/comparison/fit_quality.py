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
# FullProf holds x in single precision and prints its profile to three decimals, so its x is
# within one float32 step of the true x plus 0.0005. A point is matched only to a FullProf row
# within that, and only when no other row is: an absent or ambiguous row is not matched.
FLOAT32_STEP = 2.0**-23
PRINT_ROUNDING = 5e-4
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
    """The catalogue's cases with measured data (an experiment with a data loop), in order."""
    rows = yaml.safe_load((root / REGISTRY).read_text(encoding='utf-8'))['projects']
    cases = []
    for row in rows:
        if row.get('user-facing') is not True:
            continue
        experiments = (root / REGISTRY.parent / row['id'] / 'project' / 'experiments').glob(
            '*.edi'
        )
        if any(
            re.search(r'(?m)^_(data|refln)\.', path.read_text('utf-8')) for path in experiments
        ):
            cases.append(str(row['id']))
    return cases


def match_rows(reference: np.ndarray, x: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Match each point of ``x`` to one ``reference`` row.

    A point is matched when exactly one row lies within the rounding tolerance and no other point
    claims that row. Returns the matched flags and each point's candidate row index.
    """
    order = np.argsort(reference, kind='stable')
    sorted_ref = reference[order]
    tolerance = np.abs(x) * FLOAT32_STEP + PRINT_ROUNDING
    low = np.searchsorted(sorted_ref, x - tolerance, side='left')
    high = np.searchsorted(sorted_ref, x + tolerance, side='right')
    nearest = order[np.clip(low, 0, max(reference.size - 1, 0))] if reference.size else low
    found = (high - low) == 1
    claimed = np.bincount(nearest[found], minlength=max(reference.size, 1))
    found &= claimed[nearest] == 1
    return found, nearest


def fullprof_banks(root: Path, case: str, banks: list[str], grids: dict) -> dict:
    """FullProf's calculated curve on each bank's points; ``found`` is false where it has none."""
    home = root / FULLPROF / case
    names = read_json(home / 'reference.json')['banks']
    if names != banks:
        raise ValueError(f'{case}: FullProf banks {names} differ from edi banks {banks}')
    out = {}
    for index, bank in enumerate(banks, start=1):
        x, observed, calculated = read_prf(
            home / ('fit.prf' if len(banks) == 1 else f'fit_{index}.prf')
        )
        # Only included points are compared, so only they take part in the matching: FullProf
        # writes no row for an excluded point, and one must not take an included point's row.
        included = grids[bank]['included']
        found = np.zeros(included.size, dtype=bool)
        nearest = np.zeros(included.size, dtype=int)
        found[included], nearest[included] = match_rows(x, grids[bank]['x'][included])
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


def fullprof_gap(case: str, banks: list[str], grids: dict, fp_curves: dict) -> str | None:
    """Why FullProf's curve cannot be compared: included points its profile lacks, if any."""
    lacking = []
    for bank in banks:
        grid = grids[bank]
        missing = grid['included'] & ~fp_curves[bank]['found']
        if missing.any():
            x = grid['x'][missing]
            lacking.append(f'{int(missing.sum())} in {bank} (x {x.min():g} to {x.max():g})')
        both = grid['included'] & fp_curves[bank]['found']
        apart = np.abs(fp_curves[bank]['observed'][both] - grid['observed'][both])
        if (apart > 0.01 + 1e-6 * np.abs(grid['observed'][both])).any():
            raise ValueError(f'{case}: FullProf and edi observed counts differ in {bank}')
    if not lacking:
        return None
    return (
        "FullProf's profile has no single matching row for included points: "
        + '; '.join(lacking)
        + '.'
    )


def diffraction_lib_curves(root: Path, case: str, grids: dict) -> dict[str, np.ndarray]:
    """diffraction-lib's calculated curve per bank, on edi's points."""
    curves = {}
    for bank, grid in grids.items():
        dl = read_curves(root / COMPARISON / case / 'diffraction-lib' / f'{bank}.csv')
        if not np.allclose(dl['x'], grid['x'], rtol=0, atol=1e-6):
            raise ValueError(f'{case}: diffraction-lib and edi points differ in {bank}')
        curves[bank] = dl['calculated']
    return curves


def compare(root: Path, case: str) -> dict:
    """Every program's factors for one case, on the points edi fits.

    A program whose curve does not cover every one of those points is not compared, and the
    reason says which points it lacks; the points are never dropped to make it fit.
    """
    edi_dir = root / COMPARISON / case / 'edi'
    edi = read_json(edi_dir / 'reference.json')
    banks = edi['banks']
    grids = {bank: read_curves(edi_dir / f'{bank}.csv') for bank in banks}
    fullprof = read_json(root / FULLPROF / case / 'reference.json')
    fp_curves = fullprof_banks(root, case, banks, grids)
    reasons = {}
    calculated = {'edi': {bank: grids[bank]['calculated'] for bank in banks}}
    free = {'edi': edi['n_free'], 'FullProf': fullprof['n_free']}
    gap = fullprof_gap(case, banks, grids, fp_curves)
    if gap:
        reasons['FullProf'] = gap
    else:
        calculated['FullProf'] = {bank: fp_curves[bank]['calculated'] for bank in banks}
    dl = read_json(root / COMPARISON / case / 'diffraction-lib' / 'reference.json')
    if dl['model_compatible']:
        free['diffraction-lib'] = dl['n_free']
        calculated['diffraction-lib'] = diffraction_lib_curves(root, case, grids)
    else:
        reasons['diffraction-lib'] = dl['reason']
    rows = {}
    for program, curves in calculated.items():
        banks_data = [
            {
                'observed': grids[bank]['observed'],
                'calculated': curves[bank],
                'sigma': grids[bank]['sigma'],
                'included': grids[bank]['included'],
            }
            for bank in banks
        ]
        rows[program] = agreement_factors(banks_data, free[program]) | {'n_free': free[program]}
    cells = {'edi': edi['cells'], 'FullProf': fullprof_cells(root, case)}
    if dl['model_compatible']:
        cells['diffraction-lib'] = dl['cells']
    return {'rows': rows, 'reasons': reasons, 'free': free, 'cells': cells}


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
CELL_HEADER = '| example | phase | edi (Å) | FullProf (Å) | diffraction-lib (Å) |'
NONE = '\u2013'  # an en dash: nothing to show
CELL_TIE = 2e-5  # Å


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


def independent(lengths: list) -> list:
    """The lengths symmetry leaves free: a; a and c; or a, b and c."""
    a, b, c = lengths
    # FullProf's .new rounds a tied length on its own, so ties are judged to its last digit.
    tied = lambda x, y: abs(x[0] - y[0]) <= CELL_TIE  # noqa: E731
    if tied(a, b) and tied(a, c):
        return [a]
    if tied(a, b):
        return [a, c]
    return [a, b, c]


def cell_text(cell: dict | list | None) -> str:
    if not cell:
        return NONE
    if isinstance(cell, dict):
        return ', '.join(itertools.starmap(with_su, independent(list(cell.values()))))
    lengths = independent([(value, None) for value in cell])
    return ', '.join(f'{value:.5f}' for value, _ in lengths)


def case_lines(root: Path, case: str, out: dict[str, list[str]]) -> None:
    """Add one example's table rows and list entries to ``out``."""
    result = compare(root, case)
    link = first = f'[`{case}`](../cli/{case}/index.md)'
    for program in ('edi', 'FullProf', 'diffraction-lib'):
        row = result['rows'].get(program)
        if row is None:
            out['marked'].append(f'- {first}, {program}: {result["reasons"][program]}')
        out['factors'].append(factor_row(link, program, row))
        link = ''
    counts = result['free']
    if len(set(counts.values())) > 1:
        out['unequal'].append(
            f'- `{case}`: ' + ', '.join(f'{name} {count}' for name, count in counts.items())
        )
    fullprof = result['rows'].get('FullProf')
    edi_rwp = result['rows']['edi']['r_wp']
    if fullprof and edi_rwp > fullprof['r_wp'] * (1 + WORSE):
        out['worse'].append(
            f'- `{case}`: edi {percent(edi_rwp)} %, FullProf {percent(fullprof["r_wp"])} %'
        )
    cells = result['cells']
    for phase, edi_cell in cells['edi'].items():
        fp = cells['FullProf'].get(phase)
        dl = cells.get('diffraction-lib', {}).get(phase)
        out['cells'].append(
            f'| `{case}` | {phase} | {cell_text(edi_cell)} | {cell_text(fp)} | {cell_text(dl)} |'
        )


def tables(root: Path) -> str:
    out = {
        'factors': [FACTOR_HEADER, '|' + ' --- |' * 8],
        'cells': [CELL_HEADER, '|' + ' --- |' * 5],
        'marked': [],
        'worse': [],
        'unequal': [],
    }
    for case in measured_cases(root):
        case_lines(root, case, out)
    worse_title = (
        f"Examples where edi's R<sub>wp</sub> exceeds FullProf's by more than {100 * WORSE:.0f} %:"
    )
    lines = [BEGIN, '', *out['factors'], '', '¹ Not compared, and why:', '']
    lines += [*out['marked'], '', worse_title, '', *(out['worse'] or ['- none'])]
    lines += ['', 'Examples whose programs free different numbers of parameters:', '']
    lines += [*(out['unequal'] or ['- none']), '', '### Cell lengths', '']
    lines += [*out['cells'], '', END]
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
