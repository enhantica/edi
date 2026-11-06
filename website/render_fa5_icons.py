#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-3-Clause
"""Extract the site's interface symbols from the Font Awesome 5 font as SVG icons.

Needs fontTools, which the site build does not, so the SVG files are committed. To add a
symbol, add its name here and run this script with any Python that has fontTools.
See adrs/0014-font-awesome-icons.md.
"""

from __future__ import annotations

import json
from pathlib import Path

from fontTools.pens.svgPathPen import SVGPathPen
from fontTools.pens.transformPen import TransformPen
from fontTools.ttLib import TTFont

ROOT = Path(__file__).resolve().parent
ASSETS = ROOT / 'surfaces/docs/assets/gui-icons'
OUTPUT = ROOT / 'surfaces/overrides/.icons/fa5'
NAMES = [
    'archive',
    'book',
    'book-open',
    'calculator',
    'chart-area',
    'chart-line',
    'clipboard-check',
    'clipboard-list',
    'columns',
    'desktop',
    'download',
    'exchange-alt',
    'file-code',
    'filter',
    'globe',
    'home',
    'layer-group',
    'lightbulb',
    'microscope',
    'robot',
    'route',
    'sliders-h',
    'terminal',
    'times-circle',
    'window-maximize',
    'window-minimize',
]
# The font's em box runs from -64 to 448, so this places the baseline as the official SVGs do.
ASCENT = 448
EM = 512
NOTICE = '<!-- Font Awesome Free 5.15.4 by @fontawesome, https://fontawesome.com, CC BY 4.0 -->'


def main() -> None:
    glyphs = json.loads((ASSETS / 'glyphs.json').read_text())
    font = TTFont(ASSETS / 'fontawesome-5-solid.otf')
    cmap = font.getBestCmap()
    glyph_set = font.getGlyphSet()
    OUTPUT.mkdir(parents=True, exist_ok=True)
    for stale in OUTPUT.glob('*.svg'):
        stale.unlink()
    for name in NAMES:
        glyph = glyph_set[cmap[glyphs[name]]]
        pen = SVGPathPen(glyph_set)
        glyph.draw(TransformPen(pen, (1, 0, 0, -1, 0, ASCENT)))
        (OUTPUT / f'{name}.svg').write_text(
            f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {glyph.width} {EM}">{NOTICE}'
            f'<path d="{pen.getCommands()}"/></svg>\n'
        )


if __name__ == '__main__':
    main()
