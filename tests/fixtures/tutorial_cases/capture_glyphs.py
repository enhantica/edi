"""Author glyph fingerprints directly from the pinned shared font, never from generated SVGs."""

import hashlib
import json
import re
from pathlib import Path

from fontTools.pens.svgPathPen import SVGPathPen
from fontTools.pens.transformPen import TransformPen
from fontTools.ttLib import TTFont

from tests.fixtures.tutorial_cases.presentation import path_digest

ROOT = Path(__file__).resolve().parents[3]


def main():
    path = ROOT / 'website/surfaces/docs/assets/gui-icons/fontawesome-5-solid.otf'
    font = TTFont(path)
    glyph_set = font.getGlyphSet()
    registry = json.loads((ROOT / 'app/examples/tags.json').read_text())['tags']

    def reference(name):
        pen = SVGPathPen(glyph_set)
        glyph_set[name].draw(TransformPen(pen, (1, 0, 0, -1, 0, font['hhea'].ascent)))
        return {
            'path_sha256': path_digest([pen.getCommands()]),
            'viewBox': [0, 0, font['hmtx'][name][0], font['head'].unitsPerEm],
        }

    glyphs = {}
    for values in registry.values():
        for tag in values.values():
            if not tag['glyph']:
                continue
            codepoint = ord(tag['glyph'])
            name = font.getBestCmap()[codepoint]
            glyphs[str(codepoint)] = reference(name)
    toolbar = '\n'.join(
        (ROOT / 'app/qml/Components' / name).read_text()
        for name in ['ChartToolbar.qml', 'StructureToolbar.qml']
    )
    toolbar_names = sorted(
        set(re.findall(r'fontIcon:\s*"([^"]+)"', toolbar)) | {'camera', 'magnet'}
    )
    Path(__file__).with_name('glyphs.json').write_text(
        json.dumps(
            {
                'source': (
                    'Font Awesome Free Solid 5.15.4, shared app/site font; '
                    'glyph outlines are the reference, not a regression capture'
                ),
                'font_sha256': hashlib.sha256(path.read_bytes()).hexdigest(),
                'glyphs': glyphs,
                'toolbar': {name: reference(name) for name in toolbar_names},
            },
            indent=2,
        )
        + '\n'
    )


if __name__ == '__main__':
    main()
