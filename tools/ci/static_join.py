# SPDX-License-Identifier: BSD-3-Clause
"""Join the static-check parts of one platform: CI's required job `static · <platform>` (ADR-0093).

    python3 tools/ci/static_join.py <platform> <parts> <folder>

<folder> holds this run's artifacts: static-full-<platform>, the app job's `cpp-tidy.sh list` and
`cpp-cppcheck.sh list` on its full build, and static-part-<platform>-<k> for k = 1..<parts>, the
units each part's analyzers reported as processed (the lines of tools/ci/static_checks.py). It
exits 1, naming each problem, unless:

- every part reported for both tools under its own `part <k>/<parts>`;
- the parts' units together are the app job's list, no more and no fewer;
- that list holds every unit of tests/fixtures/static_checks/<platform>.txt, the analyzers' own
  report of the run before the split, except one whose file Git no longer tracks; a unit whose
  command hash differs counts only if its file or a build file changed since that list was last
  committed;
- every call that list gives arguments for ran with exactly those arguments in the parts.

The list lives in Git and holds unit and `args` lines, blank lines and `#` comments.
"""

from __future__ import annotations

import re
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
TOOLS = ('clang-tidy', 'cppcheck')
UNIT = re.compile(r'(clang-tidy|cppcheck) (\S+) (\S+) (\S+) ([0-9a-f]{64})')
ARGS = re.compile(r'args (clang-tidy|cppcheck) (\S+) (\S+) (.*)')
# What can change a compile command while its file stays the same.
BUILD = re.compile(
    r'(?:.*/)?CMakeLists\.txt|.*\.cmake|cmake/.*|pixi\.(?:toml|lock)|\.github/workflows/ci\.yml'
    r'|tools/ci/(?:app-build|core-build|build-crysta|cpp-cppcheck)\.sh'
)

Unit = tuple[str, str, str, str, str]
Call = tuple[str, str, str]


class RefusedError(Exception):
    """A report or the committed list that cannot be read."""


@dataclass
class Listing:
    """The lines of one report or of the committed list."""

    header: str = ''
    units: set[Unit] = field(default_factory=set)
    args: dict[Call, str] = field(default_factory=dict)


def read(path: Path, *, header: bool) -> Listing:
    """A report (its first line a header) or the committed list."""
    try:
        lines = path.read_text(encoding='utf-8').splitlines()
    except OSError as error:
        raise RefusedError(f'{path}: {error.strerror or error}') from error
    listing = Listing(header=lines.pop(0) if header and lines else '')
    for number, line in enumerate(lines, start=2 if header else 1):
        if not line.strip() or line.startswith('#'):
            continue
        if unit := UNIT.fullmatch(line):
            listing.units.add(unit.groups())
        elif args := ARGS.fullmatch(line):
            call = args.group(1, 2, 3)
            if listing.args.setdefault(call, args[4]) != args[4]:
                raise RefusedError(f'{path}:{number}: a second argument list for {" ".join(call)}')
        else:
            raise RefusedError(f'{path}:{number}: neither a unit nor an args line: {line[:80]!r}')
    return listing


def report(path: Path, header: str, tool: str) -> Listing | str:
    """One tool's report with the header it must have, or why it cannot count."""
    try:
        listing = read(path, header=True)
    except RefusedError as error:
        return str(error)
    if listing.header != header:
        return f'{path}: starts with {listing.header!r}, not {header!r}'
    if any(unit[0] != tool for unit in listing.units) or any(c[0] != tool for c in listing.args):
        return f'{path}: holds another tool than {tool}'
    return listing


def show(unit: Unit) -> str:
    """A unit as its line."""
    return ' '.join(unit)


def git(*args: str) -> str:
    """Git's answer about this checkout."""
    result = subprocess.run(['git', *args], cwd=ROOT, capture_output=True, text=True, check=False)
    if result.returncode != 0:
        raise RefusedError(f'git {" ".join(args)}: {result.stderr.strip()}')
    return result.stdout.strip()


def against_list(full: set[Unit], seen: dict[Call, set[str]], platform: str) -> list[str]:
    """What the full build's list lost of the committed list, and the arguments that changed."""
    path = ROOT / 'tests' / 'fixtures' / 'static_checks' / f'{platform.lower()}.txt'
    name = path.relative_to(ROOT).as_posix()
    if not path.is_file():
        return [f'{name} is not committed, so nothing shows that the parts kept every unit']
    fixture = read(path, header=False)
    since = git('log', '-1', '--format=%H', '--', name)
    if not since:
        return [f'{name} has no commit, so nothing says what changed since it was taken']
    changed = set(git('diff', '--name-only', since, 'HEAD').splitlines())
    tracked = set(git('ls-files').splitlines())
    rebuilt = any(BUILD.fullmatch(changed_path) for changed_path in changed)
    hashes: dict[tuple[str, ...], set[str]] = {}
    for unit in full:
        hashes.setdefault(unit[:4], set()).add(unit[4])
    problems = []
    for unit in sorted(fixture.units - full):
        if unit[3] not in tracked:
            continue
        if unit[:4] not in hashes:
            problems.append(f'{show(unit)}: in {name}, missing from the full build')
        elif unit[3] not in changed and not rebuilt:
            problems.append(
                f'{show(unit)}: its command changed while neither the file nor a build file did'
                f' since {since[:12]}'
            )
    for call, args in sorted(fixture.args.items()):
        if seen.get(call, set()) != {args}:
            ran = sorted(seen.get(call, set()))
            problems.append(
                f'args {" ".join(call)}: {name} records {args!r}, the parts ran {ran!r}'
            )
    return problems


def join(platform: str, parts: int, folder: Path) -> list[str]:
    """Every reason the parts do not cover the full build and the run before the split."""
    problems: list[str] = []
    full: set[Unit] = set()
    processed: set[Unit] = set()
    seen: dict[Call, set[str]] = {}
    for tool in TOOLS:
        wanted = [(folder / f'static-full-{platform}' / f'{tool}.txt', 'full')]
        wanted += [
            (folder / f'static-part-{platform}-{k}' / f'{tool}.txt', f'part {k}/{parts}')
            for k in range(1, parts + 1)
        ]
        for path, header in wanted:
            got = report(path, header, tool)
            if isinstance(got, str):
                problems.append(got)
                continue
            (full if header == 'full' else processed).update(got.units)
            for call, args in got.args.items():
                seen.setdefault(call, set()).add(args)
    problems += [
        f'{show(u)}: in the full build, processed by no part' for u in sorted(full - processed)
    ]
    problems += [
        f'{show(u)}: processed by a part, not in the full build' for u in sorted(processed - full)
    ]
    problems += [
        f'args {" ".join(c)}: the parts ran {sorted(a)!r}' for c, a in seen.items() if len(a) > 1
    ]
    try:
        problems += against_list(full, seen, platform)
    except RefusedError as error:
        problems.append(str(error))
    return problems


def main(argv: list[str]) -> int:
    """Print each problem and exit 1, or say what the join covered."""
    if len(argv) != 3 or not re.fullmatch(r'[A-Za-z]+', argv[0]) or not argv[1].isdigit():
        print(__doc__.split('\n\n')[1], file=sys.stderr)
        return 2
    platform, parts, folder = argv[0], int(argv[1]), Path(argv[2])
    problems = join(platform, parts, folder) if parts > 0 else ['no parts']
    for problem in problems:
        print(f'static · {platform}: {problem}')
    if not problems:
        print(f'static · {platform}: the {parts} parts processed every unit of the full build')
    return 1 if problems else 0


if __name__ == '__main__':
    raise SystemExit(main(sys.argv[1:]))
