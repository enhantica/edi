#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-3-Clause
"""The tutorial execution-exclusion gate, edi side.

The five ported tutorials live in ``docs/user/tutorials/`` execution-disabled; an unglobbed
directory would be a gate that cannot fail, so the exclusion is DECLARED
(``docs/user/tutorials/execution-exclusions.yml``) and this gate makes every state decidable
from edi's own committed files (single-repo input — green in a clean edi-only checkout):

  (a) a tutorial source neither covered by any nbmake invocation parsed from ``pixi.toml`` nor
      listed in the declaration is red (an undeclared skip);
  (b) a listed notebook whose source does not exist is red (a stale entry);
  (c) a listed notebook that IS covered by a parsed nbmake invocation is red (execution wired,
      entry must leave);
  (d) an entry whose ``unblocked_by`` is not a well-formed unblocker name is red: a lower-case,
      hyphenated name of the work whose landing lets the tutorial execute.

The executed set is DERIVED from the committed task definitions, never restated. The expiry
event itself is checked outside edi, against the record of the unblocking work.
"""

from __future__ import annotations

import fnmatch
import re
import sys
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
TUTORIALS_DIR = ROOT / 'docs' / 'user' / 'tutorials'
DECLARATION = TUTORIALS_DIR / 'execution-exclusions.yml'
PIXI = ROOT / 'pixi.toml'
UNBLOCKER = re.compile(r'^[a-z][a-z0-9]*(?:-[a-z0-9]+)*$')


def parse_declaration(violations: list[str]) -> list[dict[str, str]]:
    if not DECLARATION.is_file():
        violations.append(f'missing declaration {DECLARATION.relative_to(ROOT)} (fail closed)')
        return []
    entries: list[dict[str, str]] = []
    current: dict[str, str] = {}
    for lineno, raw in enumerate(DECLARATION.read_text().splitlines(), start=1):
        line = raw.split('#', 1)[0].rstrip()
        if not line.strip():
            continue
        if line.strip() == 'excluded:':
            continue
        m = re.match(r'^\s*-\s+notebook:\s*(\S+)\s*$', line)
        if m:
            current = {'notebook': m.group(1)}
            entries.append(current)
            continue
        m = re.match(r'^\s+unblocked_by:\s*(\S+)\s*$', line)
        if m:
            if not current:
                violations.append(f'{DECLARATION.name}:{lineno}: unblocked_by before any notebook')
            else:
                current['unblocked_by'] = m.group(1)
            continue
        violations.append(f'{DECLARATION.name}:{lineno}: unparseable line {raw!r} (fail closed)')
    for entry in entries:
        task = entry.get('unblocked_by', '')
        if not UNBLOCKER.match(task):
            violations.append(
                f'{DECLARATION.name}: entry {entry.get("notebook")!r} has no well-formed '
                f'unblocker name (got {task!r})'
            )
    return entries


# pytest option arity for the supported nbmake command grammar (parse positional selector
# semantics, never token spelling). `=`-joined options are self-contained; the sets below say
# which bare options consume the NEXT token as their value. An option outside every set is
# AMBIGUOUS and refuses fail-closed: a wrong guess in either direction silently flips red (a)/(c).
_VALUE_OPTIONS = {
    # every option whose valid SEPARATED form consumes the next token (pytest core + nbmake);
    # review-11 F2: --color belongs here — `--color yes` is valid, so a flag classification
    # would record `yes` as a positional selector.
    '-k',
    '-m',
    '-p',
    '-c',
    '-o',
    '--override-ini',
    '--rootdir',
    '--confcutdir',
    '--basetemp',
    '--color',
    '--nbmake-timeout',
    '--ignore',
    '--ignore-glob',
    '--deselect',
}
_FLAG_OPTIONS = {
    '-v',
    '-vv',
    '-q',
    '-x',
    '-s',
    '--nbmake',
    '--overwrite',
    '--no-header',
    '--co',
    '--collect-only',
    '-rA',
    '-ra',
}
_EXCLUDE_OPTIONS = {'--ignore', '--ignore-glob', '--deselect'}
_LAUNCHERS = {'python', 'python3', 'pytest'}


def parse_nbmake_command(tokens: list[str], violations: list[str]) -> tuple[list[str], list[str]]:
    """(positional selectors, exclusion selectors) of one nbmake command; refuses ambiguity."""
    selectors: list[str] = []
    excluded: list[str] = []
    i = 0
    while i < len(tokens):
        piece = tokens[i]
        if piece in _LAUNCHERS:
            i += 1
            continue
        if piece == '-m' and i + 1 < len(tokens) and tokens[i + 1] == 'pytest':
            i += 2  # the launcher's module selector, not a test-expression option
            continue
        if piece.startswith('-'):
            name = piece.split('=', 1)[0]
            if '=' in piece:
                if name in _EXCLUDE_OPTIONS:
                    excluded.append(piece.split('=', 1)[1])
                i += 1
            elif name in _VALUE_OPTIONS:
                if name in _EXCLUDE_OPTIONS and i + 1 < len(tokens):
                    excluded.append(tokens[i + 1])
                i += 2  # the option consumes its separated value
            elif name in _FLAG_OPTIONS:
                i += 1
            else:
                violations.append(
                    f'(f) nbmake command carries the undeclared option {piece!r} — selector '
                    'semantics are parsed with explicit arity and an unknown option is '
                    'ambiguous; use its =value form or extend the declared arity tables'
                )
                return [], []
        else:
            selectors.append(piece)
            i += 1
    return selectors, excluded


def executed_selector_sets(violations: list[str]) -> list[tuple[list[str], list[str]]]:
    """One (selectors, exclusions) pair per committed nbmake TASK COMMAND in pixi.toml.

    Only `cmd` values are commands; other pixi strings are never harvested.
    """
    out: list[tuple[list[str], list[str]]] = []

    def harvest(tokens: list[str]) -> None:
        if any(piece == '--nbmake' for piece in tokens):
            out.append(parse_nbmake_command(tokens, violations))

    def walk(node: object) -> None:
        if isinstance(node, dict):
            for key, value in node.items():
                if key == 'cmd':
                    if isinstance(value, str):
                        harvest(value.split())
                    elif isinstance(value, list):
                        harvest([str(item) for item in value])
                else:
                    walk(value)
        elif isinstance(node, list):
            for item in node:
                walk(item)

    walk(tomllib.loads(PIXI.read_text()))
    return out


def _matches(rel: str, sel: str) -> bool:
    sel = sel.rstrip('/')
    if any(ch in sel for ch in '*?['):
        return fnmatch.fnmatch(rel, sel)
    if (ROOT / sel).is_dir():
        return rel.startswith(sel + '/')
    return rel == sel


def covered(source: Path, commands: list[tuple[list[str], list[str]]]) -> bool:
    """True iff any nbmake command executes this tutorial.

    A positional selector must reach its source or paired notebook, and no exclusion
    selector of the same command may remove it.
    """
    rel_source = source.relative_to(ROOT).as_posix()
    rel_notebook = source.with_suffix('.ipynb').relative_to(ROOT).as_posix()
    for selectors, excluded in commands:
        for rel in (rel_source, rel_notebook):
            if any(_matches(rel, sel) for sel in selectors) and not any(
                _matches(rel, sel) for sel in excluded
            ):
                return True
    return False


def main() -> int:
    violations: list[str] = []
    entries = parse_declaration(violations)
    listed = {Path(entry['notebook']).stem for entry in entries}
    if len(listed) != len(entries):
        violations.append(f'{DECLARATION.name}: duplicate notebook entries')
    for entry in entries:
        declared = entry['notebook']
        if Path(declared).suffix != '.ipynb':
            violations.append(
                f'(d) {declared}: an entry names its rendered notebook path (.ipynb), '
                'identifying exactly one tutorial file'
            )
            continue
        if not (TUTORIALS_DIR / declared).is_file():
            violations.append(
                f'(b) {declared}: listed in {DECLARATION.name} but the notebook file is absent'
            )
        if not (TUTORIALS_DIR / (Path(declared).stem + '.py')).is_file():
            violations.append(
                f'(b) {declared}: listed in {DECLARATION.name} but its jupytext source is absent'
            )
    executed = executed_selector_sets(violations)

    sources = sorted(TUTORIALS_DIR.glob('*.py')) if TUTORIALS_DIR.is_dir() else []
    for source in sources:
        stem = source.stem
        if covered(source, executed):
            if stem in listed:
                violations.append(
                    f'(c) {stem}: executed by a committed nbmake invocation but still listed — '
                    'the entry must leave in the change set that wires execution'
                )
        elif stem not in listed:
            violations.append(
                f'(a) {stem}: neither executed by any committed nbmake invocation nor listed in '
                f'{DECLARATION.name} — an undeclared skip is a gate that cannot fail'
            )

    if violations:
        print('tutorial-exclusions: RED')
        for item in violations:
            print(f'  {item}')
        return 1
    print(
        f'tutorial-exclusions: OK — {len(sources)} tutorial sources; {len(listed)} declared '
        f'exclusions, each naming its unblocker; executed set derived from pixi.toml '
        f'({len(executed)} nbmake command(s), arity-parsed)'
    )
    return 0


if __name__ == '__main__':
    sys.exit(main())
