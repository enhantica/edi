#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-3-Clause
"""Write the Co2SiO4 HEiDi 2.5 K reflections with estimated uncertainties.

The published 2.5 K file (Acta Cryst. B 64, 2008, supplementary bp5014-2.5K.hkl) carries 2-theta
in its F_squared_sigma column, so its uncertainties are estimated from the 55 K and 300 K data of
the same crystal, instrument and setting. A reflection is matched by its Laue-equivalent indices
(mmm: the signs of h, k and l do not matter):

1. measured at 55 K: sigma = max(sigma_55 * F2_2.5 / F2_55, sigma_55), the 55 K relative error
   carried over and never below the 55 K absolute sigma; a reflection measured at or below zero at
   55 K takes the 55 K absolute sigma;
2. otherwise measured at 300 K: the same with the 300 K values;
3. otherwise (mostly the reflections Pnma forbids, which carry only magnetic intensity at 2.5 K):
   from the 25 reflections estimated by 1 or 2 whose F2_2.5 is nearest, sigma = max(F2_2.5 times
   their median relative error, their median sigma). The second term is the counting floor rule 1
   keeps, so a reflection measured near zero does not get a vanishing sigma.

F2meas and FullProf's F2calc are kept as published; only the sigma column changes, and the file
header says so.

    python tools/data/estimate_cosio_heidi_su.py <folder with the bp5014-*.hkl files> <output.hkl>
"""

from __future__ import annotations

import argparse
import statistics
from pathlib import Path

NEIGHBOURS = 25


def read(path: Path) -> list[tuple[tuple[int, int, int], str, float, float, float, str]]:
    """A published _refln loop's rows: hkl, F2calc as text and number, F2meas, sigma, status."""
    rows = []
    for line in path.read_text(encoding='utf-8').splitlines():
        fields = line.split()
        if len(fields) == 7 and fields[6] in {'o', '<'}:
            hkl = (int(fields[0]), int(fields[1]), int(fields[2]))
            rows.append((
                hkl,
                fields[3],
                float(fields[3]),
                float(fields[4]),
                float(fields[5]),
                fields[6],
            ))
    return rows


def laue(hkl: tuple[int, int, int]) -> tuple[int, int, int]:
    return (abs(hkl[0]), abs(hkl[1]), abs(hkl[2]))


def estimate(low: list, warm: list, cold: list) -> list[tuple[float, int]]:
    """Each cold row's estimated sigma and the rule (1, 2 or 3) that gave it."""
    by_low = {laue(row[0]): row for row in low}
    by_warm = {laue(row[0]): row for row in warm}
    out: list[tuple[float, int] | None] = []
    for hkl, _, _, f2, _, _ in cold:
        for rule, table in ((1, by_low), (2, by_warm)):
            match = table.get(laue(hkl))
            if match is not None:
                # A reference measured at or below zero has no relative error to carry over; its
                # absolute sigma is the floor every match keeps.
                relative = match[4] * f2 / match[3] if match[3] > 0 else 0.0
                out.append((max(relative, match[4]), rule))
                break
        else:
            out.append(None)
    known = [(cold[i][3], out[i][0]) for i in range(len(cold)) if out[i] is not None]
    for i, value in enumerate(out):
        if value is None:
            f2 = cold[i][3]
            nearest = sorted(known, key=lambda item: abs(item[0] - f2))[:NEIGHBOURS]
            ratios = [sigma / measured for measured, sigma in nearest if measured > 0]
            relative = statistics.median(ratios) if ratios else 0.0
            floor = statistics.median(sigma for _, sigma in nearest)
            out[i] = (max(f2 * relative, floor), 3)
    return [value for value in out if value is not None]


HEADER = """\
# Co2SiO4, HEiDi (MLZ), 2.5 K: Sazonov et al., Acta Cryst. B 64 (2008) 661-668,
# supplementary bp5014-2.5K.hkl. F2meas and FullProf's F2calc are as published. The
# published sigma column holds 2-theta, so the sigma column here is ESTIMATED from the
# 55 K data of the same crystal (else the 300 K data, else from the 25 reflections of
# nearest intensity): tools/data/estimate_cosio_heidi_su.py in the edi repository.
"""


def main() -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument('source', type=Path, help='the folder holding the three bp5014 files')
    parser.add_argument('output', type=Path)
    args = parser.parse_args()
    cold = read(args.source / 'bp5014-2.5K.hkl')
    low = read(args.source / 'bp5014-55K.hkl')
    warm = read(args.source / 'bp5014-300K.hkl')
    sigmas = estimate(low, warm, cold)
    lines = [HEADER, 'data_2.5K', '', 'loop_']
    lines += [
        f' _refln_{name}'
        for name in (
            'index_h',
            'index_k',
            'index_l',
            'F_squared_calc',
            'F_squared_meas',
            'F_squared_sigma',
            'observed_status',
        )
    ]
    for (hkl, calc, _, f2, _, status), (sigma, _) in zip(cold, sigmas, strict=True):
        indices = f'{hkl[0]:4d}{hkl[1]:4d}{hkl[2]:4d}'
        lines.append(f'{indices} {calc:>11} {f2:11.2f} {sigma:9.2f} {status}')
    args.output.write_text('\n'.join(lines) + '\n', encoding='utf-8')
    counts = [sum(1 for _, rule in sigmas if rule == r) for r in (1, 2, 3)]
    print(
        f'{args.output}: {len(cold)} reflections; sigma from 55 K {counts[0]}, '
        f'300 K {counts[1]}, nearest {counts[2]}'
    )
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
