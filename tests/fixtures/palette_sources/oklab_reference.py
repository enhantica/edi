"""Independent WCAG/Oklab arithmetic from W3C and Bjorn Ottosson's matrices.

https://www.w3.org/TR/WCAG22/#dfn-relative-luminance
https://bottosson.github.io/posts/oklab/ (updated matrices, 2021-01-25)
Hue/chroma tolerance is the actual colour's half-LSB RGB quantisation box,
not a tolerance fitted to any product palette.
"""

import itertools
import math
from functools import cache

import numpy as np

RGB_TO_LMS = (
    (0.4122214708, 0.5363325363, 0.0514459929),
    (0.2119034982, 0.6806995451, 0.1073969566),
    (0.0883024619, 0.2817188376, 0.6299787005),
)
LMS_TO_LAB = (
    (0.2104542553, 0.7936177850, -0.0040720468),
    (1.9779984951, -2.4285922050, 0.4505937099),
    (0.0259040371, 0.7827717662, -0.8086757660),
)


def rgb(hexadecimal):
    return tuple(int(hexadecimal[i : i + 2], 16) / 255 for i in (1, 3, 5))


def linear(value):
    return value / 12.92 if value <= 0.04045 else ((value + 0.055) / 1.055) ** 2.4


def oklab(colour):
    values = rgb(colour) if isinstance(colour, str) else colour
    encoded = tuple(map(linear, values))
    lms = [sum(a * b for a, b in zip(row, encoded, strict=True)) for row in RGB_TO_LMS]
    roots = [math.cbrt(value) for value in lms]
    return tuple(sum(a * b for a, b in zip(row, roots, strict=True)) for row in LMS_TO_LAB)


def contrast(a, b):
    def luminance(value):
        return sum(
            weight * linear(channel)
            for weight, channel in zip((0.2126, 0.7152, 0.0722), rgb(value), strict=True)
        )

    first, second = sorted((luminance(a), luminance(b)))
    return (second + 0.05) / (first + 0.05)


def polar(colour):
    lightness, a, b = oklab(colour)
    return lightness, math.hypot(a, b), math.degrees(math.atan2(b, a))


def angle_difference(first, second):
    return abs((first - second + 180) % 360 - 180)


def quantisation_tolerance(actual):
    _, chroma, hue = polar(actual)
    bounds = [(max(0, v - 0.5 / 255), min(1, v + 0.5 / 255)) for v in rgb(actual)]
    vertices = [polar(point) for point in itertools.product(*bounds)]
    return (
        max(abs(value[1] - chroma) for value in vertices) + 1e-7,
        max(angle_difference(value[2], hue) for value in vertices) + 1e-5,
    )


def hue_chroma_preserved(source, actual):
    _, before_chroma, before_hue = polar(source)
    _, after_chroma, after_hue = polar(actual)
    chroma_tolerance, hue_tolerance = quantisation_tolerance(actual)
    return abs(before_chroma - after_chroma) <= chroma_tolerance and (
        before_chroma < 1e-5 or angle_difference(before_hue, after_hue) <= hue_tolerance
    )


def distance(first, second):
    return math.dist(oklab(first), oklab(second))


def linear_rgb(lab):
    """Invert Ottosson's published Oklab matrices without channel clipping."""
    level, a, b = lab
    cone_l = (level + 0.3963377774 * a + 0.2158037573 * b) ** 3
    m = (level - 0.1055613458 * a - 0.0638541728 * b) ** 3
    s = (level - 0.0894841775 * a - 1.2914855480 * b) ** 3
    return (
        4.0767416621 * cone_l - 3.3077115913 * m + 0.2309699292 * s,
        -1.2684380046 * cone_l + 2.6097574011 * m - 0.3413193965 * s,
        -0.0041960863 * cone_l - 0.7034186147 * m + 1.7076147010 * s,
    )


def gamut_ray(source, level):
    """Keep the largest published chroma that fits sRGB at this lightness."""
    _, a, b = oklab(source)

    def point(scale):
        return level, scale * a, scale * b

    def inside(scale):
        return all(-1e-10 <= channel <= 1 + 1e-10 for channel in linear_rgb(point(scale)))

    if inside(1):
        return point(1)
    low, high = 0, 1
    for _ in range(48):
        mid = (low + high) / 2
        if inside(mid):
            low = mid
        else:
            high = mid
    return point(low)


def lab_contrast(lab, background):
    luminance = sum(w * c for w, c in zip((0.2126, 0.7152, 0.0722), linear_rgb(lab), strict=True))
    back = sum(
        w * linear(c) for w, c in zip((0.2126, 0.7152, 0.0722), rgb(background), strict=True)
    )
    low, high = sorted((luminance, back))
    return (high + 0.05) / (low + 0.05)


@cache
def smallest_adaptation(source, background, calculated=None):
    """Find the nearest feasible lightness on the gamut-mapped published hue ray."""
    origin = oklab(source)[0]
    calc = oklab(calculated) if calculated else None

    def eligible(level):
        lab = gamut_ray(source, level)
        return lab_contrast(lab, background) >= 3 and (
            calc is None or math.dist(lab, calc) >= 0.10
        )

    if eligible(origin):
        return gamut_ray(source, origin)
    candidates = []
    for end in (0, 1):
        previous = origin
        for step in range(1, 1025):
            level = origin + (end - origin) * step / 1024
            if eligible(level):
                bad, good = previous, level
                for _ in range(48):
                    mid = (bad + good) / 2
                    if eligible(mid):
                        good = mid
                    else:
                        bad = mid
                candidates.append(good)
                break
            previous = level
    if not candidates:
        raise ValueError('No gamut-mapped published hue meets both palette rules')
    return gamut_ray(source, min(candidates, key=lambda level: abs(level - origin)))


def smallest_lightness_shift(source, background, calculated=None):
    return smallest_adaptation(source, background, calculated)[0]


def gamut_hue_chroma_preserved(source, actual):
    """Compare hue and maximal gamut chroma within RGB rounding uncertainty."""
    level, chroma, hue = polar(actual)
    source_chroma, source_hue = polar(source)[1:]
    chroma_error, hue_error = quantisation_tolerance(actual)
    lightness_error = lightness_quantisation_tolerance(actual)
    expected = [
        math.hypot(*gamut_ray(source, max(0, min(1, candidate)))[1:])
        for candidate in (level - lightness_error, level, level + lightness_error)
    ]
    return min(expected) - chroma_error <= chroma <= max(expected) + chroma_error and (
        source_chroma < 1e-5 or angle_difference(source_hue, hue) <= hue_error
    )


def lightness_quantisation_tolerance(actual):
    level = oklab(actual)[0]
    bounds = [(max(0, v - 0.5 / 255), min(1, v + 0.5 / 255)) for v in rgb(actual)]
    return max(abs(oklab(point)[0] - level) for point in itertools.product(*bounds)) + 1e-7


@cache
def nearest_passing_lightness_error(source, background, calculated=None):  # noqa: PLR0914 - independent lattice coordinates and bounds
    """Nearest passing lattice point, bounded by one full RGB quantisation step.

    Quantisation is one-sided after projection onto a strict contrast/distance
    boundary. Search the neighbouring lattice, preserving the original half-LSB
    hue/chroma bounds. The six disputed minima have an exhaustive independent
    256-cubed witness in quantisation-proof.json, not a product-derived tolerance.
    """
    ideal = smallest_adaptation(source, background, calculated)
    origin = oklab(source)[0]
    direction = 1 if ideal[0] > origin else -1
    if ideal == oklab(source):
        return 0.0

    def encode(value):
        value = max(0, min(1, value))
        return 12.92 * value if value <= 0.0031308 else 1.055 * value ** (1 / 2.4) - 0.055

    centre = [round(encode(value) * 255) for value in linear_rgb(ideal)]
    offsets = np.array(list(itertools.product(range(-16, 17), repeat=3)))
    coordinates = offsets + centre
    coordinates = coordinates[np.all((coordinates >= 0) & (coordinates <= 255), axis=1)]
    encoded = coordinates / 255

    def array_lab(values):
        values = np.where(values <= 0.04045, values / 12.92, ((values + 0.055) / 1.055) ** 2.4)
        cones = np.cbrt(np.einsum('ij,kj->ik', values, np.array(RGB_TO_LMS)))
        return np.einsum('ij,kj->ik', cones, np.array(LMS_TO_LAB))

    values = array_lab(encoded)
    delta = (values[:, 0] - ideal[0]) * direction
    hue = np.degrees(np.arctan2(values[:, 2], values[:, 1]))
    hue_tolerance = np.zeros(len(values))
    full_tolerance = np.zeros(len(values))
    for vertex in itertools.product((-0.5, 0.5), repeat=3):
        mapped = array_lab(np.clip(encoded + np.array(vertex) / 255, 0, 1))
        hue_tolerance = np.maximum(
            hue_tolerance,
            np.abs((np.degrees(np.arctan2(mapped[:, 2], mapped[:, 1])) - hue + 180) % 360 - 180),
        )
        full = array_lab(np.clip(encoded + 2 * np.array(vertex) / 255, 0, 1))
        full_tolerance = np.maximum(full_tolerance, np.abs(full[:, 0] - values[:, 0]))
    source_hue = polar(source)[2]
    indices = np.nonzero(
        (delta >= -1e-10)
        & (delta <= full_tolerance + 1e-7)
        & (np.abs((hue - source_hue + 180) % 360 - 180) <= hue_tolerance + 1e-5)
    )[0]
    for index in indices[np.argsort(delta[indices])]:
        colour = '#' + ''.join(f'{value:02X}' for value in coordinates[index])
        if contrast(colour, background) < 3 or (
            calculated and distance(colour, calculated) < 0.10
        ):
            continue
        if gamut_hue_chroma_preserved(source, colour):
            return max(0, float(delta[index]))
    return math.inf


def full_step_lightness_tolerance(actual):
    level = oklab(actual)[0]
    bounds = [(max(0, value - 1 / 255), min(1, value + 1 / 255)) for value in rgb(actual)]
    return max(abs(oklab(point)[0] - level) for point in itertools.product(*bounds)) + 1e-7


def nearest_passing_lightness(source, actual, background, calculated=None):
    ideal = smallest_adaptation(source, background, calculated)[0]
    origin = oklab(source)[0]
    error = oklab(actual)[0] - ideal
    if abs(ideal - origin) <= 1e-10:
        return abs(error) <= lightness_quantisation_tolerance(actual)
    direction = 1 if ideal > origin else -1
    return (
        error * direction >= -1e-10
        and abs(error) <= full_step_lightness_tolerance(actual)
        and abs(error) <= nearest_passing_lightness_error(source, background, calculated) + 1e-7
    )
