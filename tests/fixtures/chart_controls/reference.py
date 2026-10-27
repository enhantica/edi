"""Recorded figure colours and ADR-0038 assignment, independent of edi."""

import json
from pathlib import Path

from tests.fixtures.approved_palettes.reference import gradient

OWNER = json.loads(Path(__file__).with_name('owner.json').read_text())
SCHEMES = ['earth', 'classic', 'soft', 'natural', 'colourBlindSafe']
PALETTES = [
    {**palette, 'scheme': scheme, 'default': index == 0}
    for index, (palette, scheme) in enumerate(zip(OWNER['palettes'], SCHEMES, strict=True))
]
_PREVIOUS = json.loads(
    Path(__file__).parents[1].joinpath('approved_palettes/colours.json').read_text()
)['palettes'][0]


def role_colours(theme):
    """The calc record replaces calc only; the existing role greys carry forward."""
    return {
        'total_calculation': OWNER['calc'][theme],
        'background': _PREVIOUS[theme]['background'],
        'difference': _PREVIOUS[theme]['difference'],
    }


def assigned_structure(palette, place, experiments, structures, theme):
    """Fresh projects assign experiments first, then structures, with Earth's reservation."""
    first = max(experiments, 2 if palette['name'] == 'Earth' else 0)
    position, size = first + place, first + structures
    colours = palette[theme]
    if position < 11:
        return colours[position]
    return gradient(colours[0], colours[1], (position - 10) / (size - 10))
