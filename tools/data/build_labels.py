#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-3-Clause
"""Fill the app's label registry, app/data/labels.tsv, from crysta's dictionary and the QML.

Every label the app shows has one row: its key, its long form, a short form for a narrow place
and a Font Awesome icon, the last two empty where there is none (edi ADR-0104).
The rows this script can derive:

- every item of crysta's dictionary, by its uid (`cell.length_a`), its variants (`uid@token`), its
  options (`uid=token`) and every category (`atom_site`): the long form is the name the app shows
  for it (`Session.label`, `Session.optionLabel`, `Session.categoryTitle`), an item's icon the
  parameter icon the Analysis table draws for its name, a category's icon its dictionary icon;
- every QML control with a literal `objectName` and a literal text or title (tabs, toolbars,
  group titles): the key is the objectName;
- every table header written as a literal text with no objectName: `header.<text>`.

Short forms and icons entered by hand are kept, and so is a row the sources no longer give when it
holds one. Labels whose text is not a literal are listed as not filled.

    python tools/data/build_labels.py [--crysta <crysta source>] [--check]

The dictionary is read from --crysta, else CRYSTA_CONSUMER_SRC, else build/crysta-src, as
tools/checks/display_glyphs.py reads it. --check writes nothing and fails when the file differs
from what the sources give.
"""

from __future__ import annotations

import argparse
import os
import re
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
REGISTRY = ROOT / 'app/data/labels.tsv'
QML = ROOT / 'app/qml'
APP_INFO = ROOT / 'app/src/app_info.cpp'
DICTIONARY = 'data/dictionary/parameters.yaml'
COLUMNS = ('key', 'long', 'short', 'icon')

# The one item whose shown name is not its dictionary name (core/src/display.cpp, shown_label).
SHOWN_LABELS = {'fit_result_bank.chi_square': 'χ²'}
QSTR = re.compile(r'^qsTr\("((?:[^"\\]|\\.)*)"\)$')
STRING = re.compile(r'^"((?:[^"\\]|\\.)*)"$')
# A text that picks its long or short form itself, by the room its row has:
# `buttons.wholeLabels ? qsTr("Create structure") : qsTr("Create")`.
CHOICE = re.compile(
    r'^[^?]*wholeLabels[^?]*\?\s*qsTr\("((?:[^"\\]|\\.)*)"\)\s*:\s*qsTr\("((?:[^"\\]|\\.)*)"\)$'
)
# A text from the dictionary, which has its own rows.
FROM_DICTIONARY = re.compile(
    r'^Session\.(label|categoryTitle|optionLabel)\("[^"]*"(, *"[^"]*")?\)$'
)


def label_case(name: str) -> str:
    """A dictionary name as a label, as app/src/label_case.hpp writes it."""
    end = 0
    while end < len(name) and name[end] not in ' (':
        end += 1
    word = name[:end]
    if word == 'id':
        return 'ID' + name[end:]
    if len(word) < 2 or word == 'sin':
        return name
    if any(not ('a' <= c <= 'z') and c not in '-/' for c in word):
        return name
    return name[:1].upper() + name[1:]


def crysta_source(named: str | None) -> Path:
    if named:
        return Path(named)
    env = os.environ.get('CRYSTA_CONSUMER_SRC')
    return Path(env) if env else ROOT / 'build/crysta-src'


def parameter_icons() -> list[tuple[str, str]]:
    """The Analysis table's parameter icons by name prefix (ApplicationInfo::nameParameterIcon)."""
    text = APP_INFO.read_text(encoding='utf-8')
    start = text.index('ApplicationInfo::nameParameterIcon')
    table = text[start : text.index('};', start)]
    return re.findall(r'\{"([a-z0-9_]+)", "([a-z0-9-]+)"\}', table)


def icon_for(name: str, icons: list[tuple[str, str]]) -> str:
    return next((icon for prefix, icon in icons if name.startswith(prefix)), '')


def dictionary_rows(source: Path) -> dict[str, tuple[str, str, str]]:
    """Each dictionary key's long form, short form (none) and icon."""
    path = source / DICTIONARY
    try:
        data = yaml.safe_load(path.read_text(encoding='utf-8'))
    except (OSError, yaml.YAMLError) as error:
        sys.exit(f"build_labels: cannot read crysta's dictionary at {path}: {error}")
    icons = parameter_icons()
    rows: dict[str, tuple[str, str, str]] = {}
    for category in data.get('categories') or []:
        title = category.get('loop_title') if category.get('loop') else category.get('title')
        rows[category['id']] = (title or '', '', category.get('icon') or '')
    for entry in list(data.get('parameters') or []) + list(data.get('items') or []):
        uid = entry['uid']
        icon = icon_for(entry.get('name') or '', icons)
        shown = SHOWN_LABELS.get(uid, entry.get('display_name') or '')
        rows[uid] = (label_case(shown), '', icon)
        for token, variant in (entry.get('variants') or {}).items():
            if isinstance(variant, dict):
                # A variant without a name of its own (only its units differ) keeps the item's.
                named = variant.get('display_name') or shown
                rows[f'{uid}@{token}'] = (label_case(named), '', icon)
        for option in entry.get('options') or []:
            rows[f'{uid}={option["token"]}'] = (option.get('display_name') or '', '', '')
    return rows


def strip_comments(text: str) -> str:
    """The QML without its comments, strings kept, so a brace in a comment is not counted."""
    out, i = [], 0
    while i < len(text):
        if text.startswith('//', i):
            i = text.find('\n', i) if '\n' in text[i:] else len(text)
        elif text.startswith('/*', i):
            end = text.find('*/', i + 2)
            i = len(text) if end < 0 else end + 2
        elif text[i] in '"\'`':
            quote, j = text[i], i + 1
            while j < len(text) and text[j] != quote:
                j += 2 if text[j] == '\\' else 1
            out.append(text[i : j + 1])
            i = j + 1
        else:
            out.append(text[i])
            i += 1
    return ''.join(out)


def objects(text: str) -> list[tuple[str, str, int, list[str]]]:
    """Each `Type {...}` block's type, own lines (nested blocks removed), offset and parents."""
    found, stack, own = [], [], []
    i = 0
    while i < len(text):
        c = text[i]
        if c in '"\'`':
            j = i + 1
            while j < len(text) and text[j] != c:
                j += 2 if text[j] == '\\' else 1
            if own:
                own[-1].append(text[i : j + 1])
            i = j + 1
            continue
        if c == '{':
            head = re.search(r'([A-Za-z_][\w.]*)\s*$', text[max(0, i - 80) : i])
            stack.append((head[1] if head else '', i))
            own.append([])
        elif c == '}' and stack:
            kind, start = stack.pop()
            found.append((kind, ''.join(own.pop()), start, [k for k, _ in stack]))
        elif own:
            own[-1].append(c)
        i += 1
    return found


def literal(value: str) -> str | None:
    value = value.strip()
    match = QSTR.match(value) or STRING.match(value)
    return match[1].replace('\\"', '"') if match else None


def prop(body: str, name: str) -> str | None:
    match = re.search(rf'(?m)^\s*{name}:\s*(.+?)\s*$', body)
    return match[1] if match else None


def slug(text: str) -> str:
    return re.sub(r'\W+', '_', text.lower()).strip('_')


def qml_rows() -> tuple[dict[str, tuple[str, str, str]], list[str]]:
    """The QML's literal labels by key, and the labels it shows that are not literals."""
    rows: dict[str, tuple[str, str, str]] = {}
    unfilled: list[str] = []
    for path in sorted(QML.rglob('*.qml')):
        if 'Base' in path.relative_to(QML).parts:
            continue
        relative = path.relative_to(ROOT).as_posix()
        text = strip_comments(path.read_text(encoding='utf-8'))
        for kind, body, start, parents in objects(text):
            line = text.count('\n', 0, start) + 1
            name = literal(prop(body, 'objectName') or '')
            shown = prop(body, 'text') or prop(body, 'title')
            header = kind.endswith('ListViewLabel') and any(
                p.endswith('ListViewHeader') for p in parents
            )
            # An icon drawn as text is not a label.
            if shown is None or (name is None and not header) or 'iconsFamily' in body:
                continue
            value, short = literal(shown), ''
            choice = CHOICE.match(shown)
            if choice:
                value, short = sorted(choice.groups(), key=len, reverse=True)
            if value is None:
                if not FROM_DICTIONARY.match(shown):
                    unfilled.append(f'{relative}:{line}: {shown}')
                continue
            if not value:
                continue
            icon = literal(prop(body, 'fontIcon') or prop(body, 'icon') or '') or ''
            key = name or f'header.{slug(value)}'
            rows.setdefault(key, (value, short, icon))
    return rows, unfilled


def read_registry() -> dict[str, list[str]]:
    if not REGISTRY.exists():
        return {}
    lines = REGISTRY.read_text(encoding='utf-8').splitlines()
    return {cells[0]: cells for cells in (line.split('\t') for line in lines[1:]) if cells}


def build(source: Path) -> tuple[str, list[str], int]:
    """The registry's text, the labels not filled and the number of rows kept by hand."""
    old = read_registry()
    found, unfilled = qml_rows()
    found.update(dictionary_rows(source))
    rows = []
    # A row the sources no longer give stays only when it holds a hand-entered short form or icon.
    hand = {key for key, cells in old.items() if key not in found and any(cells[2:4])}
    for key in sorted(set(found) | hand):
        before = old.get(key, [key, '', '', ''])
        long, short, icon = found.get(key, (before[1], before[2], before[3]))
        rows.append([key, long, before[2] or short, before[3] or icon])
    kept = len(hand)
    body = ['\t'.join(COLUMNS)] + ['\t'.join(row) for row in rows]
    return '\n'.join(body) + '\n', unfilled, kept


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument('--crysta', help="crysta's source folder")
    parser.add_argument('--check', action='store_true', help='compare, write nothing')
    args = parser.parse_args()
    text, unfilled, kept = build(crysta_source(args.crysta))
    for site in unfilled:
        print(f'not filled (no literal text): {site}')
    rows = text.count('\n') - 1
    if args.check:
        current = REGISTRY.read_text(encoding='utf-8') if REGISTRY.exists() else ''
        if current != text:
            print(f'build_labels: {REGISTRY.relative_to(ROOT)} differs from its sources (run it)')
            return 1
        print(f'build_labels: {rows} rows match their sources, {kept} kept by hand')
        return 0
    REGISTRY.parent.mkdir(parents=True, exist_ok=True)
    REGISTRY.write_text(text, encoding='utf-8')
    print(f'build_labels: {rows} rows written, {kept} kept by hand, {len(unfilled)} not filled')
    return 0


if __name__ == '__main__':
    sys.exit(main())
