#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-3-Clause
"""Every number and name the app, the report and Python show comes from crysta's dictionary.

The core's display bridge (core/src/display.cpp) is the one place that rounds a number for display
or names an item. This check reads the app's QML and C++, the core and edi's Python library and
fails on:

* a rounding primitive anywhere else: toFixed, toPrecision, toExponential, toDefaultPrecision,
  toSinglePrecision, toErrSinglePrecision, QString::number with an 'f', 'g' or 'e' format,
  setprecision, a precision in a std::format, printf or Python format spec, or round(x, n), unless
  data/display-format-exceptions.json names its file, the text on its line and why it is not a
  displayed value of an item (chart ticks, durations, file writers);
* an exception that matches nothing any more;
* a qsTr literal equal to a dictionary display string (a category title, an item label or units,
  an option name), a .edi name or a selector token, and a C++ string literal equal to a display
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
SURFACES = (('app', ('.qml', '.cpp', '.hpp', '.js')), ('core', ('.cpp', '.hpp')), ('lib/edi', ('.py',)))

ROUNDING = {
    '.qml': [r'\.(toFixed|toPrecision|toExponential)\s*\(', r'\b(toDefaultPrecision|toSinglePrecision|toErrSinglePrecision)\b'],
    '.js': [r'\.(toFixed|toPrecision|toExponential)\s*\(', r'\b(toDefaultPrecision|toSinglePrecision|toErrSinglePrecision)\b'],
    '.cpp': [
        r"QString::number\([^;]*,\s*'[fgeFGE]'",
        r'\bsetprecision\s*\(',
        r'std::format\s*\(\s*"[^"]*\{[^}"]*\.\d',
        r'printf\s*\([^;]*"[^"]*%[-+ #0]*\d*\.\d+[fgeFGE]',
    ],
    '.py': [
        r'\{[^{}\'"]*:[^{}\'"]*\.\d+[fFeEgG%]?\}',
        r'%[-+ #0]*\d*\.\d+[fFeEgG]',
        r'\bround\(\s*[^,()]+(\([^()]*\))?\s*,\s*\d+\s*\)',
    ],
}
ROUNDING['.hpp'] = ROUNDING['.cpp']

QSTR = re.compile(r'qsTr\(\s*"((?:[^"\\]|\\.)*)"')
CPP_STRING = re.compile(r'"((?:[^"\\\n]|\\.)*)"')


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
    """The dictionary's display strings, and its .edi names and selector tokens."""
    path = source / 'data/dictionary/parameters.yaml'
    data = yaml.safe_load(path.read_text(encoding='utf-8'))
    display: set[str] = set()
    names: set[str] = set()
    for category in data.get('categories') or []:
        display.update(filter(None, (category.get('title'), category.get('loop_title'))))
    for entry in list(data.get('parameters') or []) + list(data.get('items') or []):
        display.update(filter(None, (entry.get('display_name'), entry.get('display_units'))))
        names.update(entry.get('edi_names') or [])
        for option in entry.get('options') or []:
            display.update(filter(None, [option.get('display_name')]))
            names.update(filter(None, [option.get('token')]))
    return display, names


def distinctive(text: str) -> bool:
    """A display string a user reads as a name, not a key a program also spells."""
    return len(text) > 1 and (any(c.isupper() or c == ' ' or ord(c) > 127 for c in text))


def surface_files(root: Path) -> list[Path]:
    """Every source of a surface, the bridge itself left out."""
    found = []
    for folder, suffixes in SURFACES:
        for path in sorted((root / folder).rglob('*')):
            if path.suffix in suffixes and path.is_file() and path.relative_to(root).as_posix() != BRIDGE:
                found.append(path)
    return found


def rounding_sites(root: Path) -> list[tuple[str, int, str]]:
    """Every line with a rounding primitive: file, line number and the line."""
    sites = []
    for path in surface_files(root):
        patterns = [re.compile(p) for p in ROUNDING.get(path.suffix, [])]
        rel = path.relative_to(root).as_posix()
        for number, line in enumerate(path.read_text(encoding='utf-8', errors='replace').splitlines(), 1):
            if line.lstrip().startswith(('//', '#', '*')):
                continue
            if any(p.search(line) for p in patterns):
                sites.append((rel, number, line.strip()))
    return sites


def copied_names(root: Path, display: set[str], names: set[str]) -> list[tuple[str, int, str]]:
    """Every literal that copies a dictionary name instead of asking the bridge: file, line, literal."""
    found = []
    readable = {text for text in display if distinctive(text)}
    for path in surface_files(root):
        rel = path.relative_to(root).as_posix()
        text = path.read_text(encoding='utf-8', errors='replace')
        for number, raw in enumerate(text.splitlines(), 1):
            if raw.lstrip().startswith(('//', '#', '*')):
                continue
            line = code_of(raw) if path.suffix != '.py' else raw
            for literal in QSTR.findall(line):
                if literal in display or literal in names:
                    found.append((rel, number, literal))
            if path.suffix in {'.cpp', '.hpp'} and 'qsTr(' not in line:
                found.extend((rel, number, literal) for literal in CPP_STRING.findall(line) if literal in readable)
    return found


def findings(root: Path) -> list[str]:
    """Every way a surface keeps its own number format or name."""
    source = crysta_source(root)
    try:
        display, names = dictionary_strings(source)
    except (OSError, yaml.YAMLError, AttributeError) as error:
        return [f'cannot read crysta\'s dictionary under {source}: {error}']
    exceptions_path = root / EXCEPTIONS
    try:
        recorded = json.loads(exceptions_path.read_text(encoding='utf-8'))
        exceptions, admitted = recorded['exceptions'], recorded['names']
    except (OSError, ValueError, KeyError) as error:
        return [f'cannot read {EXCEPTIONS}: {error}']
    found: list[str] = []
    used = [False] * len(exceptions)
    for rel, number, line in rounding_sites(root):
        matched = False
        for index, exception in enumerate(exceptions):
            if exception['file'] == rel and exception['match'] in line:
                used[index] = matched = True
        if not matched:
            found.append(f'{rel}:{number}: rounds a number outside the display bridge: {line}')
    for index, exception in enumerate(exceptions):
        if not exception.get('reason'):
            found.append(f'{EXCEPTIONS}: the exception for {exception["file"]} gives no reason')
        if not used[index]:
            found.append(f'{EXCEPTIONS}: the exception {exception["match"]!r} in {exception["file"]} is stale')
    named = [False] * len(admitted)
    for rel, number, literal in copied_names(root, display, names):
        matched = False
        for index, name in enumerate(admitted):
            if name['file'] == rel and name['literal'] == literal:
                named[index] = matched = True
        if not matched:
            found.append(f'{rel}:{number}: "{literal}" copies a dictionary name')
    for index, name in enumerate(admitted):
        if not name.get('reason'):
            found.append(f'{EXCEPTIONS}: the name {name["literal"]!r} in {name["file"]} gives no reason')
        if not named[index]:
            found.append(f'{EXCEPTIONS}: the name {name["literal"]!r} in {name["file"]} is stale')
    return found


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
    sys.stdout.write('display_sources: every number and name on screen comes from the dictionary\n')
    return 0


if __name__ == '__main__':
    sys.exit(main())
