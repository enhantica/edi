# SPDX-License-Identifier: BSD-3-Clause
"""The files clang-tidy and cppcheck take from a compile database, and those they ran (ADR-0093).

cpp-tidy.sh and cpp-cppcheck.sh choose the files; this reads the databases and the analyzers' own
output for them. A unit is one line per database entry of a file:

    <tool> <call> <database> <file> <sha256>

<file> is relative to the repository root, and <sha256> is the SHA-256 of the entry's `command`
with every occurrence of the root's absolute path replaced by `.`. A call's arguments other than
its files are one line, made relative the same way:

    args <tool> <call> <database> <argument> ...

    static_checks.py select <root> <database> clang-tidy <regex>...
        the files run-clang-tidy takes: a regex found in the file's absolute path
    static_checks.py select <root> <database> cppcheck <argument>...
        the files cppcheck takes: a --file-filter glob, whose * and ? match / too
    static_checks.py part <k>/<n> <offset>
        the stdin lines whose index plus <offset> is k-1 modulo n
    static_checks.py regexes
        each stdin file as a regex that matches only it
    static_checks.py units <root> <tool> <call> <database>
        the units of the stdin files
    static_checks.py processed <root> <tool> <call> <database> <log> [<argument>...]
        the args line and the units of every file the analyzer's output names as processed:
        run-clang-tidy's line per file, which holds clang-tidy's arguments, or cppcheck's
        `Checking <file> ...`, whose arguments are given
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import sys
from pathlib import Path

TOOLS = ('clang-tidy', 'cppcheck')
# run-clang-tidy prints `[i/n][seconds] <clang-tidy invocation> <file>` after each file it ran.
TIDY_RAN = re.compile(r'\[\s*\d+/\d+\]\[\d+(?:\.\d+)?s\] (\S.*)')
# cppcheck prints `Checking <file> ...` as it starts a database entry; its configurations follow
# as `Checking <file>: <defines>...`.
CPPCHECK_RAN = re.compile(r'Checking (\S+[^:\s]) \.\.\.')
ANSI = re.compile(r'\x1b\[[0-9;]*m')
PART = re.compile(r'([1-9][0-9]*)/([1-9][0-9]*)')


class RefusedError(Exception):
    """A database, a list or an analyzer's output that cannot be read as units."""


def relative(root: str, text: str) -> str:
    """``text`` with the repository root's absolute path made relative."""
    return text.replace(root, '.')


def database_entries(root: str, database: str) -> dict[str, list[str]]:
    """Each absolute file of a compile database, with the hash of each of its entries' commands."""
    path = Path(root, database, 'compile_commands.json')
    try:
        loaded = json.loads(path.read_text(encoding='utf-8'))
    except (OSError, ValueError) as error:
        raise RefusedError(f'{path}: {error}') from error
    found: dict[str, list[str]] = {}
    for entry in loaded if isinstance(loaded, list) else [None]:
        fields = entry if isinstance(entry, dict) else {}
        command, folder, name = (fields.get(key) for key in ('command', 'directory', 'file'))
        if not all(isinstance(value, str) for value in (command, folder, name)):
            raise RefusedError(f'{path}: an entry without a command, directory and file')
        digest = hashlib.sha256(relative(root, command).encode()).hexdigest()
        found.setdefault(os.path.normpath(Path(folder, name)), []).append(digest)
    return found


def glob(pattern: str) -> re.Pattern[str]:
    """A cppcheck file-filter glob as a regex."""
    parts = ('.*' if c == '*' else '.' if c == '?' else re.escape(c) for c in pattern)
    return re.compile(''.join(parts))


def select(root: str, database: str, tool: str, patterns: list[str]) -> list[str]:
    """The files of a database the analyzer takes, sorted."""
    files = database_entries(root, database)
    if tool == 'clang-tidy':
        found = re.compile('|'.join(patterns))
        return sorted(name for name in files if found.search(name))
    filters = [
        glob(p.removeprefix('--file-filter=')) for p in patterns if p.startswith('--file-filter=')
    ]
    return sorted(name for name in files if not filters or any(f.fullmatch(name) for f in filters))


def part(spec: str, offset: int, lines: list[str]) -> list[str]:
    """The lines part k of n takes: every n-th, counted from ``offset``."""
    match = PART.fullmatch(spec)
    if match is None or not 1 <= int(match[1]) <= int(match[2]):
        raise RefusedError(f'{spec!r} is not a part k/n with 1 <= k <= n')
    k, n = int(match[1]), int(match[2])
    return [line for i, line in enumerate(lines) if (i + offset) % n == k - 1]


def units(root: str, tool: str, call: str, database: str, files: list[str]) -> list[str]:
    """One unit line per database entry of each file."""
    entries = database_entries(root, database)
    lines = []
    for name in files:
        if name not in entries:
            raise RefusedError(f'{name} is not a file of {database}/compile_commands.json')
        if os.path.commonpath([root, name]) != root:
            raise RefusedError(f'{name} is outside the repository')
        file = os.path.relpath(name, root)
        lines += [f'{tool} {call} {database} {file} {digest}' for digest in entries[name]]
    return lines


def processed(
    root: str, tool: str, call: str, database: str, log: str, given: list[str]
) -> list[str]:
    """The args line and the units of the files the analyzer's own output names as processed."""
    try:
        text = Path(log).read_text(encoding='utf-8', errors='replace')
    except OSError as error:
        raise RefusedError(f'{log}: {error}') from error
    files, arguments = set(), set()
    for line in ANSI.sub('', text).splitlines():
        if tool == 'clang-tidy' and (match := TIDY_RAN.fullmatch(line)):
            *outer, name = match[1].split(' ')
            arguments.add(' '.join(outer))
        elif tool == 'cppcheck' and (match := CPPCHECK_RAN.fullmatch(line)):
            name = match[1]
        else:
            continue
        files.add(os.path.normpath(Path(root, name)))
    if tool == 'cppcheck':
        arguments = {' '.join(given)}
    if len(arguments) > 1:
        raise RefusedError(
            f'{log}: run-clang-tidy ran its files with {len(arguments)} argument lists'
        )
    head = [f'args {tool} {call} {database} {relative(root, a)}' for a in arguments]
    return head + units(root, tool, call, database, sorted(files))


def stdin_lines() -> list[str]:
    """The non-empty lines of standard input."""
    return [line for line in sys.stdin.read().splitlines() if line]


def run(args: list[str]) -> list[str]:
    """The output lines of one command."""
    match args:
        case ['select', root, database, tool, *patterns] if tool in TOOLS:
            return select(root, database, tool, patterns)
        case ['part', spec, offset] if offset.isdigit():
            return part(spec, int(offset), stdin_lines())
        case ['regexes']:
            return [f'^{re.escape(name)}$' for name in stdin_lines()]
        case ['units', root, tool, call, database] if tool in TOOLS:
            return units(root, tool, call, database, stdin_lines())
        case ['processed', root, tool, call, database, log, *given] if tool in TOOLS:
            return processed(root, tool, call, database, log, given)
    raise RefusedError(f'usage: see {Path(__file__).name}; got {" ".join(args)!r}')


def main() -> int:
    """Print one command's lines; exit 1 with the reason if they cannot be read."""
    try:
        lines = run(sys.argv[1:])
    except RefusedError as error:
        print(f'static-checks: {error}', file=sys.stderr)
        return 1
    for line in lines:
        print(line)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
