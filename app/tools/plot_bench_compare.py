# SPDX-License-Identifier: BSD-3-Clause
"""Compare two plotting benchmark tables (edi_app_plot_bench), side by side.

usage: python app/tools/plot_bench_compare.py <a.tsv> <b.tsv>

For every route, workload and measure in either table: the median in each, in milliseconds, and b's
over a's.
"""

import csv
import sys
from pathlib import Path


def read(path: Path) -> tuple[str, dict]:
    with path.open(newline='', encoding='utf-8') as handle:
        rows = list(csv.DictReader(handle, delimiter='\t'))
    if not rows:
        sys.exit(f'{path}: no rows')
    first = rows[0]
    name = f'{first["machine"]} ({first["renderer"]})'
    return name, {(r['method'], r['workload'], r['measure']): r for r in rows}


def cell(row: dict | None) -> tuple[str, float | None]:
    if row is None:
        return 'absent', None
    median = float(row['median_ms'])
    if median < 0:
        return row['status'], None
    note = '' if row['status'] == 'ok' else f' ({row["status"]}, n={row["n"]})'
    return f'{median:.1f}{note}', median


def main() -> None:
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    a_name, a = read(Path(sys.argv[1]))
    b_name, b = read(Path(sys.argv[2]))
    keys = list(a) + [k for k in b if k not in a]
    print(f'a: {a_name}\nb: {b_name}\n')
    header = ('method', 'workload', 'measure', 'a ms', 'b ms', 'b / a')
    lines = [header]
    for key in keys:
        a_text, a_ms = cell(a.get(key))
        b_text, b_ms = cell(b.get(key))
        ratio = f'{b_ms / a_ms:.2f}' if a_ms and b_ms is not None else ''
        lines.append((*key, a_text, b_text, ratio))
    widths = [max(len(str(line[i])) for line in lines) for i in range(len(header))]
    for line in lines:
        cells = (str(value).ljust(width) for value, width in zip(line, widths, strict=True))
        print('  '.join(cells).rstrip())


if __name__ == '__main__':
    main()
