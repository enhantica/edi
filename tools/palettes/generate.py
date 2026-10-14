# SPDX-License-Identifier: BSD-3-Clause
"""Write data/palettes/*.tsv from the published palettes (data/palettes/PROVENANCE.md).

Every data colour has at least 3:1 WCAG 2.x contrast against its theme's chart background.
A distinct set keeps each published hue and moves only its Oklab lightness, by the smallest
step that passes; a colour that would sit too close to an earlier one of its set moves
further. Measured data must not look like the calculated pattern: a set colour too close to
it in either theme goes to the end of its set, and a gradient keeps the longest run of its
published table that passes both rules, at evenly spaced stops. matplotlib supplies the
viridis, cividis, plasma and magma tables. The script is run by hand and its output is
committed:

    python tools/palettes/generate.py [--check]
"""

import argparse
import math
import sys
from collections.abc import Callable
from pathlib import Path

import matplotlib as mpl

BACKGROUND = {'light': '#FFFFFF', 'dark': '#444444'}
MIN_CONTRAST = 3.0
# The smallest Oklab distance between two colours of one set in one theme.
MIN_DISTANCE = 0.08
# The calculated pattern's colour in each theme (core/src/presentation.cpp) and the smallest
# Oklab distance a pattern colour keeps from it.
CALCULATED = {'light': '#F44336', 'dark': '#EF9A9A'}
MIN_CALCULATED_DISTANCE = 0.10
GRADIENT_STOPS = 17

# Paul Tol's iridescent scheme, as published (pale to dark).
TOL_IRIDESCENT = [
    '#FEFBE9', '#FCF7D5', '#F5F3C1', '#EAF0B5', '#DDECBF', '#D0E7CA', '#C2E3D2', '#B5DDD8',
    '#A8D8DC', '#9BD2E1', '#8DCBE4', '#81C4E7', '#7BBCE7', '#7EB2E4', '#88A5DD', '#9398D2',
    '#9B8AC4', '#9D7DB2', '#9A709E', '#906388', '#805770', '#684957', '#46353A',
]  # fmt: skip

SCHEMES = {
    'default': {
        # Material Design colours, as edi has used them, the light blue first.
        'pattern': [
            '#03A9F4', '#795548', '#4CAF50', '#9C27B0', '#FFC107', '#3F51B5', '#00BCD4', '#CDDC39',
        ],
        'gradient': 'viridis',
        'structure': ['#FF9800', '#009688', '#E91E63'],
    },
    'colour-blind-safe': {
        # Okabe and Ito, in the order edi has used them.
        'pattern': [
            '#0072B2', '#E69F00', '#009E73', '#CC79A7', '#56B4E9', '#D55E00', '#F0E442', '#000000',
        ],
        'gradient': 'cividis',
        # Paul Tol's muted wine, green and indigo.
        'structure': ['#882255', '#117733', '#332288'],
    },
    'tableau': {
        # Tableau 10, as matplotlib's tab10.
        'pattern': [
            '#1F77B4', '#FF7F0E', '#2CA02C', '#D62728', '#9467BD', '#8C564B', '#E377C2', '#7F7F7F',
            '#BCBD22', '#17BECF',
        ],
        'gradient': 'plasma',
        # The first colours of matplotlib's tab20b indigo, red and gold groups.
        'structure': ['#393B79', '#843C39', '#8C6D31'],
    },
    'paul-tol': {
        # Paul Tol's bright scheme.
        'pattern': ['#4477AA', '#EE6677', '#228833', '#CCBB44', '#66CCEE', '#AA3377', '#BBBBBB'],
        'gradient': TOL_IRIDESCENT,
        # Paul Tol's high-contrast scheme.
        'structure': ['#004488', '#DDAA33', '#BB5566'],
    },
    'vivid': {
        # ColorBrewer Set1.
        'pattern': [
            '#E41A1C', '#377EB8', '#4DAF4A', '#984EA3', '#FF7F00', '#FFFF33', '#A65628', '#F781BF',
            '#999999',
        ],
        'gradient': 'magma',
        # ColorBrewer Dark2's first three.
        'structure': ['#1B9E77', '#D95F02', '#7570B3'],
    },
}  # fmt: skip

Lab = tuple[float, float, float]


def channels(colour: str) -> list[float]:
    return [int(colour[i : i + 2], 16) / 255 for i in (1, 3, 5)]


def to_linear(c: float) -> float:
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4


def to_srgb(c: float) -> float:
    return 12.92 * c if c <= 0.0031308 else 1.055 * c ** (1 / 2.4) - 0.055


def luminance(colour: str) -> float:
    red, green, blue = (to_linear(c) for c in channels(colour))
    return 0.2126 * red + 0.7152 * green + 0.0722 * blue


def contrast(first: str, second: str) -> float:
    high, low = sorted((luminance(first), luminance(second)), reverse=True)
    return (high + 0.05) / (low + 0.05)


def oklab(colour: str) -> Lab:
    red, green, blue = (to_linear(c) for c in channels(colour))
    long_ = math.cbrt(0.4122214708 * red + 0.5363325363 * green + 0.0514459929 * blue)
    medium = math.cbrt(0.2119034982 * red + 0.6806995451 * green + 0.1073969566 * blue)
    short = math.cbrt(0.0883024619 * red + 0.2817188376 * green + 0.6299787005 * blue)
    return (
        0.2104542553 * long_ + 0.7936177850 * medium - 0.0040720468 * short,
        1.9779984951 * long_ - 2.4285922050 * medium + 0.4505937099 * short,
        0.0259040371 * long_ + 0.7827717662 * medium - 0.8086757660 * short,
    )


def linear_rgb(lab: Lab) -> Lab:
    lightness, a, b = lab
    long_ = (lightness + 0.3963377774 * a + 0.2158037573 * b) ** 3
    medium = (lightness - 0.1055613458 * a - 0.0638541728 * b) ** 3
    short = (lightness - 0.0894841775 * a - 1.2914855480 * b) ** 3
    return (
        4.0767416621 * long_ - 3.3077115913 * medium + 0.2309699292 * short,
        -1.2684380046 * long_ + 2.6097574011 * medium - 0.3413193965 * short,
        -0.0041960863 * long_ - 0.7034186147 * medium + 1.7076147010 * short,
    )


def in_gamut(lab: Lab) -> bool:
    return all(-1e-9 <= c <= 1 + 1e-9 for c in linear_rgb(lab))


def hex_clamped(lab: Lab) -> str:
    """Return the sRGB colour with each channel clamped, as edi's core mixes gradient stops."""
    red, green, blue = (
        round(min(1.0, max(0.0, to_srgb(min(1.0, max(0.0, c))))) * 255) for c in linear_rgb(lab)
    )
    return f'#{red:02X}{green:02X}{blue:02X}'


def hex_of(lab: Lab) -> str:
    """Return the sRGB colour; outside the gamut, the chroma shrinks with the hue kept."""
    lightness, a, b = lab
    if not in_gamut(lab):
        low, high = 0.0, 1.0
        for _ in range(40):
            middle = (low + high) / 2
            if in_gamut((lightness, a * middle, b * middle)):
                low = middle
            else:
                high = middle
        lab = (lightness, a * low, b * low)
    return hex_clamped(lab)


def distance(first: str, second: str) -> float:
    return math.dist(oklab(first), oklab(second))


def nearest_passing(lab: Lab, step: float, passes: Callable[[str], bool]) -> str | None:
    """Return the colour at the smallest lightness shift, in the direction of `step`, that passes.

    The shift is found by coarse steps, then halved between the last failing and the first passing
    lightness, so it is exact to well under one unit of the 8-bit colour.
    """
    lightness, a, b = lab
    failing = lightness
    while 0.0 <= lightness + step <= 1.0:
        lightness += step
        if passes(hex_of((lightness, a, b))):
            for _ in range(40):
                middle = (failing + lightness) / 2
                if passes(hex_of((middle, a, b))):
                    lightness = middle
                else:
                    failing = middle
            return hex_of((lightness, a, b))
        failing = lightness
    return None


def adapt(colour: str, theme: str) -> str:
    """Return the colour if it passes, else its hue and chroma at the nearest passing lightness."""
    background = BACKGROUND[theme]
    if contrast(colour, background) >= MIN_CONTRAST:
        return colour
    step = -0.01 if theme == 'light' else 0.01
    found = nearest_passing(oklab(colour), step, lambda c: contrast(c, background) >= MIN_CONTRAST)
    if found is None:
        sys.exit(f'{colour}: no lightness reaches {MIN_CONTRAST}:1 on {background}')
    return found


def apart_from_calculated(colour: str, theme: str) -> bool:
    return distance(colour, CALCULATED[theme]) >= MIN_CALCULATED_DISTANCE


def passes_for_data(colour: str, theme: str) -> bool:
    return contrast(colour, BACKGROUND[theme]) >= MIN_CONTRAST and apart_from_calculated(
        colour, theme
    )


def adapt_set(colours: list[str], theme: str, moved: frozenset[str] = frozenset()) -> list[str]:
    """Adapt each colour; one too close to an earlier one moves on, away from the background.

    A colour in `moved`, at the end of its set, also takes the smallest lightness shift away from
    the background that keeps it apart from the calculated colour, with 3:1 contrast and its
    distance from the set's earlier colours kept.
    """
    out: list[str] = []
    for colour in colours:
        candidate = adapt(colour, theme)
        if any(distance(candidate, earlier) < MIN_DISTANCE for earlier in out):
            step = -0.005 if theme == 'light' else 0.005
            found = nearest_passing(
                oklab(candidate),
                step,
                lambda c: all(distance(c, earlier) >= MIN_DISTANCE for earlier in out),
            )
            if found is None:
                sys.exit(f'{colour} ({theme}): cannot keep {MIN_DISTANCE} from its set')
            candidate = found
        if colour in moved and not apart_from_calculated(candidate, theme):
            found = nearest_passing(
                oklab(candidate),
                -0.01 if theme == 'light' else 0.01,
                lambda c: (
                    passes_for_data(c, theme)
                    and all(distance(c, earlier) >= MIN_DISTANCE for earlier in out)
                ),
            )
            if found is None:
                sys.exit(
                    f'{colour} ({theme}): no lightness keeps it apart from the calculated colour'
                )
            candidate = found
        if contrast(candidate, BACKGROUND[theme]) < MIN_CONTRAST:
            sys.exit(f'{colour} ({theme}): moved below {MIN_CONTRAST}:1')
        out.append(candidate)
    return out


def table_of(gradient: str | list[str]) -> list[str]:
    if isinstance(gradient, list):
        return gradient
    cmap = mpl.colormaps[gradient]
    out = []
    for index in range(256):
        red, green, blue = (round(c * 255) for c in cmap(index / 255)[:3])
        out.append(f'#{red:02X}{green:02X}{blue:02X}')
    return out


def passing_range(table: list[str], theme: str) -> tuple[int, int]:
    """Return the first and last entry of the longest run of entries that pass."""
    passes = [passes_for_data(c, theme) for c in table]
    best, start = (0, -1), None
    for index, good in enumerate([*passes, False]):
        if good and start is None:
            start = index
        elif not good and start is not None:
            if index - 1 - start > best[1] - best[0]:
                best = (start, index - 1)
            start = None
    if best[1] < best[0] + 1:
        sys.exit('a gradient keeps fewer than two passing entries')
    return best


def mix(first: str, second: str, t: float) -> str:
    lab_first, lab_second = oklab(first), oklab(second)
    return hex_clamped(tuple(x + (y - x) * t for x, y in zip(lab_first, lab_second, strict=True)))


def stops_of(table: list[str], first: int, last: int) -> list[str]:
    """Return GRADIENT_STOPS stops evenly spaced along entries first..last."""
    out = []
    for k in range(GRADIENT_STOPS):
        position = first + (last - first) * k / (GRADIENT_STOPS - 1)
        below = min(math.floor(position), last - 1)
        out.append(mix(table[below], table[below + 1], position - below))
    return out


def sample(stops: list[str], t: float) -> str:
    """Return the gradient at t in [0, 1], as edi's core samples it."""
    position = t * (len(stops) - 1)
    below = min(math.floor(position), len(stops) - 2)
    return mix(stops[below], stops[below + 1], position - below)


def set_order(colours: list[str]) -> tuple[list[str], frozenset[str]]:
    """Return the published set with those near the calculated colour at its end, and those."""
    moved: set[str] = set()
    while True:
        order = [c for c in colours if c not in moved] + [c for c in colours if c in moved]
        adapted = {theme: adapt_set(order, theme) for theme in BACKGROUND}
        failing = {
            published
            for theme, final in adapted.items()
            for published, colour in zip(order, final, strict=True)
            if not apart_from_calculated(colour, theme)
        }
        if failing <= moved:
            return order, frozenset(moved)
        moved |= failing


def build(
    name: str,
) -> tuple[dict[str, tuple[list[str], ...]], dict[str, tuple[int, int]], list[str], list[str]]:
    scheme = SCHEMES[name]
    table = table_of(scheme['gradient'])
    order, moved = set_order(scheme['pattern'])
    rows, ranges = {}, {}
    for theme in BACKGROUND:
        first, last = passing_range(table, theme)
        gradient = stops_of(table, first, last)
        # Every colour the core can give between the stops passes too.
        for count in range(2, 400):
            for place in range(count):
                colour = sample(gradient, place / (count - 1))
                if not passes_for_data(colour, theme):
                    sys.exit(f'{name} {theme}: gradient colour {colour} fails at {place}/{count}')
        pattern = adapt_set(order, theme, moved)
        # Every stored pattern colour passes, those moved to the end of the set included.
        for colour in pattern:
            if not passes_for_data(colour, theme):
                sys.exit(f'{name} {theme}: pattern colour {colour} fails a rule')
        rows[theme] = (pattern, gradient, adapt_set(scheme['structure'], theme))
        ranges[theme] = (first, last)
    return rows, ranges, order, [c for c in order if c in moved]


def tsv(rows: dict[str, tuple[list[str], ...]]) -> str:
    lines = ['role\tindex\tlight\tdark']
    for column, role in enumerate(('pattern', 'gradient', 'structure')):
        pairs = zip(rows['light'][column], rows['dark'][column], strict=True)
        lines.extend(
            f'{role}\t{index}\t{light}\t{dark}' for index, (light, dark) in enumerate(pairs)
        )
    return '\n'.join(lines) + '\n'


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument('--check', action='store_true', help='compare, write nothing')
    args = parser.parse_args()
    out_dir = Path(__file__).resolve().parents[2] / 'data' / 'palettes'
    stale = []
    for name in SCHEMES:
        rows, ranges, _order, moved = build(name)
        for theme, (first, last) in ranges.items():
            pattern = rows[theme][0]
            closest = min(distance(a, b) for i, a in enumerate(pattern) for b in pattern[i + 1 :])
            print(f'{name} {theme}: gradient entries {first}..{last}; closest pair {closest:.3f}')
        if moved:
            print(f'{name}: moved to the end, near the calculated colour: {", ".join(moved)}')
        path = out_dir / f'{name}.tsv'
        if not args.check:
            path.write_text(tsv(rows), encoding='utf-8')
        elif not path.exists() or path.read_text(encoding='utf-8') != tsv(rows):
            stale.append(path.name)
    if stale:
        print('out of date: ' + ', '.join(stale))
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
