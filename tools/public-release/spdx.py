# SPDX-License-Identifier: BSD-3-Clause
"""Give every product source file its SPDX licence identifier.

    python tools/public-release/spdx.py --tree PATH [--check]

edi's source, the application's included, is BSD-3-Clause (LICENSE). A source file that lacks the
identifier gets it as its first line, after a shebang or an encoding line. `--check` lists the
files that lack it and exits 1 if any does; it writes nothing.

Source is the code under the product directories, the build files and the tools. Test fixtures and
the documentation tree carry data and pages, not product source, and the hidden test tiers belong
to the tests.
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

IDENTIFIER = 'SPDX-License-Identifier: BSD-3-Clause'
SLASH = {'.cpp', '.hpp', '.h', '.c', '.qml', '.js', '.in'}
HASH = {'.py', '.sh', '.cmake'}
EXCLUDED = (
    'tests/unit/',
    'tests/integration/',
    'tests/system/',
    'tests/fixtures/',
    'docs/',
    'knowledge/',
    'build/',
)


def _marker(path: str) -> str | None:
    name = path.rsplit('/', 1)[-1]
    suffix = Path(name).suffix
    if name == 'CMakeLists.txt' or suffix in HASH:
        return '#'
    return '//' if suffix in SLASH else None


def sources(tree: Path) -> list[str]:
    """The tracked source files that must carry the identifier."""
    listed = subprocess.run(
        ['git', '-C', str(tree), 'ls-files', '-z'], capture_output=True, check=True
    )
    return [
        rel
        for rel in sorted(listed.stdout.decode().split('\0'))
        if rel and not rel.startswith(EXCLUDED) and _marker(rel) is not None
    ]


def with_identifier(text: str, marker: str) -> str:
    """The text with the identifier line inserted, unless it already has one."""
    lines = text.split('\n')
    if any(IDENTIFIER in line for line in lines[:5]):
        return text
    at = 0
    while at < len(lines) and at < 2 and lines[at].startswith(('#!', '# -*-')):
        at += 1
    lines.insert(at, f'{marker} {IDENTIFIER}')
    return '\n'.join(lines)


def main(argv: list[str] | None = None) -> int:
    """Command line: add the identifier, or with --check list the files that lack it."""
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument('--tree', required=True, type=Path, help='a git checkout of edi')
    parser.add_argument('--check', action='store_true', help='list what lacks it; write nothing')
    args = parser.parse_args(argv)
    missing = []
    for rel in sources(args.tree):
        path = args.tree / rel
        text = path.read_text(encoding='utf-8')
        new = with_identifier(text, _marker(rel) or '#')
        if new != text:
            missing.append(rel)
            if not args.check:
                path.write_text(new, encoding='utf-8')
    for rel in missing:
        print(rel)
    verb = 'lack' if args.check else 'were given'
    print(f'spdx: {len(missing)} file(s) {verb} the identifier', file=sys.stderr)
    return 1 if (args.check and missing) else 0


if __name__ == '__main__':
    sys.exit(main())
