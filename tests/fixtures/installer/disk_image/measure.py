# SPDX-License-Identifier: BSD-3-Clause
"""Measure installer text within a Finder capture's visible artwork."""

import argparse
from pathlib import Path

import numpy as np

from tests.fixtures.fast_chart_redraws.line_quality import read_png

TOLERANCE_POINTS = 2


def ink_rows(pixels):
    width = pixels.shape[1]
    center = pixels[:, width // 4 : 3 * width // 4]
    rows = np.flatnonzero(np.count_nonzero(center.max(axis=2) < 110, axis=1) > 5)
    if not rows.size:
        raise ValueError('No dark text was found in the central part of the measurement band')
    return int(rows[0]), int(rows[-1]) + 1


def capture_margins(picture, x, y, width, height):
    pixels = read_png(picture)
    rows, columns, _ = pixels.shape
    if not 0 <= x < x + width <= columns or not 0 <= y < y + height <= rows or height < 3:
        raise ValueError('The visible Finder content rectangle must lie inside the capture')
    content = pixels[y : y + height, x : x + width]
    band = height // 3
    top, _ = ink_rows(content[:band])
    _, label_end = ink_rows(content[-band:])
    return top, band - label_end


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('png', type=Path)
    parser.add_argument('x', type=int)
    parser.add_argument('y', type=int)
    parser.add_argument('width', type=int)
    parser.add_argument('height', type=int)
    parser.add_argument('--pixels-per-point', type=int, default=2, choices=(1, 2))
    args = parser.parse_args()
    top, bottom = capture_margins(args.png, args.x, args.y, args.width, args.height)
    scale = args.pixels_per_point
    print(f'{top / scale:g} pt above the instruction, {bottom / scale:g} pt below the label')
    return int(min(top, bottom) <= 0 or abs(top - bottom) > TOLERANCE_POINTS * scale)


if __name__ == '__main__':
    raise SystemExit(main())
