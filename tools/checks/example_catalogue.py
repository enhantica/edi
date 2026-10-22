#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-3-Clause
"""Check that every example catalogue case has all its forms (ADR-0048).

The registry ``docs/user/cli/projects.yml`` is the one list: a ``user-facing: true`` row is a
catalogue case, every other row a test fixture. This check reads files and runs nothing. It is red
when:

- the registry read as YAML and the registry read the way the app's CMake reads it (the
  ``^  - id:`` and ``^    user-facing: true`` lines) disagree on the ids, the cases or the order;
- a case lacks its ``project/project.edi`` named after the case, its ``index.md``, its
  ``PROVENANCE.md`` with a ``## Sources`` section, its tutorial ``docs/user/tutorials/<id>.py``,
  its notebook, or its one entry in ``docs/user/tutorials/execution-exclusions.yml``;
- a tutorial or its notebook loads anything but ``../cli/<id>/project``, loads it more than once,
  or the two disagree. A load is one top-level statement of one form,
  ``project = edi.Project.load('<path>')``; any other mention of ``Project.load`` fails;
- a file under a case's ``data/`` is not named in its Sources with its sha256;
- a tutorial, notebook or exclusion entry names something that is not a case, or a fixture has an
  ``index.md`` page (a fixture's page is its ``README.md``).

Every problem is reported. With none, it prints each case's title, tutorial and data files.
"""

from __future__ import annotations

import argparse
import ast
import hashlib
import json
import re
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
CLI_DIR = Path('docs') / 'user' / 'cli'
TUTORIALS_DIR = Path('docs') / 'user' / 'tutorials'
REGISTRY = CLI_DIR / 'projects.yml'
EXCLUSIONS = TUTORIALS_DIR / 'execution-exclusions.yml'
# The app's CMake reads the registry with these patterns (app/CMakeLists.txt).
CMAKE_LINE = re.compile(r'^  - id: |^    user-facing: ')
CMAKE_ID = re.compile(r'^  - id: *(.+)$')
CMAKE_CASE = re.compile(r'^    user-facing: *true$')
SOURCES = re.compile(r'^## Sources\s*$(?P<body>.*?)(?=^## |\Z)', re.MULTILINE | re.DOTALL)
# Files in the tutorials folder that are not tutorials.
NOT_TUTORIALS = {'index.md', 'execution-exclusions.yml'}


def read(path: Path) -> str:
    return path.read_text(encoding='utf-8')


def registry_from_yaml(root: Path, problems: list[str]) -> tuple[list[str], list[str]]:
    try:
        rows = yaml.safe_load(read(root / REGISTRY))['projects']
        ids = [str(row['id']) for row in rows]
        cases = [str(row['id']) for row in rows if row.get('user-facing') is True]
    except (OSError, yaml.YAMLError, KeyError, TypeError) as error:
        problems.append(f'{REGISTRY}: cannot be read as YAML ({error})')
        return [], []
    return ids, cases


def registry_as_cmake_reads_it(root: Path) -> tuple[list[str], list[str]]:
    ids: list[str] = []
    cases: list[str] = []
    for line in read(root / REGISTRY).splitlines():
        if not CMAKE_LINE.match(line):
            continue
        if match := CMAKE_ID.match(line):
            ids.append(match.group(1))
        elif CMAKE_CASE.match(line) and ids:
            cases.append(ids[-1])
    return ids, cases


def metadata_value(project_edi: Path, key: str) -> str | None:
    for line in read(project_edi).splitlines():
        name, _, value = line.strip().partition(' ')
        if name == key:
            value = value.strip()
            if len(value) >= 2 and value[0] == value[-1] and value[0] in '\'"':
                value = value[1:-1]
            return value
    return None


# The one form a tutorial loads its project in (ADR-0048): a top-level statement of its own,
# ``project = edi.Project.load('<path>')``. Python runs it exactly once, so the check needs no
# reasoning about evaluation; every other mention of ``Project.load`` fails.
LOAD_FORM = "project = edi.Project.load('<path>')"


def is_project_load(node: ast.AST) -> bool:
    """Whether ``node`` names ``Project.load``, called or not."""
    if not (isinstance(node, ast.Attribute) and node.attr == 'load'):
        return False
    owner = node.value
    return (isinstance(owner, ast.Name) and owner.id == 'Project') or (
        isinstance(owner, ast.Attribute) and owner.attr == 'Project'
    )


def is_load_statement(statement: ast.stmt) -> bool:
    """Whether a top-level statement is exactly ``project = edi.Project.load(<one argument>)``."""
    if not (
        isinstance(statement, ast.Assign)
        and len(statement.targets) == 1
        and isinstance(statement.targets[0], ast.Name)
        and statement.targets[0].id == 'project'
        and isinstance(statement.value, ast.Call)
    ):
        return False
    call = statement.value
    func = call.func
    return (
        isinstance(func, ast.Attribute)
        and func.attr == 'load'
        and isinstance(func.value, ast.Attribute)
        and func.value.attr == 'Project'
        and isinstance(func.value.value, ast.Name)
        and func.value.value.id == 'edi'
        and len(call.args) == 1
        and not call.keywords
    )


def supported_loads(tree: ast.Module) -> dict[int, str]:
    """The paths of the loads in the one form, by the ``id`` of their ``Project.load`` node."""
    found = {}
    for statement in tree.body:
        if is_load_statement(statement):
            call = statement.value
            first = call.args[0]
            literal = isinstance(first, ast.Constant) and isinstance(first.value, str)
            found[id(call.func)] = first.value if literal else '<not a literal>'
    return found


def loads(code: list[str]) -> list[str]:
    """The path of every ``Project.load`` in the code, in order.

    A load in the one form (``LOAD_FORM``) gives its literal path, or ``<not a literal>``. Any
    other mention of ``Project.load``, in any expression or position, reads as
    ``<unsupported placement>``, and code that does not parse as ``<no parse>``, so either fails
    the one-load rule. A load in a comment or a string is no load.
    """
    paths: list[str] = []
    for source in code:
        try:
            tree = ast.parse(source)
        except SyntaxError:
            paths.append('<no parse>')
            continue
        supported = supported_loads(tree)
        mentions = [node for node in ast.walk(tree) if is_project_load(node)]
        mentions.sort(key=lambda node: (node.lineno, node.col_offset))
        paths.extend(supported.get(id(node), '<unsupported placement>') for node in mentions)
    return paths


def notebook_code(notebook: Path) -> list[str]:
    cells = json.loads(read(notebook))['cells']
    return [
        ''.join(cell['source']) if isinstance(cell['source'], list) else cell['source']
        for cell in cells
        if cell.get('cell_type') == 'code'
    ]


def check_project(folder: Path, case: str, problems: list[str]) -> str | None:
    project_edi = folder / 'project' / 'project.edi'
    if not project_edi.is_file():
        problems.append(f'{case}: no project/project.edi')
        return None
    name = metadata_value(project_edi, '_metadata.name')
    if name != case:
        problems.append(f'{case}: project/project.edi names itself {name!r}')
    if not (folder / 'index.md').is_file():
        problems.append(f'{case}: no index.md page')
    return metadata_value(project_edi, '_metadata.title')


def entries(sources: str) -> list[str]:
    """The Sources section's list items, table rows and paragraphs, each with its wrapped lines."""
    items: list[str] = []
    for line in sources.splitlines():
        if not line.strip():
            items.append('')
        elif line.lstrip().startswith(('- ', '* ', '|')) or not items:
            items.append(line)
        else:
            items[-1] += ' ' + line.strip()
    return [item for item in items if item]


def check_provenance(folder: Path, case: str, problems: list[str]) -> int:
    provenance = folder / 'PROVENANCE.md'
    if not provenance.is_file():
        problems.append(f'{case}: no PROVENANCE.md')
        return 0
    match = SOURCES.search(read(provenance))
    if match is None:
        problems.append(f'{case}: PROVENANCE.md has no "## Sources" section')
    sources = match.group('body') if match else ''
    data = folder / 'data'
    files = sorted(path for path in data.rglob('*') if path.is_file()) if data.is_dir() else []
    for path in files:
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        named = [entry for entry in entries(sources) if path.name in entry]
        relative = path.relative_to(folder).as_posix()
        if not named:
            problems.append(f'{case}: {relative} is not named in the Sources')
        elif not any(digest in line for line in named):
            problems.append(f'{case}: {relative} is named in the Sources without its sha256')
    return len(files)


def check_tutorial(root: Path, case: str, problems: list[str]) -> str | None:
    expected = [f'../cli/{case}/project']
    source = root / TUTORIALS_DIR / f'{case}.py'
    notebook = root / TUTORIALS_DIR / f'{case}.ipynb'
    source_loads = loads([read(source)]) if source.is_file() else None
    notebook_loads = loads(notebook_code(notebook)) if notebook.is_file() else None
    if source_loads is None:
        problems.append(f'{case}: no tutorial {source.relative_to(root)}')
    elif source_loads != expected:
        problems.append(f'{case}: its tutorial must load {expected[0]} once, not {source_loads}')
    if notebook_loads is None:
        problems.append(f'{case}: no notebook {notebook.relative_to(root)}')
    elif notebook_loads != expected:
        problems.append(f'{case}: its notebook must load {expected[0]} once, not {notebook_loads}')
    return source.relative_to(root).as_posix() if source_loads is not None else None


def exclusion_entries(root: Path, problems: list[str]) -> list[str]:
    try:
        declaration = yaml.safe_load(read(root / EXCLUSIONS)) or {}
        return [str(entry['notebook']) for entry in declaration.get('excluded', [])]
    except (OSError, yaml.YAMLError, KeyError, TypeError, AttributeError) as error:
        problems.append(f'{EXCLUSIONS}: cannot be read ({error})')
        return []


def check(root: Path) -> list[str]:
    """Every problem the catalogue under ``root`` has; empty when every case has all its forms."""
    return survey(root)[0]


def survey(root: Path) -> tuple[list[str], list[tuple[str, str | None, str | None, int]]]:
    """The problems, and each case's title, tutorial and number of data files."""
    problems: list[str] = []
    ids, cases = registry_from_yaml(root, problems)
    cmake_ids, cmake_cases = registry_as_cmake_reads_it(root)
    if ids and (ids, cases) != (cmake_ids, cmake_cases):
        problems.append(
            f'{REGISTRY}: as YAML, {len(ids)} projects and the cases {cases}; as the app reads '
            f'it, {len(cmake_ids)} projects and the cases {cmake_cases}'
        )
    excluded = exclusion_entries(root, problems)
    facts = []
    for case in cases:
        folder = root / CLI_DIR / case
        title = check_project(folder, case, problems)
        data_files = check_provenance(folder, case, problems)
        tutorial = check_tutorial(root, case, problems)
        if (count := excluded.count(f'{case}.ipynb')) != 1:
            problems.append(f'{case}: {EXCLUSIONS} lists its notebook {count} times')
        facts.append((case, title, tutorial, data_files))
    known = set(cases)
    problems.extend(
        f"{path.relative_to(root)} is not a catalogue case's tutorial"
        for path in sorted((root / TUTORIALS_DIR).iterdir())
        if path.name not in NOT_TUTORIALS
        and not (path.suffix in {'.py', '.ipynb'} and path.stem in known)
    )
    problems.extend(
        f"{EXCLUSIONS}: {entry} is not a catalogue case's notebook"
        for entry in excluded
        if not (entry.endswith('.ipynb') and entry.removesuffix('.ipynb') in known)
    )
    problems.extend(
        f'{fixture}: a test fixture has an index.md page'
        for fixture in ids
        if fixture not in known and (root / CLI_DIR / fixture / 'index.md').exists()
    )
    return problems, facts


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split('\n\n', 1)[0])
    parser.add_argument('--root', type=Path, default=ROOT, help='the edi tree (default: this one)')
    # Checking is all it does; the flag matches tools/dev/example_metadata.py --check.
    parser.add_argument('--check', action='store_true', help='check the catalogue (the default)')
    args = parser.parse_args(argv)
    problems, facts = survey(args.root.resolve())
    if problems:
        for problem in problems:
            print(f'example catalogue: {problem}', file=sys.stderr)
        print(f'example catalogue: {len(problems)} problem(s)', file=sys.stderr)
        return 1
    for case, title, tutorial, data_files in facts:
        print(f'{case}\t{title}\t{tutorial}\t{data_files} data file(s)')
    print(f'example catalogue: {len(facts)} cases, every form present')
    return 0


if __name__ == '__main__':
    sys.exit(main())
