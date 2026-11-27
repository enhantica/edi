#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-3-Clause
"""Write a synthetic three-column plain data file (x y sigma) of an exact size.

    python3 tools/probes/large_plain_data.py <size MB> <output path>

1 MB is 1 000 000 bytes. Every line is 29 bytes wide; the bytes whole lines leave over become
extra spaces in the last line, so the file has exactly the requested size. x is 2 theta from 5 to
175 degrees in equal steps, strictly ascending; y = 1000 + 500 sin(x) plus deterministic noise in
[-5, 5); sigma = sqrt(y). It prints the byte and line counts it wrote, the reference counts for
the web app's data file bound (edi ADR-0110).
"""

import math
import sys
from pathlib import Path

WIDTH = 29
X0, X1 = 5.0, 175.0
BLOCK = 100_000


def line(i: int, step: float) -> str:
    """Line `i` of the pattern."""
    x = X0 + i * step
    noise = ((i * 2654435761) % 1000) / 100.0 - 5.0
    y = 1000.0 + 500.0 * math.sin(x) + noise
    return f'{x:11.7f} {y:8.3f} {math.sqrt(y):7.4f}\n'


def write(target: int, path: Path) -> int:
    """Write `target` bytes of pattern to `path`; the number of lines."""
    lines = target // WIDTH
    if lines < 2:
        raise SystemExit('the size is too small for two lines')
    step = (X1 - X0) / (lines - 1)
    if step <= 1e-7:
        raise SystemExit(f'step {step} is below the printed resolution')
    with path.open('w', encoding='ascii', newline='\n') as out:
        for start in range(0, lines - 1, BLOCK):
            block = ''.join(line(i, step) for i in range(start, min(start + BLOCK, lines - 1)))
            if len(block) % WIDTH:
                raise SystemExit(f'a line near {start} is not {WIDTH} bytes wide')
            out.write(block)
        last = line(lines - 1, step)
        out.write(last[:11] + ' ' * (target - lines * WIDTH) + last[11:])
    return lines


def main() -> None:
    """Write the file and print its counts."""
    if len(sys.argv) != 3:
        raise SystemExit(__doc__)
    target = round(float(sys.argv[1]) * 1_000_000)
    path = Path(sys.argv[2])
    lines = write(target, path)
    size = path.stat().st_size
    if size != target:
        raise SystemExit(f'the file has {size} bytes, wanted {target}')
    print(f'bytes={size} lines={lines} path={path}')


if __name__ == '__main__':
    main()
