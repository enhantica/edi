# SPDX-License-Identifier: BSD-3-Clause
"""Write data/palettes/*.tsv from the schemes' sources (data/palettes/PROVENANCE.md).

Every data colour has at least 3:1 WCAG 2.x contrast against its theme's chart background. A
measured-data set keeps each source hue and moves only its Oklab lightness, by the smallest step
that passes, to the 8-bit colour that keeps the hue and chroma within its rounding; a colour that
would sit too close to an earlier one of its set moves further. Measured data must not look like
the calculated pattern: a set colour in the calculated curve's hue range, or too close to its
colour, goes to the end of its set, and one that is still too close takes the smallest lightness
shift, either way, that keeps it apart. A set keeps at most seven colours. Past them, a two-colour
gradient whose lightness rises from the first dataset to the last, every colour along it keeping
3:1 and out of the calculated hue range. The structure colours are muted, each at its own
lightness, hue and place apart from the others and from the measured colours. The script is run by
hand and its output is committed:

    python tools/palettes/generate.py [--check]
"""

import argparse
import functools
import itertools
import math
import sys
from collections.abc import Callable
from functools import partial
from pathlib import Path

BACKGROUND = {'light': '#FFFFFF', 'dark': '#444444'}
MIN_CONTRAST = 3.0
# The smallest Oklab distance between two colours of one set in one theme.
MIN_DISTANCE = 0.08
# The calculated pattern's colour in each theme (core/src/presentation.cpp) and the smallest
# Oklab distance a pattern colour keeps from it.
CALCULATED = {'light': '#F44336', 'dark': '#EF9A9A'}
MIN_CALCULATED_DISTANCE = 0.10
# The calculated curve's hue range: Oklab hues within this many degrees of its colour's hue in
# either theme. A colour of lower chroma than NEUTRAL_CHROMA has no hue and is never in it.
CALCULATED_HUE_WIDTH = 45.0
NEUTRAL_CHROMA = 0.04
# The most colours a measured-data set keeps before the gradient takes over.
MAX_PATTERN = 7
# The structure colours: at most five, muted to this chroma, each at its own step of this
# lightness ladder (from the background's side, the softest, outwards), and this many degrees apart
# in hue.
MAX_STRUCTURE = 5
STRUCTURE_CHROMA = 0.06
STRUCTURE_LIGHTNESS = {
    'light': [0.62, 0.56, 0.50, 0.44, 0.38],
    'dark': [0.70, 0.76, 0.82, 0.88, 0.94],
}
STRUCTURE_HUE_STEP = 25.0
# Earth tones from the Design Seeds and peaceful palettes (stone, wheat, plum, slate, sage, lichen,
# rose, artichoke, ochre, clay, lavender, lake teal), tried after a scheme's own candidates for its
# structure colours; the neutral ones never qualify.
EARTH_TONES = [
    '#A49693',
    '#B09F85',
    '#97667B',
    '#5C6670',
    '#9DB18E',
    '#CEC88A',
    '#A57B7C',
    '#6A4D83',
    '#B7946A',
    '#A67969',
    '#9389BD',
    '#7BA9A9',
]
# A gradient's ends: the first dataset at this lightness in the light theme and the last at the
# lightest that keeps 3:1; in the dark theme the first at the darkest that keeps 3:1 and the last
# at this lightness.
GRADIENT_FIRST_LIGHT = 0.36
GRADIENT_LAST_DARK = 0.92
# The step of the search for the smallest passing lightness shift; a passing range can be narrow.
LIGHTNESS_STEP = 0.0005
# How far, in 8-bit units per channel, the search for the passing 8-bit colour reaches from the
# exact one: near the gamut's edge a channel can move several units with the hue barely moving.
SEARCH_REACH = 10

# A source colour is one value for both themes, or a (light, dark) pair where the source gives
# its own dark colours.
Source = str | tuple[str, str]

SCHEMES: dict[str, dict] = {
    # edi's own, after the Design Seeds nature palettes (Jessica Colaluca), akulakreative's garden
    # greenery and paperheartdesign's peaceful palettes; PROVENANCE.md names each inspiration.
    'coast': {
        'title': 'Coast',
        'pattern': [
            ('#2C90D7', '#71BFFF'), ('#079E92', '#44D0C1'), ('#3CA059', '#7CCD8E'),
            ('#8978D7', '#B6AAFF'), ('#0999B2', '#43CAE7'),
        ],
        'structure': [
            '#B09F85', '#97667B', '#A57B7C', '#A49693', '#9DB18E', '#5C6670', '#DCC7AC', '#6A4D83',
            '#CEC88A',
        ],
        'gradient': ('#3E3875', '#2DC08E'),
    },
    'garden': {
        'title': 'Garden',
        'pattern': [
            ('#3D84A0', '#7CC3E0'), ('#3D8984', '#7CC7C2'), ('#668558', '#A2C393'),
            ('#896BA4', '#C7A8E5'), ('#527FA4', '#8EBDE4'),
        ],
        'structure': [
            '#756E51', '#DBAD93', '#A67969', '#A49693', '#B9A88E', '#CEC88A', '#5C6670', '#97667B',
            '#9DB18E',
        ],
        'gradient': ('#35536B', '#7E9A72'),
    },
    'peaceful': {
        'title': 'Peaceful',
        'pattern': [
            ('#3E7EBC', '#7CBDFF'), ('#42897C', '#80C8B9'), ('#7172B6', '#ACAFF8'),
            ('#3B888A', '#7BC7C9'), ('#9F6683', '#E0A2C1'),
        ],
        'structure': [
            '#B7946A', '#948D71', '#9389BD', '#707978', '#D9AE8E', '#97667B', '#B09F85', '#5C6670',
            '#9DB18E',
        ],
        'gradient': ('#6768AB', '#5E8D83'),
    },
    'fog-forest': {
        'title': 'Fog forest',
        'pattern': ['#6495A3', '#46653C', '#7BA9A9', '#A78FA9', '#BCB096'],
        'structure': [
            '#587175', '#9DB18E', '#A49693', '#B9C5D5', '#CEC88A', '#97667B', '#DCC7AC', '#A57B7C',
            '#6A4D83',
        ],
        'gradient': ('#32444E', '#9DB18E'),
    },
    'sage': {
        'title': 'Sage',
        'pattern': ['#66D795', '#5C7FA3', '#889F8E', '#8C7BA8', '#4A9A96', '#C2A15F'],
        'structure': [
            '#A49693', '#B09F85', '#97667B', '#7A8B99', '#CEC88A', '#A57B7C', '#DCC7AC', '#6A4D83',
            '#5C6670',
        ],
        'gradient': ('#2F5D6B', '#66D795'),
    },
    # Published palettes designed for data, in their published order.
    'okabe-ito': {
        'title': 'Okabe-Ito',
        'pattern': [
            '#0072B2', '#E69F00', '#009E73', '#CC79A7', '#56B4E9', '#D55E00', '#F0E442', '#000000',
        ],
        'gradient': ('#0072B2', '#009E73'),
    },
    'paul-tol-bright': {
        'title': 'Paul Tol bright',
        'pattern': ['#4477AA', '#EE6677', '#228833', '#CCBB44', '#66CCEE', '#AA3377', '#BBBBBB'],
        'gradient': ('#4477AA', '#228833'),
    },
    'paul-tol-muted': {
        'title': 'Paul Tol muted',
        'pattern': [
            '#CC6677', '#332288', '#DDCC77', '#117733', '#88CCEE', '#882255', '#44AA99', '#999933',
            '#AA4499',
        ],
        'gradient': ('#332288', '#44AA99'),
    },
    'tableau': {
        'title': 'Tableau 10',
        'pattern': [
            '#4E79A7', '#F28E2C', '#E15759', '#76B7B2', '#59A14F', '#EDC949', '#AF7AA1', '#FF9DA7',
            '#9C755F', '#BAB0AB',
        ],
        'gradient': ('#4E79A7', '#59A14F'),
    },
    'observable': {
        'title': 'Observable 10',
        'pattern': [
            '#4269D0', '#EFB118', '#FF725C', '#6CC5B0', '#3CA951', '#FF8AB7', '#A463F2', '#97BBF5',
            '#9C6B4E', '#9498A0',
        ],
        'gradient': ('#4269D0', '#3CA951'),
    },
    'carbon': {
        'title': 'IBM Carbon',
        # The light and dark categorical sequences, place by place.
        'pattern': [
            ('#6929C4', '#8A3FFC'), ('#1192E8', '#33B1FF'), ('#005D5D', '#007D79'),
            ('#9F1853', '#FF7EB6'), ('#FA4D56', '#FA4D56'), ('#570408', '#FFF1F1'),
            ('#198038', '#6FDC8C'), ('#002D9C', '#4589FF'), ('#EE538B', '#D12771'),
            ('#B28600', '#D2A106'), ('#009D9A', '#08BDBA'), ('#012749', '#BAE6FF'),
            ('#8A3800', '#BA4E00'), ('#A56EFF', '#D4BBFF'),
        ],
        'gradient': (('#6929C4', '#8A3FFC'), ('#009D9A', '#08BDBA')),
    },
    'dark2': {
        'title': 'ColorBrewer Dark2',
        'pattern': [
            '#1B9E77', '#D95F02', '#7570B3', '#E7298A', '#66A61E', '#E6AB02', '#A6761D', '#666666',
        ],
        'gradient': ('#7570B3', '#1B9E77'),
    },
    'petroff': {
        'title': 'Petroff',
        'pattern': [
            '#3F90DA', '#FFA90E', '#BD1F01', '#94A4A2', '#832DB6', '#A96B59', '#E76300', '#B9AC70',
            '#717581', '#92DADD',
        ],
        'gradient': ('#832DB6', '#92DADD'),
    },
    'vivid': {
        'title': 'Vivid',
        'pattern': [
            '#E41A1C', '#377EB8', '#4DAF4A', '#984EA3', '#FF7F00', '#FFFF33', '#A65628', '#F781BF',
            '#999999',
        ],
        'gradient': ('#377EB8', '#4DAF4A'),
    },
    # App themes, their accent colours.
    'nord': {
        'title': 'Nord',
        # nord10, nord14, nord15, nord8, nord13, nord7, nord9, nord12, nord11
        'pattern': [
            '#5E81AC', '#A3BE8C', '#B48EAD', '#88C0D0', '#EBCB8B', '#8FBCBB', '#81A1C1', '#D08770',
            '#BF616A',
        ],
        'gradient': ('#5E81AC', '#A3BE8C'),
    },
    'solarized': {
        'title': 'Solarized',
        # blue, green, violet, cyan, yellow, magenta, orange, red
        'pattern': [
            '#268BD2', '#859900', '#6C71C4', '#2AA198', '#B58900', '#D33682', '#CB4B16', '#DC322F',
        ],
        'gradient': ('#268BD2', '#859900'),
    },
    'catppuccin': {
        'title': 'Catppuccin',
        # Latte in the light theme, Mocha in the dark: blue, green, mauve, teal, yellow, sapphire,
        # lavender, peach, pink, red, maroon, flamingo, rosewater, sky
        'pattern': [
            ('#1E66F5', '#89B4FA'), ('#40A02B', '#A6E3A1'), ('#8839EF', '#CBA6F7'),
            ('#179299', '#94E2D5'), ('#DF8E1D', '#F9E2AF'), ('#209FB5', '#74C7EC'),
            ('#7287FD', '#B4BEFE'), ('#FE640B', '#FAB387'), ('#EA76CB', '#F5C2E7'),
            ('#D20F39', '#F38BA8'), ('#E64553', '#EBA0AC'), ('#DD7878', '#F2CDCD'),
            ('#DC8A78', '#F5E0DC'), ('#04A5E5', '#89DCEB'),
        ],
        'gradient': (('#8839EF', '#CBA6F7'), ('#179299', '#94E2D5')),
    },
    'apple': {
        'title': 'Apple',
        # blue, green, indigo, cyan, purple, mint, yellow, teal, orange, pink, red, brown
        'pattern': [
            ('#0088FF', '#0091FF'), ('#34C759', '#30D158'), ('#6155F5', '#6D7CFF'),
            ('#00C0E8', '#3CD3FE'), ('#CB30E0', '#DB34F2'), ('#00C8B3', '#00DAC3'),
            ('#FFCC00', '#FFD600'), ('#00C3D0', '#00D2E0'), ('#FF8D28', '#FF9230'),
            ('#FF2D55', '#FF375F'), ('#FF383C', '#FF4245'), ('#AC7F5E', '#B78A66'),
        ],
        'gradient': (('#6155F5', '#6D7CFF'), ('#00C8B3', '#00DAC3')),
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
    return oklab_of(channels(colour))


def oklab_of(values: list[float]) -> Lab:
    red, green, blue = (to_linear(c) for c in values)
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


def on_gamut(lab: Lab) -> Lab:
    """Return the colour; outside the sRGB gamut, its chroma shrinks to the edge, the hue kept."""
    lightness, a, b = lab
    if in_gamut(lab):
        return lab
    low, high = 0.0, 1.0
    for _ in range(40):
        middle = (low + high) / 2
        if in_gamut((lightness, a * middle, b * middle)):
            low = middle
        else:
            high = middle
    return lightness, a * low, b * low


def distance(first: str, second: str) -> float:
    return math.dist(oklab(first), oklab(second))


def contrast_of(lab: Lab, background: str) -> float:
    """Return the contrast ratio of an exact Oklab colour inside the gamut on the background."""
    red, green, blue = (min(1.0, max(0.0, c)) for c in linear_rgb(lab))
    low, high = sorted((0.2126 * red + 0.7152 * green + 0.0722 * blue, luminance(background)))
    return (high + 0.05) / (low + 0.05)


def nearest_passing(lab: Lab, step: float, passes: Callable[[Lab], bool]) -> Lab | None:
    """Return the exact colour at the smallest lightness shift towards `step` that passes.

    The published hue and chroma are kept, the chroma shrinking to the gamut's edge where needed.
    The steps are small enough not to miss a narrow passing range, and the shift is then halved
    between the last failing and the first passing lightness.
    """
    lightness, a, b = lab
    failing = lightness
    while 0.0 <= lightness + step <= 1.0:
        lightness += step
        if passes(on_gamut((lightness, a, b))):
            for _ in range(48):
                middle = (failing + lightness) / 2
                if passes(on_gamut((middle, a, b))):
                    lightness = middle
                else:
                    failing = middle
            return on_gamut((lightness, a, b))
        failing = lightness
    return None


def polar(values: list[float]) -> Lab:
    """Return Oklab lightness, chroma and hue in degrees of 0..1 sRGB channel values."""
    lightness, a, b = oklab_of(values)
    return lightness, math.hypot(a, b), math.degrees(math.atan2(b, a))


def hue_difference(first: float, second: float) -> float:
    return abs((first - second + 180) % 360 - 180)


def rounding_error(colour: str, target: Lab, published: str) -> list[float]:
    """Return how far an 8-bit colour is from the exact adapted colour, in units of its rounding.

    Lightness, chroma and hue are each compared with how far they move across the colour's
    half-unit box of channel values: the lightness with the exact colour's, the chroma with the
    published colour's at the gamut's edge and the hue with the published hue. Up to 1 is within
    the colour's rounding.
    """
    values = channels(colour)
    lightness, chroma, hue = polar(values)
    box = [(max(0.0, v - 0.5 / 255), min(1.0, v + 0.5 / 255)) for v in values]
    corners = [polar(list(corner)) for corner in itertools.product(*box)]
    _, published_chroma, published_hue = polar(channels(published))
    expected_chroma = math.hypot(*on_gamut((lightness, *oklab(published)[1:]))[1:])
    errors = [
        abs(lightness - target[0]) / max(abs(c[0] - lightness) for c in corners),
        abs(chroma - expected_chroma) / max(abs(c[1] - chroma) for c in corners),
    ]
    if published_chroma >= 1e-5:
        errors.append(
            hue_difference(published_hue, hue) / max(hue_difference(c[2], hue) for c in corners)
        )
    return errors


def keeps_hue_and_chroma(published: str, colour: str) -> bool:
    """Tell whether the colour has the published hue and the gamut's chroma within its rounding.

    The rounding is how far lightness, chroma and hue move across the colour's half-unit box of
    8-bit channel values; the chroma may be the gamut's at any lightness within that box.
    """
    values = channels(colour)
    lightness, chroma, hue = polar(values)
    box = [(max(0.0, v - 0.5 / 255), min(1.0, v + 0.5 / 255)) for v in values]
    corners = [polar(list(corner)) for corner in itertools.product(*box)]
    # A little more than floating-point noise, so a colour at the edge of its rounding counts.
    lightness_error = max(abs(c[0] - lightness) for c in corners) + 1e-7
    chroma_error = max(abs(c[1] - chroma) for c in corners) + 1e-7
    hue_error = max(hue_difference(c[2], hue) for c in corners) + 1e-5
    _, a, b = oklab(published)
    expected = [
        math.hypot(*on_gamut((min(1.0, max(0.0, level)), a, b))[1:])
        for level in (lightness - lightness_error, lightness, lightness + lightness_error)
    ]
    _, published_chroma, published_hue = polar(channels(published))
    return min(expected) - chroma_error <= chroma <= max(expected) + chroma_error and (
        published_chroma < 1e-5 or hue_difference(published_hue, hue) <= hue_error
    )


def nearest_8_bit(
    target: Lab, published: str, passes: Callable[[str], bool], origin: float | None = None
) -> str | None:
    """Return the passing 8-bit colour for the exact adapted colour `target`.

    Rounding the exact colour can fail, or land further than a neighbour that also passes. With
    `origin`, the colour that keeps the published hue and chroma within its rounding at the
    smallest lightness shift from it, no smaller than the exact colour's; else the one nearest
    `target`, measured by its rounding, one that keeps the hue and chroma first.
    """
    base = [round(v * 255) for v in channels(hex_clamped(target))]
    reach = SEARCH_REACH if origin is not None else 3
    found = []
    for offset in itertools.product(range(-reach, reach + 1), repeat=3):
        values = [v + o for v, o in zip(base, offset, strict=True)]
        if all(0 <= v <= 255 for v in values):
            colour = '#' + ''.join(f'{v:02X}' for v in values)
            if passes(colour):
                found.append(colour)
    if not found:
        return None
    if origin is not None:
        # Never closer to the origin than the exact colour: an 8-bit colour can pass by its own
        # rounding while its lightness falls short of the shift the rules ask for.
        beyond = [c for c in found if (oklab(c)[0] - target[0]) * (origin - target[0]) <= 0]
        found = sorted(beyond or found, key=lambda c: (abs(oklab(c)[0] - origin), c))
        return next((c for c in found if keeps_hue_and_chroma(published, c)), found[0])
    scored = []
    for colour in found:
        errors = rounding_error(colour, target, published)
        scored.append((
            not keeps_hue_and_chroma(published, colour),
            max(errors),
            sum(errors),
            colour,
        ))
    return min(scored)[-1]


def apart_from_calculated(colour: str, theme: str) -> bool:
    return distance(colour, CALCULATED[theme]) >= MIN_CALCULATED_DISTANCE


def passes_for_data(colour: str, theme: str) -> bool:
    return contrast(colour, BACKGROUND[theme]) >= MIN_CONTRAST and apart_from_calculated(
        colour, theme
    )


def apart(lab: Lab, earlier: list[Lab], calculated: Lab | None) -> bool:
    """Tell whether the colour keeps apart from the earlier colours and the calculated one."""
    return (calculated is None or math.dist(lab, calculated) >= MIN_CALCULATED_DISTANCE) and all(
        math.dist(lab, e) >= MIN_DISTANCE for e in earlier
    )


def passes_exact(lab: Lab, background: str, earlier: list[Lab], calculated: Lab | None) -> bool:
    return contrast_of(lab, background) >= MIN_CONTRAST and apart(lab, earlier, calculated)


def passes_8_bit(colour: str, background: str, earlier: list[Lab], calculated: Lab | None) -> bool:
    return contrast(colour, background) >= MIN_CONTRAST and apart(
        oklab(colour), earlier, calculated
    )


@functools.cache
def adapt_colour(colour: str, theme: str, earlier: tuple[str, ...], *, moved: bool) -> str:
    """Return one set colour adapted after the set's `earlier` colours (adapt_set)."""
    background = BACKGROUND[theme]
    away = -LIGHTNESS_STEP if theme == 'light' else LIGHTNESS_STEP
    rules = {
        'background': background,
        'earlier': [oklab(c) for c in earlier],
        'calculated': oklab(CALCULATED[theme]) if moved else None,
    }
    passes = partial(passes_8_bit, **rules)
    if passes(colour):
        return colour
    published = oklab(colour)
    steps = (away, -away) if moved else (away,)
    exact = [nearest_passing(published, step, partial(passes_exact, **rules)) for step in steps]
    found = [
        c
        for lab in exact
        if lab and (c := nearest_8_bit(lab, colour, passes, published[0])) is not None
    ]
    if not found:
        sys.exit(f'{colour} ({theme}): no lightness meets the palette rules')
    return min(found, key=lambda c: abs(oklab(c)[0] - published[0]))


def adapt_set(colours: list[str], theme: str, moved: list[bool] | None = None) -> list[str]:
    """Adapt each colour by the smallest lightness shift that passes.

    A colour passes with 3:1 contrast and MIN_DISTANCE from the set's earlier colours, so it
    shifts away from the background. A moved colour, at the end of its set, must also keep apart
    from the calculated colour, and takes the smaller shift of the two directions.
    """
    moved = moved or [False] * len(colours)
    out: list[str] = []
    for colour, data in zip(colours, moved, strict=True):
        out.append(adapt_colour(colour, theme, tuple(out), moved=data))
    return out


def side(source: Source, theme: str) -> str:
    """Return a source's colour in a theme: its own dark colour where it gives one."""
    return source if isinstance(source, str) else source[0 if theme == 'light' else 1]


def chroma_hue(colour: str) -> tuple[float, float]:
    _, a, b = oklab(colour)
    return math.hypot(a, b), math.degrees(math.atan2(b, a)) % 360


def in_calculated_hue_range(colour: str) -> bool:
    chroma, hue = chroma_hue(colour)
    return chroma >= NEUTRAL_CHROMA and any(
        hue_difference(hue, chroma_hue(c)[1]) <= CALCULATED_HUE_WIDTH for c in CALCULATED.values()
    )


def passing_colour(target: Lab, theme: str, step: float) -> str:
    """Return the 8-bit colour nearest `target` with 3:1, shifted towards `step` if needed.

    `target`'s chroma shrinks to the gamut's edge at each lightness, its hue kept.
    """
    rules = {'background': BACKGROUND[theme], 'earlier': [], 'calculated': None}
    lab = on_gamut(target)
    if not passes_exact(lab, **rules):
        lab = nearest_passing(target, step, partial(passes_exact, **rules))
        if lab is None:
            sys.exit(f'{hex_clamped(target)} ({theme}): no lightness keeps 3:1')
    colour = nearest_8_bit(lab, hex_clamped(lab), partial(passes_8_bit, **rules))
    if colour is None:
        sys.exit(f'{hex_clamped(lab)} ({theme}): no 8-bit colour keeps 3:1')
    return colour


def set_order(pattern: list[Source]) -> tuple[list[Source], list[bool]]:
    """Return the set in order and which of its colours are moved to its end.

    A colour in the calculated hue range or near the calculated colour, as published or once
    adapted, goes to the end, the nearest last: those moved for their hue first, the farthest in
    hue first, then those near the calculated colour itself. The set is cut to MAX_PATTERN colours.
    """
    in_range = {
        i
        for i, s in enumerate(pattern)
        if any(in_calculated_hue_range(side(s, t)) for t in BACKGROUND)
    }
    near = {
        i
        for i, s in enumerate(pattern)
        if any(not apart_from_calculated(side(s, t), t) for t in BACKGROUND)
    }

    def hue_gap(source: Source) -> float:
        gaps = []
        for theme in BACKGROUND:
            chroma, hue = chroma_hue(side(source, theme))
            if chroma >= NEUTRAL_CHROMA:
                gaps.append(hue_difference(hue, chroma_hue(CALCULATED[theme])[1]))
        return min(gaps, default=180.0)

    while True:
        moved = in_range | near
        order = [i for i in range(len(pattern)) if i not in moved]
        order += sorted(moved, key=lambda i: (i in near, -hue_gap(pattern[i]), i))
        order = order[:MAX_PATTERN]
        failing = {
            i
            for theme in BACKGROUND
            for i, colour in zip(
                order, adapt_set([side(pattern[i], theme) for i in order], theme), strict=True
            )
            if not apart_from_calculated(colour, theme)
        }
        if failing <= near:
            return [pattern[i] for i in order], [i in moved for i in order]
        near |= failing


def structure_set(
    candidates: list[Source], measured: dict[str, list[str]]
) -> tuple[dict[str, list[str]], list[Source]]:
    """Return up to MAX_STRUCTURE muted structure colours, from the candidates in order.

    Each takes its candidate's hue at STRUCTURE_CHROMA at most and the first free step of
    STRUCTURE_LIGHTNESS where it keeps MIN_DISTANCE from every measured colour and earlier
    structure colour in both themes, shifted only to keep 3:1. A candidate is skipped when it is
    neutral (each structure colour has its own hue), when its hue is within STRUCTURE_HUE_STEP of
    an earlier structure colour's, or when no free step keeps it apart. Also returns the
    candidates taken.
    """
    out: dict[str, list[str]] = {theme: [] for theme in BACKGROUND}
    taken_from: list[Source] = []
    hues: list[float] = []
    taken: set[int] = set()
    for source in candidates:
        if len(hues) == MAX_STRUCTURE:
            break
        chroma, hue = chroma_hue(side(source, 'light'))
        if min(chroma, STRUCTURE_CHROMA) < NEUTRAL_CHROMA or any(
            hue_difference(hue, h) < STRUCTURE_HUE_STEP for h in hues
        ):
            continue
        for step in range(len(STRUCTURE_LIGHTNESS['light'])):
            if step in taken:
                continue
            made = {}
            for theme in BACKGROUND:
                _, a, b = oklab(side(source, theme))
                own = math.hypot(a, b)
                scale = min(1.0, STRUCTURE_CHROMA / own) if own > 0 else 0.0
                target = (STRUCTURE_LIGHTNESS[theme][step], a * scale, b * scale)
                away = -LIGHTNESS_STEP if theme == 'light' else LIGHTNESS_STEP
                made[theme] = passing_colour(target, theme, away)
            if all(
                distance(made[theme], c) >= MIN_DISTANCE
                for theme in BACKGROUND
                for c in measured[theme] + out[theme]
            ):
                taken.add(step)
                taken_from.append(source)
                hues.append(hue)
                for theme in BACKGROUND:
                    out[theme].append(made[theme])
                break
    if not hues:
        sys.exit('a scheme keeps no structure colour')
    return out, taken_from


def gradient_of(first: Source, last: Source, theme: str) -> list[str]:
    """Return a gradient's two stops, the first the darker.

    Each is its source's hue and chroma, within the gamut, at its theme's end of the gradient.
    """
    _, a0, b0 = oklab(side(first, theme))
    _, a1, b1 = oklab(side(last, theme))
    if theme == 'light':
        start = passing_colour((GRADIENT_FIRST_LIGHT, a0, b0), theme, -LIGHTNESS_STEP)
        # The lightest that keeps 3:1: from white down.
        end = passing_colour((0.98, a1, b1), theme, -LIGHTNESS_STEP)
    else:
        start = passing_colour((0.30, a0, b0), theme, LIGHTNESS_STEP)
        end = passing_colour((GRADIENT_LAST_DARK, a1, b1), theme, LIGHTNESS_STEP)
    return [start, end]


def mix(first: str, second: str, t: float) -> str:
    lab_first, lab_second = oklab(first), oklab(second)
    return hex_clamped(tuple(x + (y - x) * t for x, y in zip(lab_first, lab_second, strict=True)))


def sample(stops: list[str], t: float) -> str:
    """Return the gradient at t in [0, 1], as edi's core samples it."""
    position = t * (len(stops) - 1)
    below = min(math.floor(position), len(stops) - 2)
    return mix(stops[below], stops[below + 1], position - below)


def check_gradient(name: str, theme: str, stops: list[str], first_count: int) -> None:
    """Exit unless the gradient gets lighter and every colour along it meets the rules.

    Its lightness rises from stop to stop, so along the Oklab mix between them; every colour the
    core can give along it is checked.
    """
    if any(oklab(a)[0] >= oklab(b)[0] for a, b in itertools.pairwise(stops)):
        sys.exit(f'{name} {theme}: the gradient {" ".join(stops)} does not get lighter')
    for count in range(first_count, 400):
        for place in range(count):
            colour = sample(stops, place / (count - 1))
            if not passes_for_data(colour, theme) or in_calculated_hue_range(colour):
                sys.exit(f'{name} {theme}: gradient colour {colour} fails at {place}/{count}')


def build(
    name: str,
) -> tuple[dict[str, tuple[list[str], ...]], list[Source], list[bool], list[Source]]:
    scheme = SCHEMES[name]
    order, moved = set_order(scheme['pattern'])
    rows = {}
    pattern = {
        theme: adapt_set([side(s, theme) for s in order], theme, moved) for theme in BACKGROUND
    }
    # edi's own schemes take their structure candidates, then the earth tones; a published scheme
    # takes its own colours from the last back.
    if 'structure' in scheme:
        candidates = scheme['structure'] + EARTH_TONES
    else:
        candidates = list(reversed(scheme['pattern']))
    structure, structure_sources = structure_set(candidates, pattern)
    for theme in BACKGROUND:
        for colour in pattern[theme]:
            if not passes_for_data(colour, theme):
                sys.exit(f'{name} {theme}: pattern colour {colour} fails a rule')
        stops = gradient_of(*scheme['gradient'], theme)
        check_gradient(name, theme, stops, len(order) + 1)
        rows[theme] = (pattern[theme], stops, structure[theme])
    return rows, order, moved, structure_sources


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
    parser.add_argument('--out', type=Path, default=None, help='write the tables here instead')
    args = parser.parse_args()
    out_dir = args.out or Path(__file__).resolve().parents[2] / 'data' / 'palettes'
    stale = []
    for name in SCHEMES:
        rows, order, moved, _ = build(name)
        for theme in BACKGROUND:
            pattern = rows[theme][0]
            closest = min(distance(a, b) for i, a in enumerate(pattern) for b in pattern[i + 1 :])
            print(
                f'{name} {theme}: {len(pattern)} colours, closest pair {closest:.3f}, '
                f'gradient {" ".join(rows[theme][1])}, {len(rows[theme][2])} structures'
            )
        moved_colours = [side(s, 'light') for s, m in zip(order, moved, strict=True) if m]
        if moved_colours:
            print(f'{name}: moved to the end: {", ".join(moved_colours)}')
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
