# SPDX-License-Identifier: BSD-3-Clause
"""Write each surface's licence lists from DEPENDENCIES.md, the one list of third-party components.

DEPENDENCIES.md has a row per component with a column for each surface (desktop app, web app,
Python package, CLI). From it this script writes:

- each THIRD-PARTY-NOTICES section's `Licence:` and `In edi:` lines (the section's licence text
  stays as the component distributes it);
- licenses/, one `<component>-LICENSE` file per component the Python package or the CLI
  carries, the text of its notices section, and nothing else;
- pyproject.toml's `license-files`: LICENSE and the Python package's files;
- cli/licence-files.txt: the CLI's files, which its build puts beside the executable with LICENSE.

The application reads DEPENDENCIES.md itself, from its resources (ApplicationInfo).

    python tools/licences/sync.py           # write
    python tools/licences/sync.py --check   # compare, write nothing; exit 1 on a difference
"""

import argparse
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DEPENDENCIES = ROOT / 'DEPENDENCIES.md'
NOTICES = ROOT / 'THIRD-PARTY-NOTICES'
LICENSES = ROOT / 'licenses'
PYPROJECT = ROOT / 'pyproject.toml'
CLI_LIST = ROOT / 'cli' / 'licence-files.txt'
HEADER = [
    'Component',
    'Version',
    'Licence',
    'Desktop app',
    'Web app',
    'Python package',
    'CLI',
    'In edi',
]
NONE = '—'


def cells(line: str) -> list[str]:
    return [cell.strip() for cell in line.strip().strip('|').split('|')]


def components() -> list[dict[str, str]]:
    """Every component row of DEPENDENCIES.md, keyed by the header's names."""
    rows = []
    header = None
    for line in DEPENDENCIES.read_text(encoding='utf-8').splitlines():
        if not line.startswith('|'):
            header = None
            continue
        row = cells(line)
        if row[0] == 'Component':
            header = row
            continue
        if header != HEADER or set(row[0]) <= {'-', ' '}:
            continue
        if len(row) != len(HEADER):
            raise ValueError(f'DEPENDENCIES.md: a row has {len(row)} cells: {line}')
        rows.append(dict(zip(HEADER, row, strict=True)))
    if not rows:
        raise ValueError('DEPENDENCIES.md lists no components under the expected header')
    return rows


def carried(row: dict[str, str], surface: str) -> bool:
    return row[surface] not in {'', NONE}


def slug(name: str) -> str:
    return re.sub(r'[^A-Za-z0-9.+-]+', '-', name).strip('-')


def notices_sections(text: str) -> dict[str, tuple[int, int]]:
    """Each `## <name>` section's line range in the notices."""
    lines = text.split('\n')
    starts = [i for i, line in enumerate(lines) if line.startswith('#')]
    sections = {}
    for k, start in enumerate(starts):
        if lines[start].startswith('## '):
            end = starts[k + 1] if k + 1 < len(starts) else len(lines)
            sections[lines[start][3:]] = (start, end)
    return sections


def licence_text(lines: list[str]) -> str:
    """A section's indented licence text, the indent removed."""
    body = [line.removeprefix('    ') for line in lines]
    first = next(i for i, line in enumerate(lines) if line.startswith('    '))
    text = '\n'.join(body[first:]).rstrip()
    return text + '\n'


def expected(rows: list[dict[str, str]]) -> tuple[str, dict[str, str], str, str]:
    """The notices, licenses/ files, pyproject.toml and CLI list DEPENDENCIES.md makes."""
    notices = NOTICES.read_text(encoding='utf-8')
    sections = notices_sections(notices)
    names = [row['Component'] for row in rows]
    missing = [name for name in names if name not in sections]
    extra = [name for name in sections if name not in names]
    if missing or extra:
        raise ValueError(
            f'THIRD-PARTY-NOTICES sections differ from DEPENDENCIES.md: missing {missing}, '
            f'not listed {extra}'
        )
    lines = notices.split('\n')
    files = {}
    python, cli = [], []
    for row in rows:
        start, end = sections[row['Component']]
        for i in range(start, end):
            if lines[i].startswith('Licence:'):
                lines[i] = f'Licence: {row["Licence"]}'
            elif lines[i].startswith('In edi:'):
                lines[i] = f'In edi: {row["In edi"]}'
        name = f'{slug(row["Component"])}-LICENSE'
        if carried(row, 'Python package') or carried(row, 'CLI'):
            files[name] = licence_text(lines[start:end])
        if carried(row, 'Python package'):
            python.append(name)
        if carried(row, 'CLI'):
            cli.append(name)
    pyproject = PYPROJECT.read_text(encoding='utf-8')
    listed = ', '.join(f'"{name}"' for name in ['LICENSE', *(f'licenses/{f}' for f in python)])
    pyproject = re.sub(
        r'^license-files = \[.*\]$', f'license-files = [{listed}]', pyproject, flags=re.MULTILINE
    )
    cli_list = ''.join(f'{name}\n' for name in cli)
    return '\n'.join(lines), files, pyproject, cli_list


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument('--check', action='store_true', help='compare, write nothing')
    args = parser.parse_args()
    notices, files, pyproject, cli_list = expected(components())
    present = {path.name: path.read_text(encoding='utf-8') for path in LICENSES.glob('*')}
    differences = []
    if notices != NOTICES.read_text(encoding='utf-8'):
        differences.append('THIRD-PARTY-NOTICES')
    if present != files:
        differences.append('licenses/')
    if pyproject != PYPROJECT.read_text(encoding='utf-8'):
        differences.append('pyproject.toml license-files')
    if not CLI_LIST.exists() or cli_list != CLI_LIST.read_text(encoding='utf-8'):
        differences.append('cli/licence-files.txt')
    if args.check:
        if differences:
            print(f'not as DEPENDENCIES.md makes them: {", ".join(differences)}')
            print('run: python tools/licences/sync.py')
            return 1
        print('licence lists: as DEPENDENCIES.md makes them')
        return 0
    NOTICES.write_text(notices, encoding='utf-8')
    for name in present.keys() - files.keys():
        (LICENSES / name).unlink()
    for name, text in files.items():
        (LICENSES / name).write_text(text, encoding='utf-8')
    PYPROJECT.write_text(pyproject, encoding='utf-8')
    CLI_LIST.write_text(cli_list, encoding='utf-8')
    print(f'wrote {", ".join(differences) or "nothing (already current)"}')
    return 0


if __name__ == '__main__':
    sys.exit(main())
