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
- a tutorial or its notebook fetches anything but its own case's collection entries (each
  ``edi.download_data('<id>')`` names the case or an entry ``<case>-…``, as a literal), fetches
  nothing, or loads a project other than its case's: a load is one top-level statement of one
  form, ``project = edi.Project.load(project_path)``, after a top-level
  ``project_path = edi.download_data('<case>', ...)`` (ADR-0075). Any other mention of
  ``Project.load`` fails. A notebook's cells are read as one program, without its install magics;
- a file under a case's ``data/`` is not named in its Sources with its sha256;
- a tutorial, notebook or exclusion entry names something that is not a case, or a fixture has an
  ``index.md`` page (a fixture's page is its ``README.md``);
- the ``app-only`` rows, app examples without their catalogue form yet, are not exactly the
  declared list below with its reason, or a row is both a case and app-only;
- a case's record lacks a field or an artefact (``case_records.py``, edi ADR-0080).

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

sys.path.insert(0, str(Path(__file__).resolve().parent))
import case_records  # beside this script

ROOT = Path(__file__).resolve().parents[2]
CLI_DIR = Path('docs') / 'user' / 'cli'
TUTORIALS_DIR = Path('docs') / 'user' / 'tutorials'
REGISTRY = CLI_DIR / 'projects.yml'
EXCLUSIONS = TUTORIALS_DIR / 'execution-exclusions.yml'
# The app's CMake reads the registry with these patterns (app/CMakeLists.txt).
CMAKE_LINE = re.compile(r'^  - id: |^    user-facing: |^    app-only: ')
CMAKE_ID = re.compile(r'^  - id: *(.+)$')
CMAKE_CASE = re.compile(r'^    user-facing: *true$|^    app-only: ')
# App examples that have no catalogue form yet (ADR-0048). The list only shrinks: each leaves it
# when it becomes a catalogue case, and no other project may be app-only. It is empty now that the
# three single-crystal examples are cases.
APP_ONLY: dict[str, str] = {}
SOURCES = re.compile(r'^## Sources\s*$(?P<body>.*?)(?=^## |\Z)', re.MULTILINE | re.DOTALL)
# Files in the tutorials folder that are not tutorials.
NOT_TUTORIALS = {'index.md', 'execution-exclusions.yml'}


def read(path: Path) -> str:
    return path.read_text(encoding='utf-8')


def registry_from_yaml(
    root: Path, problems: list[str]
) -> tuple[list[str], list[str], dict[str, object]]:
    try:
        rows = yaml.safe_load(read(root / REGISTRY))['projects']
        ids = [str(row['id']) for row in rows]
        cases = [str(row['id']) for row in rows if row.get('user-facing') is True]
        app_only = {str(row['id']): row['app-only'] for row in rows if 'app-only' in row}
    except (OSError, yaml.YAMLError, KeyError, TypeError) as error:
        problems.append(f'{REGISTRY}: cannot be read as YAML ({error})')
        return [], [], {}
    return ids, cases, app_only


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


def downloaded_case(statement: ast.stmt) -> str | None:
    """The case of a top-level ``project_path = edi.download_data('<id>', ...)``, else None."""
    if not (
        isinstance(statement, ast.Assign)
        and len(statement.targets) == 1
        and isinstance(statement.targets[0], ast.Name)
        and statement.targets[0].id == 'project_path'
        and isinstance(statement.value, ast.Call)
    ):
        return None
    call = statement.value
    func = call.func
    named = (
        isinstance(func, ast.Attribute)
        and func.attr == 'download_data'
        and isinstance(func.value, ast.Name)
        and func.value.id == 'edi'
    )
    first = call.args[0] if call.args else None
    if named and isinstance(first, ast.Constant) and isinstance(first.value, str):
        return first.value
    return None


def downloaded(case: str) -> str:
    """How ``loads`` names a load of the collection's copy of ``case``."""
    return f'edi.download_data({case!r})'


def supported_loads(tree: ast.Module) -> dict[int, str]:
    """The paths of the loads in the one form, by the ``id`` of their ``Project.load`` node."""
    found = {}
    case = None
    for statement in tree.body:
        # Any other binding of ``project_path`` forgets the download.
        if any(
            isinstance(node, ast.Name)
            and node.id == 'project_path'
            and isinstance(node.ctx, ast.Store)
            for node in ast.walk(statement)
        ):
            case = downloaded_case(statement)
        if is_load_statement(statement):
            call = statement.value
            first = call.args[0]
            if isinstance(first, ast.Constant) and isinstance(first.value, str):
                found[id(call.func)] = first.value
            elif isinstance(first, ast.Name) and first.id == 'project_path' and case:
                found[id(call.func)] = downloaded(case)
            else:
                found[id(call.func)] = '<not a literal>'
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


def fetched(source: str) -> list[str]:
    """The id of every ``edi.download_data(...)`` call, in order; ``<not a literal>`` otherwise."""
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return ['<no parse>']
    calls = [
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and node.func.attr == 'download_data'
    ]
    calls.sort(key=lambda node: (node.lineno, node.col_offset))
    return [
        call.args[0].value
        if call.args
        and isinstance(call.args[0], ast.Constant)
        and isinstance(call.args[0].value, str)
        else '<not a literal>'
        for call in calls
    ]


def check_tutorial(root: Path, case: str, problems: list[str]) -> str | None:
    """A tutorial builds its case from the collection's entries, or loads the case's project.

    A tutorial builds the case from its structures and data; a tutorial about loading a project
    loads its case's. Either way every file comes from the case's own entries.
    """
    source = root / TUTORIALS_DIR / f'{case}.py'
    notebook = root / TUTORIALS_DIR / f'{case}.ipynb'
    programs = {}
    if source.is_file():
        programs['tutorial'] = read(source)
    else:
        problems.append(f'{case}: no tutorial {source.relative_to(root)}')
    if notebook.is_file():
        # One program, as the kernel runs it; an install cell's `%pip` or `!` line is not Python.
        programs['notebook'] = '\n'.join(
            line[: len(line) - len(line.lstrip())] + 'pass'
            if line.lstrip().startswith(('%', '!'))
            else line
            for cell in notebook_code(notebook)
            for line in cell.splitlines()
        )
    else:
        problems.append(f'{case}: no notebook {notebook.relative_to(root)}')
    for kind, program in programs.items():
        found = loads([program])
        if found not in ([], [downloaded(case)]):
            problems.append(
                f'{case}: its {kind} may load only {downloaded(case)}, once, not {found}'
            )
        ids = fetched(program)
        if not ids:
            problems.append(f'{case}: its {kind} fetches nothing from the collection')
        problems.extend(
            f'{case}: its {kind} fetches {entry}, not one of its own entries'
            for entry in ids
            if entry != case and not entry.startswith(case + '-')
        )
    return source.relative_to(root).as_posix() if source.is_file() else None


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
    ids, cases, app_only = registry_from_yaml(root, problems)
    cmake_ids, cmake_cases = registry_as_cmake_reads_it(root)
    app_examples = [example for example in ids if example in cases or example in app_only]
    if ids and (ids, app_examples) != (cmake_ids, cmake_cases):
        problems.append(
            f'{REGISTRY}: as YAML, {len(ids)} projects and the app examples {app_examples}; '
            f'as the app reads it, {len(cmake_ids)} projects and the app examples {cmake_cases}'
        )
    if ids and app_only != APP_ONLY:
        problems.append(f'{REGISTRY}: the app-only rows are {app_only}, not {APP_ONLY}')
    problems.extend(
        f'{REGISTRY}: {both} is both a case and app-only' for both in cases if both in app_only
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
    if cases:
        problems.extend(case_records.problems(root))
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
