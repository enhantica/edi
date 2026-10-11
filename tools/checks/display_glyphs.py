#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-3-Clause
"""Every non-ASCII character the app can display, and the bundled font that draws it.

The app draws text in PT Sans (the base's default font), with the bundled Noto Sans substituted
for the characters PT Sans lacks (the Greek letters, the subscripts; see engine_setup.cpp), and
icons in Font Awesome. A character no bundled font of that chain has sends Qt to the system's
fonts; on macOS that search goes through FreeType and logs "Failed to create FreeType font
engine". So every non-ASCII character in a string the app may show must be in a bundled font
that draws it, or its site must name such a font (the Wyckoff list is drawn in Noto Sans).

The census reads the string literals of the app's QML and C++ and of the core (whose messages
and units the app shows), with their escapes decoded. For each character it records where it is
used, the font chain that draws it and the font of that chain that has it. --write regenerates
data/display-glyphs.json from the sources and the fonts. --check scans the sources again and
fails when a character or a site is not in the census, or when a character is in no font of its
chain. The fonts are read when present (the base's come with the app's build); without them the
check compares the sources with the census only, and says so.
"""

from __future__ import annotations

import argparse
import json
import re
import struct
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CENSUS = ROOT / 'data' / 'display-glyphs.json'
SOURCES = [
    ('app/qml', ('.qml', '.js')),
    ('app/src', ('.cpp', '.hpp')),
    ('core/src', ('.cpp', '.hpp')),
    ('core/include', ('.hpp',)),
]
BASE_FONTS = ROOT / 'build/app/_deps/gui_components-src/src/EasyApplication/Gui/Resources/Fonts'
FONTS = {
    'PT Sans': [
        BASE_FONTS / 'PT_Sans/PTSans-Regular.ttf',
        BASE_FONTS / 'PT_Sans/PTSans-Bold.ttf',
    ],
    'Noto Sans': [ROOT / 'app/resources/fonts/Noto_Sans/NotoSans-Regular.ttf'],
    'Encode Sans': [BASE_FONTS / 'Encode_Sans/EncodeSans-Regular.ttf'],
    'Font Awesome': [BASE_FONTS / 'FontAwesome/Font Awesome 5 Free-Solid-900.otf'],
}
# The fonts Qt tries in turn for a text in each family; Noto Sans is substituted behind PT Sans.
CHAINS = {
    'PT Sans': ['PT Sans', 'Noto Sans'],
    'Noto Sans': ['Noto Sans'],
    'Encode Sans': ['Encode Sans'],
    'Font Awesome': ['Font Awesome'],
}
# The sites drawn in another family than PT Sans: a path, or a path and one character in it.
SITE_FONTS = {
    # The Wyckoff list, drawn in Noto Sans (AtomSitesGroup).
    'app/src/structure_view_model.cpp': 'Noto Sans',
    # The fit's change arrow, split out of the status text and drawn by its own Text.
    ('app/qml/Components/StatusBar.qml', '→'): 'Encode Sans',
    ('app/src/fit_view_model.cpp', '→'): 'Encode Sans',
}
# The sources whose strings never reach the app's pages: the terminal report and progress line.
NOT_SHOWN = {'core/src/report.cpp'}

LITERAL = re.compile(r'"(?:[^"\\\n]|\\.)*"' + r"|'(?:[^'\\\n]|\\.)*'" + r'|`(?:[^`\\]|\\.)*`')
ESCAPE = re.compile(r'\\u([0-9a-fA-F]{4})|\\U([0-9a-fA-F]{8})')
QCHAR = re.compile(r'QChar\(\s*0x([0-9a-fA-F]+)\s*\)')


def strip_comments(text: str) -> str:
    """The text with // and /* */ comments blanked, string literals kept (lines stay)."""
    out = []
    i = 0
    n = len(text)
    while i < n:
        c = text[i]
        if c in '"\'`':
            match = LITERAL.match(text, i)
            end = match.end() if match else i + 1
            out.append(text[i:end])
            i = end
        elif text.startswith('//', i):
            end = text.find('\n', i)
            end = n if end < 0 else end
            out.append(' ' * (end - i))
            i = end
        elif text.startswith('/*', i):
            end = text.find('*/', i + 2)
            end = n if end < 0 else end + 2
            out.append(''.join('\n' if ch == '\n' else ' ' for ch in text[i:end]))
            i = end
        else:
            out.append(c)
            i += 1
    return ''.join(out)


def decoded(literal: str) -> str:
    r"""A literal's characters with its \u and \U escapes decoded."""
    return ESCAPE.sub(lambda m: chr(int(m.group(1) or m.group(2), 16)), literal)


def font_of(relative: str, ch: str) -> str:
    if 0xE000 <= ord(ch) <= 0xF8FF:
        return 'Font Awesome'
    return SITE_FONTS.get((relative, ch), SITE_FONTS.get(relative, 'PT Sans'))


def scan() -> dict[str, dict]:
    """Each non-ASCII displayed character, by its drawing font, with the files using it."""
    found: dict[str, dict] = {}
    for directory, suffixes in SOURCES:
        for path in sorted((ROOT / directory).rglob('*')):
            relative = path.relative_to(ROOT).as_posix()
            if path.suffix not in suffixes or not path.is_file() or relative in NOT_SHOWN:
                continue
            text = strip_comments(path.read_text(encoding='utf-8'))
            for line in text.split('\n'):
                characters = [ch for m in LITERAL.finditer(line) for ch in decoded(m.group(0))]
                characters += [chr(int(m.group(1), 16)) for m in QCHAR.finditer(line)]
                for ch in characters:
                    if ord(ch) < 128:
                        continue
                    font = font_of(relative, ch)
                    code = f'U+{ord(ch):04X}'
                    entry = found.setdefault(
                        f'{code} {font}', {'char': ch, 'code': code, 'font': font, 'sites': []}
                    )
                    site = relative
                    if site not in entry['sites']:
                        entry['sites'].append(site)
    return found


def cmap_format4(data: bytes, start: int) -> set[int]:
    segments = struct.unpack('>H', data[start + 6 : start + 8])[0] // 2

    def array(at: int, kind: str = 'H') -> tuple[int, ...]:
        return struct.unpack(f'>{segments}{kind}', data[at : at + 2 * segments])

    ends = array(start + 14)
    starts = array(start + 16 + 2 * segments)
    deltas = array(start + 16 + 4 * segments, 'h')
    range_base = start + 16 + 6 * segments
    offsets = array(range_base)
    codes = set()
    for s in range(segments):
        for c in range(starts[s], ends[s] + 1):
            if offsets[s] == 0:
                glyph = (c + deltas[s]) & 0xFFFF
            else:
                at = range_base + 2 * s + offsets[s] + 2 * (c - starts[s])
                glyph = struct.unpack('>H', data[at : at + 2])[0]
                glyph = (glyph + deltas[s]) & 0xFFFF if glyph else 0
            if glyph and c != 0xFFFF:
                codes.add(c)
    return codes


def cmap_format12(data: bytes, start: int) -> set[int]:
    codes = set()
    for g in range(struct.unpack('>I', data[start + 12 : start + 16])[0]):
        at = start + 16 + 12 * g
        first, last, glyph = struct.unpack('>III', data[at : at + 12])
        codes.update(c for k, c in enumerate(range(first, last + 1)) if glyph + k != 0)
    return codes


def cmap_codepoints(path: Path) -> set[int]:
    """The code points a TrueType or OpenType font maps to a glyph (cmap format 12, else 4)."""
    data = path.read_bytes()
    cmap = None
    for i in range(struct.unpack('>H', data[4:6])[0]):
        tag, _, offset, _ = struct.unpack('>4sIII', data[12 + 16 * i : 28 + 16 * i])
        if tag == b'cmap':
            cmap = offset
    if cmap is None:
        raise ValueError(f'{path}: no cmap table')
    formats = {}
    for i in range(struct.unpack('>H', data[cmap + 2 : cmap + 4])[0]):
        offset = struct.unpack('>I', data[cmap + 8 + 8 * i : cmap + 12 + 8 * i])[0]
        start = cmap + offset
        formats.setdefault(struct.unpack('>H', data[start : start + 2])[0], start)
    if 12 in formats:
        return cmap_format12(data, formats[12])
    if 4 in formats:
        return cmap_format4(data, formats[4])
    raise ValueError(f'{path}: no format 4 or 12 cmap')


def coverage() -> dict[str, set[int]] | None:
    """Each font's code points, in every face of it; None when a font file is missing."""
    fonts = {}
    for name, paths in FONTS.items():
        if not all(p.is_file() for p in paths):
            return None
        fonts[name] = set.intersection(*[cmap_codepoints(p) for p in paths])
    return fonts


def drawn_by(ch: str, font: str, fonts: dict[str, set[int]]) -> str | None:
    """The first font of the chain that has the character, or None."""
    return next((name for name in CHAINS[font] if ord(ch) in fonts[name]), None)


def write(found: dict[str, dict], fonts: dict[str, set[int]]) -> int:
    rows = [
        {**found[key], 'drawn_by': drawn_by(found[key]['char'], found[key]['font'], fonts)}
        for key in sorted(found, key=lambda k: (ord(found[k]['char']), found[k]['font']))
    ]
    text = json.dumps({'characters': rows}, indent=1, ensure_ascii=False)
    CENSUS.write_text(text + '\n', encoding='utf-8')
    missing = sum(row['drawn_by'] is None for row in rows)
    print(f'display_glyphs: {len(rows)} characters written, {missing} in no font of their chain')
    return 0


def check(found: dict[str, dict], fonts: dict[str, set[int]] | None) -> int:
    recorded = json.loads(CENSUS.read_text(encoding='utf-8'))['characters']
    by_key = {f'{row["code"]} {row["font"]}': row for row in recorded}
    findings = []
    for key, entry in found.items():
        name = f'{entry["code"]} {entry["char"]!r}'
        row = by_key.get(key)
        if row is None:
            findings.append(f'{name} in {entry["font"]} at {entry["sites"][0]} is not recorded')
        elif sorted(row['sites']) != sorted(entry['sites']):
            findings.append(f'{name}: its sites changed (run --write)')
        if row is not None and fonts is not None:
            drawn = drawn_by(entry['char'], entry['font'], fonts)
            if row['drawn_by'] != drawn:
                findings.append(f'{name}: recorded {row["drawn_by"]}, fonts say {drawn}')
    for key, row in by_key.items():
        name = f'{row["code"]} {row["char"]!r}'
        if key not in found:
            findings.append(f'{name} is recorded but no longer in the sources (run --write)')
        if row['drawn_by'] is None:
            findings.append(f'{name} at {row["sites"][0]} in no font of the {row["font"]} chain')
    for finding in findings:
        print(f'display_glyphs: {finding}', file=sys.stderr)
    note = '' if fonts is not None else ' (no fonts: sources compared with the census only)'
    print(f'display_glyphs: {len(found)} characters, {len(findings)} findings{note}')
    return 1 if findings else 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument('--write', action='store_true')
    mode.add_argument('--check', action='store_true')
    args = parser.parse_args()
    found = scan()
    fonts = coverage()
    if args.check:
        return check(found, fonts)
    if fonts is None:
        print('display_glyphs: a bundled font is missing (build the app first)', file=sys.stderr)
        return 1
    return write(found, fonts)


if __name__ == '__main__':
    sys.exit(main())
