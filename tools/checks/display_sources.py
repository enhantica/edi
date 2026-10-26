#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-3-Clause
"""Every number and name the app, the report and Python show comes from crysta's dictionary.

The core's display bridge (core/src/display.cpp) is the one place that rounds a number for display
or names an item. This check reads the app's QML and C++, the core and edi's Python library and
fails on:

* a rounding primitive anywhere else: toFixed, toPrecision, toExponential, toDefaultPrecision,
  toSinglePrecision, toErrSinglePrecision, QString::number with an 'f', 'g' or 'e' format,
  setprecision, std::to_chars with a format, a precision in a std::format, printf or Python
  format spec, round(x, n), or fixed_text (the bridge's fixed decimals, whose count is the
  caller's), unless
  data/display-format-exceptions.json names its file, the text on its line and why it is not a
  displayed value of an item (chart ticks, durations, file writers);
* an exception that matches nothing any more;
* a qsTr literal, or a QML text, title or tooltip given as a bare string, equal to a dictionary
  display string (a category title, an item label or units, an option name), a .edi name or a
  selector token, and a C++ string literal equal to a display
  string a user would read as one (one with a capital, a space or a non-ASCII character), so no
  surface keeps a copy of a name; the same file's "names" exceptions admit a literal that names
  something else (a page, a preference) and says so.

The dictionary is read from crysta's source: CRYSTA_CONSUMER_SRC when set, else the pinned fetch
in build/crysta-src.

    python tools/checks/display_sources.py [--root DIR]
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path

import yaml

HERE = Path(__file__).resolve().parent
EXCEPTIONS = Path('data/display-format-exceptions.json')
BRIDGE = 'core/src/display.cpp'
SURFACES = (
    ('app', ('.qml', '.cpp', '.hpp', '.js')),
    ('core', ('.cpp', '.hpp')),
    ('lib/edi', ('.py',)),
    ('lib/src', ('.cpp', '.hpp')),
    # The exported HTML report's renderer, which draws the charts the core hands it.
    ('data/report', ('.js',)),
)

ROUNDING = {
    '.qml': [
        r'\.(toFixed|toPrecision|toExponential)\s*\(',
        r'\b(toDefaultPrecision|toSinglePrecision|toErrSinglePrecision)\b',
    ],
    '.js': [
        r'\.(toFixed|toPrecision|toExponential)\s*\(',
        r'\b(toDefaultPrecision|toSinglePrecision|toErrSinglePrecision)\b',
        # Plotly's own number formats: a hover template's `%{y:.3f}` and an axis's tickformat.
        r'%\{[^}]*:[^}]*\.\d',
        r'\b(?:tick|hover)format\s*:\s*[\'"][^\'"]*\.\d',
    ],
    '.cpp': [
        r"QString::number\([^;]*,\s*'[fgeFGE]'",
        r'\bsetprecision\s*\(',
        r'std::format\s*\(\s*"[^"]*\{[^}"]*\.\d',
        r'printf\s*\([^;]*"[^"]*%[-+ #0]*\d*\.\d+[fgeFGE]',
        r'\bto_chars\s*\([^;]*chars_format::',
        r'\bfixed_text\s*\(',
    ],
    '.py': [
        r'\{[^{}\'"]*:[^{}\'"]*\.\d+[fFeEgG%]?\}',
        r'%[-+ #0]*\d*\.\d+[fFeEgG]',
        r'\bround\(\s*[^,()]+(\([^()]*\))?\s*,\s*\d+\s*\)',
    ],
}
ROUNDING['.hpp'] = ROUNDING['.cpp']

QSTR = re.compile(r'qsTr\(\s*"((?:[^"\\]|\\.)*)"')
# A QML text, title or tooltip given as a bare string literal, not through qsTr or the bridge.
QML_TEXT = re.compile(r'\b(?:text|title|toolTip|placeholderText)\s*:\s*"((?:[^"\\]|\\.)*)"')
CPP_STRING = re.compile(r'"((?:[^"\\\n]|\\.)*)"')
# A JavaScript string literal in either quote.
JS_STRING = re.compile(r"'((?:[^'\\\n]|\\.)*)'|\"((?:[^\"\\\n]|\\.)*)\"")


def code_of(line: str) -> str:
    """A line without its trailing // comment (one outside a string literal)."""
    quoted = False
    for index, char in enumerate(line):
        if char == '"' and (index == 0 or line[index - 1] != '\\'):
            quoted = not quoted
        elif not quoted and line.startswith('//', index):
            return line[:index]
    return line


def crysta_source(root: Path) -> Path:
    """The crysta source whose dictionary the app links."""
    named = os.environ.get('CRYSTA_CONSUMER_SRC')
    return Path(named) if named else root / 'build/crysta-src'


def dictionary_strings(source: Path) -> tuple[set[str], set[str]]:
    """The dictionary's display strings, and its .edi names and selector tokens.

    An item's label with its units in brackets, `d (Å)`, as a column or axis title spells them, is
    a display string too: a surface that writes it keeps a copy of both.
    """
    path = source / 'data/dictionary/parameters.yaml'
    data = yaml.safe_load(path.read_text(encoding='utf-8'))
    display: set[str] = set()
    names: set[str] = set()
    for category in data.get('categories') or []:
        display.update(filter(None, (category.get('title'), category.get('loop_title'))))
    for entry in list(data.get('parameters') or []) + list(data.get('items') or []):
        display.update(filter(None, (entry.get('display_name'), entry.get('display_units'))))
        if entry.get('display_name') and entry.get('display_units'):
            display.add(f'{entry["display_name"]} ({entry["display_units"]})')
        names.update(entry.get('edi_names') or [])
        # A variant's label and units (an ADP's by its site type, the first wavelength by a
        # doublet) are the dictionary's display strings too.
        for variant in (entry.get('variants') or {}).values():
            if isinstance(variant, dict):
                shown = (variant.get('display_name'), variant.get('display_units'))
                display.update(filter(None, shown))
        for option in entry.get('options') or []:
            display.update(filter(None, [option.get('display_name')]))
            names.update(filter(None, [option.get('token')]))
    return display, names


def distinctive(text: str) -> bool:
    """A display string a user reads as a name, not a key a program also spells."""
    return len(text) > 1 and (any(c.isupper() or c == ' ' or ord(c) > 127 for c in text))


def surface_files(root: Path) -> list[Path]:
    """Every source of a surface, the bridge itself left out."""
    return [
        path
        for folder, suffixes in SURFACES
        for path in sorted((root / folder).rglob('*'))
        if path.suffix in suffixes
        and path.is_file()
        and path.relative_to(root).as_posix() != BRIDGE
        and 'vendor' not in path.relative_to(root).parts  # third-party libraries the report ships
    ]


def rounding_sites(root: Path) -> list[tuple[str, int, str]]:
    """Every line with a rounding primitive: file, line number and the line."""
    sites = []
    for path in surface_files(root):
        patterns = [re.compile(p) for p in ROUNDING.get(path.suffix, [])]
        rel = path.relative_to(root).as_posix()
        lines = path.read_text(encoding='utf-8', errors='replace').splitlines()
        for number, line in enumerate(lines, 1):
            if line.lstrip().startswith(('//', '#', '*')):
                continue
            if any(p.search(line) for p in patterns):
                sites.append((rel, number, line.strip()))
    return sites


def copied_names(root: Path, display: set[str], names: set[str]) -> list[tuple[str, int, str]]:
    """Every literal that copies a dictionary name instead of asking the bridge."""
    found = []
    readable = {text for text in display if distinctive(text)}
    for path in surface_files(root):
        rel = path.relative_to(root).as_posix()
        text = path.read_text(encoding='utf-8', errors='replace')
        for number, raw in enumerate(text.splitlines(), 1):
            if raw.lstrip().startswith(('//', '#', '*')):
                continue
            line = code_of(raw) if path.suffix != '.py' else raw
            literals = QSTR.findall(line)
            if path.suffix == '.qml':
                literals += QML_TEXT.findall(line)
            found.extend(
                (rel, number, literal)
                for literal in literals
                if literal in display or literal in names
            )
            if path.suffix in {'.cpp', '.hpp'} and 'qsTr(' not in line:
                found.extend(
                    (rel, number, literal)
                    for literal in CPP_STRING.findall(line)
                    if literal in readable
                )
            if path.suffix == '.js' and 'qsTr(' not in line:
                found.extend(
                    (rel, number, literal)
                    for pair in JS_STRING.findall(line)
                    for literal in pair
                    if literal in readable
                )
    return found


def rounding_findings(root: Path, exceptions: list[dict]) -> list[str]:
    """Each rounding outside the bridge no exception admits; each exception unreasoned, unused."""
    found = []
    used = [False] * len(exceptions)
    for rel, number, line in rounding_sites(root):
        matched = False
        for index, exception in enumerate(exceptions):
            if exception['file'] == rel and exception['match'] in line:
                used[index] = matched = True
        if not matched:
            found.append(f'{rel}:{number}: rounds a number outside the display bridge: {line}')
    for index, exception in enumerate(exceptions):
        where = f'{EXCEPTIONS}: the exception {exception["match"]!r} in {exception["file"]}'
        if not exception.get('reason'):
            found.append(f'{where} gives no reason')
        if not used[index]:
            found.append(f'{where} is stale')
    return found


def name_findings(
    root: Path, display: set[str], names: set[str], admitted: list[dict]
) -> list[str]:
    """Each copied name no exception admits, and each admitted name without a reason or a use."""
    found = []
    named = [False] * len(admitted)
    for rel, number, literal in copied_names(root, display, names):
        matched = False
        for index, name in enumerate(admitted):
            if name['file'] == rel and name['literal'] == literal:
                named[index] = matched = True
        if not matched:
            found.append(f'{rel}:{number}: "{literal}" copies a dictionary name')
    for index, name in enumerate(admitted):
        where = f'{EXCEPTIONS}: the name {name["literal"]!r} in {name["file"]}'
        if not name.get('reason'):
            found.append(f'{where} gives no reason')
        if not named[index]:
            found.append(f'{where} is stale')
    return found


def findings(root: Path) -> list[str]:
    """Every way a surface keeps its own number format or name."""
    source = crysta_source(root)
    try:
        display, names = dictionary_strings(source)
    except (OSError, yaml.YAMLError, AttributeError) as error:
        return [f"cannot read crysta's dictionary under {source}: {error}"]
    try:
        recorded = json.loads((root / EXCEPTIONS).read_text(encoding='utf-8'))
        exceptions, admitted = recorded['exceptions'], recorded['names']
    except (OSError, ValueError, KeyError) as error:
        return [f'cannot read {EXCEPTIONS}: {error}']
    return rounding_findings(root, exceptions) + name_findings(root, display, names, admitted)


def main(argv: list[str] | None = None) -> int:
    """Check the surfaces; exit 1 with each finding."""
    parser = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    parser.add_argument('--root', type=Path, default=HERE.parents[1])
    args = parser.parse_args(argv)
    found = findings(args.root)
    for finding in found:
        sys.stdout.write(f'display_sources: {finding}\n')
    if found:
        return 1
    sys.stdout.write(
        'display_sources: every number and name on screen comes from the dictionary\n'
    )
    return 0


if __name__ == '__main__':
    sys.exit(main())
