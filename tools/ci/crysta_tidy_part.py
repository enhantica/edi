# SPDX-License-Identifier: BSD-3-Clause
"""Run one part of crysta's own clang-tidy task.

    python tools/ci/crysta_tidy_part.py K/N [CRYSTA_DIR] [--list]

Reads the `cpp-tidy` task from crysta's manifest, so the flags and the file selection stay
crysta's: the files of its build database that the task's path arguments match, sorted, every N-th
from the K-th. The parts of one platform share no file and together hold the whole selection.
`--list` prints the part's files and runs nothing.
"""

from __future__ import annotations

import json
import os
import re
import shlex
import sys
import tomllib
from pathlib import Path


def task(root: Path) -> list[str]:
    """The `cpp-tidy` command as crysta's manifest writes it."""
    manifest = tomllib.loads((root / 'pixi.toml').read_text(encoding='utf-8'))
    found = manifest.get('feature', {}).get('lint', {}).get('tasks', {}).get('cpp-tidy')
    command = found.get('cmd') if isinstance(found, dict) else found
    if not isinstance(command, str):
        raise SystemExit('crysta-tidy-part: crysta pixi.toml has no cpp-tidy task command')
    return shlex.split(command)


def database(command: list[str], root: Path) -> Path:
    """The build folder `-p` names."""
    for index, word in enumerate(command):
        if word == '-p' and index + 1 < len(command):
            return root / command[index + 1]
        if word.startswith('-p='):
            return root / word[3:]
    raise SystemExit('crysta-tidy-part: the cpp-tidy task names no build folder (-p)')


def split(command: list[str]) -> tuple[list[str], list[str]]:
    """The task's options (with `-p`'s folder) and its path arguments."""
    options, paths, value = [], [], False
    for word in command[1:]:
        if value or word.startswith('-'):
            options.append(word)
            value = word == '-p'
        else:
            paths.append(word)
    return options, paths


def selection(command: list[str], root: Path) -> list[str]:
    """The files the task's path arguments match, as run-clang-tidy matches them."""
    patterns = [re.compile(word) for word in split(command)[1]]
    entries = json.loads(
        (database(command, root) / 'compile_commands.json').read_text(encoding='utf-8')
    )
    files = set()
    for entry in entries:
        path = Path(entry['file'])
        path = path if path.is_absolute() else Path(entry['directory']) / path
        if any(pattern.search(str(path)) for pattern in patterns):
            files.add(os.path.normpath(path))
    return sorted(files)


def main(argv: list[str]) -> int:
    """Run (or list) part K of N."""
    listing = '--list' in argv
    argv = [a for a in argv if a != '--list']
    match = re.fullmatch(r'([1-9][0-9]*)/([1-9][0-9]*)', argv[0]) if argv else None
    if not match or int(match[1]) > int(match[2]):
        print(__doc__, file=sys.stderr)
        return 2
    k, n = int(match[1]), int(match[2])
    root = Path(argv[1] if len(argv) > 1 else '.').resolve()
    command = task(root)
    files = selection(command, root)
    mine = files[k - 1 :: n]
    root_text = str(root) + os.sep
    print(f"crysta-tidy-part: part {k}/{n} takes {len(mine)} of the task's {len(files)} files")
    if listing:
        for path in mine:
            print(path.removeprefix(root_text))
        return 0
    if not mine:
        return 0
    exact = [f'^{re.escape(path)}$' for path in mine]
    os.chdir(root)
    os.execvp(command[0], [command[0], *split(command)[0], *exact])  # noqa: S606 - crysta's own task
    return 1


if __name__ == '__main__':
    raise SystemExit(main(sys.argv[1:]))
