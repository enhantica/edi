"""Recorded figure colours and ADR-0038 assignment, independent of edi."""

import json
from pathlib import Path

from tests.fixtures.approved_palettes.reference import gradient
from tests.fixtures.chart_controls.generate_bragg import published_palettes

OWNER = json.loads(Path(__file__).with_name('owner.json').read_text())
SCHEMES = ['main', 'colourBlindSafe']
PALETTES = [
    {**palette, 'scheme': scheme, 'default': index == 0}
    for index, (palette, scheme) in enumerate(zip(published_palettes(), SCHEMES, strict=True))
]


def role_colours(theme, palette=None):
    """Curve roles from the immutable published approval, per active palette."""
    chosen = PALETTES[0] if palette is None else palette
    return {role: values[theme] for role, values in chosen['roles'].items()}


def assigned_structure(palette, place, experiments, structures, theme):
    """Both active palettes reserve two experiment colours before structure colours."""
    first = max(experiments, 2)
    position, size = first + place, first + structures
    colours = palette[theme]
    if position < 11:
        return colours[position]
    return gradient(colours[0], colours[1], (position - 10) / (size - 10))
