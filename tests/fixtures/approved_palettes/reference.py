"""Owner-approved coordinates and Ottosson Oklab formulas (2020/2021)."""

import json
import math
from pathlib import Path

PALETTES = json.loads(Path(__file__).with_name('colours.json').read_text())['palettes']
SCHEMES = ['ediNatural', 'ediCoast', 'ediGarden', 'ediStudio', 'ediContrast']


def multiply(matrix, values):
    return tuple(sum(a * b for a, b in zip(row, values, strict=True)) for row in matrix)


def lab(colour):
    rgb = [int(colour[i : i + 2], 16) / 255 for i in (1, 3, 5)]
    linear = [v / 12.92 if v <= 0.04045 else ((v + 0.055) / 1.055) ** 2.4 for v in rgb]
    lms = multiply(
        (
            (0.4122214708, 0.5363325363, 0.0514459929),
            (0.2119034982, 0.6806995451, 0.1073969566),
            (0.0883024619, 0.2817188376, 0.6299787005),
        ),
        linear,
    )
    return multiply(
        (
            (0.2104542553, 0.7936177850, -0.0040720468),
            (1.9779984951, -2.4285922050, 0.4505937099),
            (0.0259040371, 0.7827717662, -0.8086757660),
        ),
        [math.cbrt(v) for v in lms],
    )


def gradient(first, second, t):
    if t == 0:
        return first
    if t == 1:
        return second
    mixed = [a + (b - a) * t for a, b in zip(lab(first), lab(second), strict=True)]
    lms = multiply(
        (
            (1, 0.3963377774, 0.2158037573),
            (1, -0.1055613458, -0.0638541728),
            (1, -0.0894841775, -1.2914855480),
        ),
        mixed,
    )
    rgb = multiply(
        (
            (4.0767416621, -3.3077115913, 0.2309699292),
            (-1.2684380046, 2.6097574011, -0.3413193965),
            (-0.0041960863, -0.7034186147, 1.7076147010),
        ),
        [v**3 for v in lms],
    )
    encoded = [12.92 * v if v <= 0.0031308 else 1.055 * v ** (1 / 2.4) - 0.055 for v in rgb]
    return '#' + ''.join(f'{math.floor(min(1, max(0, v)) * 255 + 0.5):02X}' for v in encoded)


def assigned(palette, role, place, count, theme):
    colours = palette[theme][role]
    if count <= 5:
        return colours[min(place, max(0, count - 1))]
    return gradient(colours[0], colours[1], min(place, count - 1) / (count - 1))
