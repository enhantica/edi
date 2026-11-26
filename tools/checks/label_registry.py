#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-3-Clause
"""The label registry, app/data/labels.tsv, against the code that shows its labels.

Every visible label has a row of long form, short form and icon (edi ADR-0104).
The check reads the sources only, without running the app:

- the table has four columns, one row per key and a long form in every row;
- every key a label call names as a literal has a row: `Session.labelForms`, `Session.label`,
  `Session.categoryTitle` and `Session.optionLabel` in the QML and C++, a header's `uid`, an
  `AdaptiveLabel`'s `key` and `find_label_forms` in the C++;
- no short form is longer than its long form;
- every icon is a glyph of the icon font the app draws with (Font Awesome 5 Free Solid, the base's
  font in the app's build). Without the build the font is absent and the icons are not checked,
  which the check says.

And it finds raw names, an item's `snake_case` name shown where words belong:

- no long or short form is one;
- every value a scan's results hold without a parameter of its own (the derived columns of
  `scan_derived_column`, core/src/adapter.cpp: a moment's spherical form, a weight fraction) has a
  row, so the Evolution selector names it in words;
- every place in the app that takes the last part of a dotted name looks it up in the registry
  within a few lines, unless the part it shows is no item name (listed below with the reason).

Whether a long form still equals crysta's dictionary is tools/data/build_labels.py --check's.

    python tools/checks/label_registry.py [--font <otf>]
"""

from __future__ import annotations

import argparse
import re
import struct
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
REGISTRY = ROOT / 'app/data/labels.tsv'
COLUMNS = ['key', 'long', 'short', 'icon']
FONT = (
    ROOT / 'build/app/_deps/gui_components-src/src/EasyApplication/Gui/Resources/Fonts'
    '/FontAwesome/Font Awesome 5 Free-Solid-900.otf'
)
SOURCES = [('app/qml', '.qml'), ('app/src', '.cpp'), ('app/src', '.hpp')]
LIT = r'"((?:[^"\\]|\\.)*)"'
CALLS = [
    re.compile(rf'Session\.(?:labelForms|label|categoryTitle)\(\s*{LIT}'),
    re.compile(rf'labelForms\(\s*QStringLiteral\(\s*{LIT}'),
    re.compile(rf'find_label_forms\(\s*QStringLiteral\(\s*{LIT}'),
]
OPTION_CALL = re.compile(rf'Session\.optionLabel\(\s*{LIT}\s*,\s*{LIT}')
# A header's item or a label's key, inside its own block.
LABEL_BLOCK = re.compile(r'\b(HeaderLabel|AdaptiveLabel)\s*\{')
BLOCK_KEY = re.compile(rf'(?m)^\s*(?:uid|key):\s*{LIT}\s*$')
RAW_NAME = re.compile(r'\b[a-z][a-z0-9]*_[a-z0-9_]+\b')
DERIVED = ROOT / 'core/src/adapter.cpp'
# Code taking the last part of a dotted name.
LAST_PART = re.compile(
    r'parts\[parts\.length - 1\]|parts\[last\]|\.split\("\."\)\.pop\(\)'
    r"|\.section\(QLatin1Char\('\.'\), -1\)"
)
LOOKUP = re.compile(r'labelForms|find_label_forms|unlistedName')
# How many lines around such a site the lookup may be: the statement that shows the part.
NEAR = 8
# Sites whose last part is not an item's name, so it is never a raw name on screen.
NOT_ITEMS = {
    'app/qml/Components/ToolbarLines.qml': 'a view button letter, a, b or c, from its objectName',
    'app/qml/Components/TutorialPanel.qml': 'a control found by its objectName, never shown',
    'app/src/demo_driver.cpp': 'controls found by their objectNames, never shown',
    'app/src/toolbar_row.cpp': 'toolbar controls ranked by their objectNames, never shown',
}
# Font Awesome names that are also CFF standard strings, whose glyphs carry no name of their own.
STANDARD_NAMES = {
    'asterisk',
    'at',
    'copyright',
    'minus',
    'percent',
    'plus',
    'question',
    'registered',
}


def read_rows() -> tuple[list[list[str]], list[str]]:
    findings = []
    lines = REGISTRY.read_text(encoding='utf-8').split('\n')
    if lines[0].split('\t') != COLUMNS:
        findings.append(f'labels.tsv: the first line is not {"\t".join(COLUMNS)!r}')
    rows, seen = [], set()
    for number, line in enumerate(lines[1:], start=2):
        if not line:
            continue
        cells = line.split('\t')
        if len(cells) != len(COLUMNS):
            findings.append(f'labels.tsv:{number}: {len(cells)} cells, not {len(COLUMNS)}')
            continue
        if cells[0] in seen:
            findings.append(f'labels.tsv:{number}: {cells[0]!r} has a second row')
        if not cells[1]:
            findings.append(f'labels.tsv:{number}: {cells[0]!r} has no long form')
        seen.add(cells[0])
        rows.append(cells)
    return rows, findings


def block(text: str, start: int) -> str:
    depth, i = 0, text.index('{', start)
    for j in range(i, len(text)):
        depth += {'{': 1, '}': -1}.get(text[j], 0)
        if depth == 0:
            return text[i : j + 1]
    return text[i:]


def used_keys() -> dict[str, str]:
    """Every literal key a label call names, with its first site."""
    used: dict[str, str] = {}
    for folder, suffix in SOURCES:
        for path in sorted((ROOT / folder).rglob(f'*{suffix}')):
            relative = path.relative_to(ROOT).as_posix()
            text = path.read_text(encoding='utf-8')
            sites = [(m[1], m.start()) for call in CALLS for m in call.finditer(text)]
            sites += [(f'{m[1]}={m[2]}', m.start()) for m in OPTION_CALL.finditer(text)]
            if suffix == '.qml':
                for match in LABEL_BLOCK.finditer(text):
                    own = re.sub(r'\{[^{}]*\}', '', block(text, match.start())[1:-1])
                    sites += [(m[1], match.start()) for m in BLOCK_KEY.finditer(own)]
            for key, at in sites:
                used.setdefault(key, f'{relative}:{text.count(chr(10), 0, at) + 1}')
    return used


def raw_names(rows: list[list[str]]) -> list[str]:
    """Where a raw item name could show: a form, a derived column, a last part shown as it is."""
    findings = [
        f'labels.tsv: {key!r} has the raw name {match[0]!r} in a form'
        for key, long, short, _ in rows
        for match in RAW_NAME.finditer(f'{long} {short}')
    ]
    items = {key.split('=')[0].split('@')[0].rpartition('.')[2] for key, *_ in rows}
    text = DERIVED.read_text(encoding='utf-8')
    body = text[text.index('bool scan_derived_column') :]
    suffixes = re.findall(r'"\.([a-z0-9_]+)"', body[: body.index('return false')])
    if not suffixes:
        findings.append(
            f'{DERIVED.relative_to(ROOT)}: no derived columns found in scan_derived_column'
        )
    findings += [
        f'{DERIVED.relative_to(ROOT)}: the derived column {suffix!r} has no row in labels.tsv'
        for suffix in suffixes
        if suffix not in items
    ]
    for folder, suffix in SOURCES:
        for path in sorted((ROOT / folder).rglob(f'*{suffix}')):
            relative = path.relative_to(ROOT).as_posix()
            if relative in NOT_ITEMS:
                continue
            lines = path.read_text(encoding='utf-8').splitlines()
            findings += [
                f'{relative}:{number}: shows the last part of a name without the label registry'
                for number, line in enumerate(lines, start=1)
                if LAST_PART.search(line)
                and not any(
                    LOOKUP.search(near)
                    for near in lines[max(0, number - 1 - NEAR) : number + NEAR]
                )
            ]
    return findings


def index(data: bytes, at: int) -> tuple[list[bytes], int]:
    """A CFF INDEX's entries and the offset after it."""
    (count,) = struct.unpack_from('>H', data, at)
    if count == 0:
        return [], at + 2
    size = data[at + 2]
    offsets = [
        int.from_bytes(data[at + 3 + i * size : at + 3 + (i + 1) * size], 'big')
        for i in range(count + 1)
    ]
    base = at + 2 + (count + 1) * size
    entries = [data[base + offsets[i] : base + offsets[i + 1]] for i in range(count)]
    return entries, base + offsets[-1]


def top_dict(data: bytes) -> dict[int, list[int]]:
    """A CFF Top DICT's integer operands by operator (reals are skipped)."""
    out, operands, i = {}, [], 0
    while i < len(data):
        b = data[i]
        if b <= 21:
            op = 1200 + data[i + 1] if b == 12 else b
            i += 2 if b == 12 else 1
            out[op], operands = operands, []
        elif b == 28:
            operands.append(struct.unpack_from('>h', data, i + 1)[0])
            i += 3
        elif b == 29:
            operands.append(struct.unpack_from('>i', data, i + 1)[0])
            i += 5
        elif b == 30:
            i += 1
            while not (data[i] & 0x0F == 0x0F or data[i] >> 4 == 0x0F):
                i += 1
            i += 1
        elif b <= 246:
            operands.append(b - 139)
            i += 1
        elif b <= 250:
            operands.append((b - 247) * 256 + data[i + 1] + 108)
            i += 2
        else:
            operands.append(-(b - 251) * 256 - data[i + 1] - 108)
            i += 2
    return out


def charset(font: bytes, at: int, glyphs: int) -> list[int]:
    """The string ids of glyphs 1 to `glyphs` - 1 from a CFF charset (formats 0, 1 and 2)."""
    sids: list[int] = []
    if at <= 2:
        return sids
    fmt, at = font[at], at + 1
    while len(sids) < glyphs - 1:
        if fmt == 0:
            sids.append(struct.unpack_from('>H', font, at)[0])
            at += 2
            continue
        first = struct.unpack_from('>H', font, at)[0]
        left = font[at + 2] if fmt == 1 else struct.unpack_from('>H', font, at + 2)[0]
        at += 3 if fmt == 1 else 4
        sids += range(first, first + left + 1)
    return sids


def glyph_names(path: Path) -> set[str]:
    """The glyph names of an OpenType CFF font: Font Awesome names each glyph by its icon."""
    data = path.read_bytes()
    (tables,) = struct.unpack_from('>H', data, 4)
    cff = next(
        struct.unpack_from('>I', data, 12 + 16 * i + 8)[0]
        for i in range(tables)
        if data[12 + 16 * i : 16 + 16 * i] == b'CFF '
    )
    font = data[cff:]
    _, after_names = index(font, font[2])
    dicts, after_dicts = index(font, after_names)
    strings, _ = index(font, after_dicts)
    top = top_dict(dicts[0])
    sids = charset(font, top.get(15, [0])[0], len(index(font, top[17][0])[0]))
    custom = [sid - 391 for sid in sids if 391 <= sid < 391 + len(strings)]
    names = {strings[sid].decode('latin-1') for sid in custom}
    if any(sid < 391 for sid in sids):
        names |= STANDARD_NAMES
    return names


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument('--font', type=Path, default=FONT, help='the icon font')
    args = parser.parse_args()
    rows, findings = read_rows()
    keys = {row[0] for row in rows}
    findings += [
        f'{site}: {key!r} has no row in labels.tsv'
        for key, site in sorted(used_keys().items())
        if key not in keys
    ]
    findings += [
        f'labels.tsv: {key!r} has a short form {short!r} longer than its long form {long!r}'
        for key, long, short, _ in rows
        if len(short) > len(long)
    ]
    findings += raw_names(rows)
    icons = {row[3] for row in rows if row[3]}
    if args.font.exists():
        known = glyph_names(args.font)
        findings += [
            f'labels.tsv: the icon {icon!r} is not in {args.font.name}'
            for icon in sorted(icons - known)
        ]
        checked = f'{len(icons)} icons'
    else:
        checked = f'icons not checked ({args.font.name} not found: build the app first)'
    for finding in findings:
        print(finding)
    print(f'label_registry: {len(rows)} rows, {len(findings)} problems; {checked}')
    return 1 if findings else 0


if __name__ == '__main__':
    sys.exit(main())
