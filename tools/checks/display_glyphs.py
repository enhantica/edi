#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-3-Clause
"""Every non-ASCII character the app can display, and the bundled font that draws it.

Every character the app shows comes from a bundled font, at the face it is drawn with; none comes
from the platform (edi ADR-0033). The app draws text in PT Sans and PT Mono, with the bundled Noto
Sans and Noto Sans Mono substituted behind them for the characters they lack (the Greek letters,
the subscripts; see engine_setup.cpp), and icons in Font Awesome Solid. A character no bundled font
of the chain has sends Qt to the system's fonts; on macOS that search goes through FreeType and
logs "Failed to create FreeType font engine". Legend marks are drawn shapes, not characters.

The census reads the string literals of the app's QML and C++ and of the core (whose messages
and units the app shows), with their escapes decoded. For each character it records where it is
used, the font chain that draws it and the font of that chain that has it. --write regenerates
data/display-glyphs.json from the sources and the fonts, failing on a character no font of its
chain has. --check scans the sources again and fails when a character or a site is not in the
census, or when a character is in no font of its chain. Each character's row also records the
weight of the face that draws it. The census lists too the QML TextMetrics and FontMetrics that
measure an icon; each must copy its font from the item drawing the icon, since a font built from
the family alone can resolve a face without the glyph. The fonts are read when present (the
base's come with the app's build); without them the check compares the sources with the census
only, and says so.
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
    'PT Mono': [BASE_FONTS / 'PT_Mono/PTMono-Regular.ttf'],
    'Noto Sans': [ROOT / 'app/resources/fonts/Noto_Sans/NotoSans-Regular.ttf'],
    'Noto Sans Mono': [ROOT / 'app/resources/fonts/Noto_Sans_Mono/NotoSansMono-Regular.ttf'],
    'Encode Sans': [BASE_FONTS / 'Encode_Sans/EncodeSans-Regular.ttf'],
    'Font Awesome': [BASE_FONTS / 'FontAwesome/Font Awesome 5 Free-Solid-900.otf'],
}
# The fonts Qt tries in turn for a text in each family; the Noto fonts are substituted behind PT's.
CHAINS = {
    'PT Sans': ['PT Sans', 'Noto Sans'],
    'PT Mono': ['PT Mono', 'Noto Sans Mono'],
    'Noto Sans': ['Noto Sans'],
    'Encode Sans': ['Encode Sans'],
    'Font Awesome': ['Font Awesome'],
}
# The sites drawn in other families than PT Sans alone: a path, or a path and one character in it.
SITE_FONTS = {
    # The Wyckoff list, drawn in Noto Sans (AtomSitesGroup).
    'app/src/structure_view_model.cpp': ('Noto Sans',),
    # The fit's status, its values drawn in PT Mono and its names and tooltips in PT Sans.
    'app/qml/Components/StatusBar.qml': ('PT Sans', 'PT Mono'),
    'app/qml/Globals/FitOutcomes.qml': ('PT Sans', 'PT Mono'),
    'app/src/fit_view_model.cpp': ('PT Sans', 'PT Mono'),
    # The fit's change arrow, split out of the status text and drawn by its own Text.
    ('app/qml/Components/StatusBar.qml', '\u2192'): ('Encode Sans',),
    ('app/src/fit_view_model.cpp', '\u2192'): ('Encode Sans',),
}
# The sources whose strings never reach the app's pages: the terminal report and progress line.
NOT_SHOWN = {'core/src/report.cpp'}

LITERAL = re.compile(r'"(?:[^"\\\n]|\\.)*"' + r"|'(?:[^'\\\n]|\\.)*'" + r'|`(?:[^`\\]|\\.)*`')
ESCAPE = re.compile(r'\\u([0-9a-fA-F]{4})|\\U([0-9a-fA-F]{8})')
QCHAR = re.compile(r'QChar\(\s*0x([0-9a-fA-F]+)\s*\)')
METRICS = re.compile(r'\b(?:TextMetrics|FontMetrics)\s*\{')
COPIED_FONT = re.compile(r'^\s*font:\s*([\w.]+\.font)\s*$', re.MULTILINE)


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


def fonts_of(relative: str, ch: str) -> tuple[str, ...]:
    if 0xE000 <= ord(ch) <= 0xF8FF:
        return ('Font Awesome',)
    return SITE_FONTS.get((relative, ch), SITE_FONTS.get(relative, ('PT Sans',)))


def scan() -> dict[str, dict]:
    """Each non-ASCII displayed character, by its drawing font, with the files using it."""
    found: dict[str, dict] = {}
    for directory, suffixes in SOURCES:
        for path in sorted((ROOT / directory).rglob('*')):
            relative = path.relative_to(ROOT).as_posix()
            if path.suffix not in suffixes or not path.is_file() or relative in NOT_SHOWN:
                continue
            text = strip_comments(path.read_text(encoding='utf-8'))
            characters = {ch for m in LITERAL.finditer(text) for ch in decoded(m.group(0))}
            characters |= {chr(int(m.group(1), 16)) for m in QCHAR.finditer(text)}
            for ch in sorted(c for c in characters if ord(c) >= 128):
                code = f'U+{ord(ch):04X}'
                for font in fonts_of(relative, ch):
                    entry = found.setdefault(
                        f'{code} {font}', {'char': ch, 'code': code, 'font': font, 'sites': []}
                    )
                    entry['sites'].append(relative)
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


def table(path: Path, data: bytes, name: bytes) -> int:
    """The offset of a font's table."""
    for i in range(struct.unpack('>H', data[4:6])[0]):
        tag, _, offset, _ = struct.unpack('>4sIII', data[12 + 16 * i : 28 + 16 * i])
        if tag == name:
            return offset
    raise ValueError(f'{path}: no {name.decode()} table')


def weight(path: Path) -> int:
    """The face's weight class (OS/2 usWeightClass: 400 regular, 700 bold, 900 black)."""
    data = path.read_bytes()
    os2 = table(path, data, b'OS/2')
    return struct.unpack('>H', data[os2 + 4 : os2 + 6])[0]


def cmap_codepoints(path: Path) -> set[int]:
    """The code points a TrueType or OpenType font maps to a glyph (cmap format 12, else 4)."""
    data = path.read_bytes()
    cmap = table(path, data, b'cmap')
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


def coverage() -> dict[str, dict] | None:
    """Each font's code points (in all its faces) and its first face's weight, or None."""
    fonts = {}
    for name, paths in FONTS.items():
        if not all(p.is_file() for p in paths):
            return None
        codes = set.intersection(*[cmap_codepoints(p) for p in paths])
        fonts[name] = {'codes': codes, 'weight': weight(paths[0])}
    return fonts


def drawn_by(ch: str, font: str, fonts: dict[str, dict]) -> str | None:
    """The first font of the chain that has the character, or None."""
    return next((name for name in CHAINS[font] if ord(ch) in fonts[name]['codes']), None)


def resolved(entry: dict, fonts: dict[str, dict]) -> dict:
    """The font that draws the character and the weight of its face."""
    drawn = drawn_by(entry['char'], entry['font'], fonts)
    return {'drawn_by': drawn, 'weight': fonts[drawn]['weight'] if drawn else None}


def block(text: str, start: int) -> str:
    """The braced QML object starting at the first brace from `start`."""
    depth = 0
    for i in range(text.index('{', start), len(text)):
        depth += {'{': 1, '}': -1}.get(text[i], 0)
        if depth == 0:
            return text[start : i + 1]
    return text[start:]


def icon_metrics() -> list[dict]:
    """The QML TextMetrics and FontMetrics that measure an icon, and where their font comes from.

    An icon is measured in the font it is drawn in, copied from the drawn item (`font: x.font`); a
    font built from the family alone can resolve another face of it, one without the glyph, and the
    platform's fonts are searched (the free column's arrow measure did, on macOS).
    """
    rows = []
    for path in sorted((ROOT / 'app/qml').rglob('*.qml')):
        relative = path.relative_to(ROOT).as_posix()
        text = strip_comments(path.read_text(encoding='utf-8'))
        for match in METRICS.finditer(text):
            body = block(text, match.start())
            icon = 'iconsFamily' in body or any(
                0xE000 <= ord(ch) <= 0xF8FF for m in LITERAL.finditer(body) for ch in decoded(m[0])
            )
            if icon:
                copied = COPIED_FONT.search(body)
                rows.append({'site': relative, 'font': copied[1] if copied else None})
    return rows


def write(found: dict[str, dict], fonts: dict[str, dict]) -> int:
    rows = [
        {**found[key], **resolved(found[key], fonts)}
        for key in sorted(found, key=lambda k: (ord(found[k]['char']), found[k]['font']))
    ]
    metrics = icon_metrics()
    census = {'characters': rows, 'icon_metrics': metrics}
    CENSUS.write_text(json.dumps(census, indent=1, ensure_ascii=False) + '\n', encoding='utf-8')
    missing = sum(row['drawn_by'] is None for row in rows)
    built = sum(row['font'] is None for row in metrics)
    print(
        f'display_glyphs: {len(rows)} characters written, {missing} in no font of their chain;'
        f' {len(metrics)} icon metrics, {built} with a font not copied from the drawn item'
    )
    return 1 if missing or built else 0


def check(found: dict[str, dict], fonts: dict[str, dict] | None) -> int:
    census = json.loads(CENSUS.read_text(encoding='utf-8'))
    by_key = {f'{row["code"]} {row["font"]}': row for row in census['characters']}
    findings = []
    metrics = icon_metrics()
    if metrics != census['icon_metrics']:
        findings.append('the icon metrics changed (run --write)')
    findings += [
        f'{row["site"]}: an icon is measured in a font not copied from the item drawing it'
        for row in metrics
        if row['font'] is None
    ]
    for key, entry in found.items():
        name = f'{entry["code"]} {entry["char"]!r}'
        row = by_key.get(key)
        if row is None:
            findings.append(f'{name} in {entry["font"]} at {entry["sites"][0]} is not recorded')
        elif sorted(row['sites']) != sorted(entry['sites']):
            findings.append(f'{name}: its sites changed (run --write)')
        if row is not None and fonts is not None:
            now = resolved(entry, fonts)
            if (row['drawn_by'], row['weight']) != (now['drawn_by'], now['weight']):
                findings.append(f'{name}: recorded {row["drawn_by"]}, fonts say {now["drawn_by"]}')
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
