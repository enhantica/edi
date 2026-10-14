"""Independent WCAG/Oklab arithmetic from W3C and Bjorn Ottosson's matrices.

https://www.w3.org/TR/WCAG22/#dfn-relative-luminance
https://bottosson.github.io/posts/oklab/ (updated matrices, 2021-01-25)
Hue/chroma tolerance is the actual colour's half-LSB RGB quantisation box,
not a tolerance fitted to any product palette.
"""

import itertools
import math

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


def smallest_lightness_shift(source, background, calculated=None):  # noqa: PLR0914 - named matrix coordinates
    """Solve the 3:1 boundary along the published hue/chroma ray.

    Inverse Oklab matrices are from Ottosson's same published definition.
    No colour clipping is used: clipping would change the required hue/chroma.
    """
    lightness, a, b = oklab(source)
    meets_contrast = contrast(source, background) >= 3
    if meets_contrast and (calculated is None or distance(source, calculated) >= 0.10):
        return lightness
    target = (
        (1.05 / 3 - 0.05)
        if background == '#FFFFFF'
        else (
            3
            * (
                sum(
                    w * linear(c)
                    for w, c in zip((0.2126, 0.7152, 0.0722), rgb(background), strict=True)
                )
                + 0.05
            )
            - 0.05
        )
    )

    def luminance(level):
        cone_l = (level + 0.3963377774 * a + 0.2158037573 * b) ** 3
        m = (level - 0.1055613458 * a - 0.0638541728 * b) ** 3
        s = (level - 0.0894841775 * a - 1.2914855480 * b) ** 3
        red = 4.0767416621 * cone_l - 3.3077115913 * m + 0.2309699292 * s
        green = -1.2684380046 * cone_l + 2.6097574011 * m - 0.3413193965 * s
        blue = -0.0041960863 * cone_l - 0.7034186147 * m + 1.7076147010 * s
        return 0.2126 * red + 0.7152 * green + 0.0722 * blue

    low, high = (0, lightness) if background == '#FFFFFF' else (lightness, 1)
    for _ in range(80):
        midpoint = (low + high) / 2
        if luminance(midpoint) < target:
            low = midpoint
        else:
            high = midpoint
    boundary = (low + high) / 2
    if calculated is None:
        return boundary
    calc_l, calc_a, calc_b = oklab(calculated)
    radial = 0.10**2 - (a - calc_a) ** 2 - (b - calc_b) ** 2
    candidates = [lightness, boundary]
    if radial > 0:
        radius = math.sqrt(radial)
        candidates.extend([calc_l - radius, calc_l + radius])
    eligible = [
        level
        for level in candidates
        if 0 <= level <= 1
        and (level <= boundary + 1e-10 if background == '#FFFFFF' else level >= boundary - 1e-10)
        and (level - calc_l) ** 2 + (a - calc_a) ** 2 + (b - calc_b) ** 2 >= 0.10**2 - 1e-12
    ]
    if not eligible:
        raise ValueError('No hue/chroma-preserving lightness meets both palette rules')
    return min(eligible, key=lambda level: abs(level - lightness))


def lightness_quantisation_tolerance(actual):
    level = oklab(actual)[0]
    bounds = [(max(0, v - 0.5 / 255), min(1, v + 0.5 / 255)) for v in rgb(actual)]
    return max(abs(oklab(point)[0] - level) for point in itertools.product(*bounds)) + 1e-7
