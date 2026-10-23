"""The owner-selected cases retain their identity across each public form."""

import ast
import hashlib
import json
import operator
import re
import shlex
from pathlib import Path

import pytest
import yaml

from tests.fixtures.excluded_display.historical_bytes import historical_excluded_bytes

ROOT = Path(__file__).resolve().parents[3]
CLI = ROOT / 'docs/user/cli'
TUTORIALS = ROOT / 'docs/user/tutorials'
FIXTURE = ROOT / 'tests/fixtures/example_catalogue'
SELECTION = json.loads((FIXTURE / 'catalogue-selection.json').read_text())['cases']
SELECTED = [row['id'] for row in SELECTION]
RETAINED = json.loads((FIXTURE / 'retained-projects.json').read_text())['projects']


def registry(root=ROOT):
    return yaml.safe_load((root / 'docs/user/cli/projects.yml').read_text())['projects']


def selected(root=ROOT):
    return [row['id'] for row in registry(root) if row.get('user-facing') is True]


def page_cases(path):
    links = re.findall(r'\]\(([^)]+)\)', path.read_text())
    cases = []
    for link in links:
        for part in link.split('/'):
            candidate = re.sub(r'\.(?:py|ipynb|md)$', '', part)
            if candidate.startswith('pd-') and candidate not in cases:
                cases.append(candidate)
    return cases


def load_paths(source):
    tree = ast.parse(source)
    paths = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call) or not isinstance(node.func, ast.Attribute):
            continue
        if node.func.attr == 'load' and ast.unparse(node.func.value).endswith('Project'):
            assert len(node.args) == 1 and isinstance(node.args[0], ast.Constant), (
                'A tutorial must load one explicit project path, checkable before execution'
            )
            paths.append(node.args[0].value)
    return paths


@pytest.mark.parametrize('surface', ['registry', 'metadata', 'cli-page', 'tutorial-page'])
def test_selected_cases_and_order_match_the_independent_owner_selection(surface):
    if surface == 'registry':
        actual = selected()
    elif surface == 'metadata':
        actual = list(json.loads((ROOT / 'app/examples/metadata.json').read_text())['examples'])
    else:
        actual = page_cases((CLI if surface == 'cli-page' else TUTORIALS) / 'index.md')
    assert actual == SELECTED, (
        'Every public catalogue must show the owner-selected cases in their requested order'
    )


@pytest.mark.parametrize('case', SELECTED)
def test_each_case_has_one_project_and_matching_tutorial_sources(case):
    directory = CLI / case
    for name in ['project/project.edi', 'index.md', 'PROVENANCE.md']:
        assert (directory / name).is_file(), 'Every selected case must have its project and guide'
    metadata = dict(
        shlex.split(line)
        for line in (directory / 'project/project.edi').read_text().splitlines()
        if line.startswith('_metadata.')
    )
    assert metadata['_metadata.name'] == case, 'The project and catalogue must use one case id'
    assert metadata['_metadata.authors'] == '.', 'Example authors must retain the chosen CIF null'
    source = TUTORIALS / f'{case}.py'
    notebook = TUTORIALS / f'{case}.ipynb'
    assert source.is_file() and notebook.is_file(), (
        'Every selected case must have both tutorial forms'
    )
    expected = [f'../cli/{case}/project']
    assert load_paths(source.read_text()) == expected, (
        'The tutorial must load its own catalogue project'
    )
    cells = json.loads(notebook.read_text())['cells']
    code = '\n'.join(''.join(cell['source']) for cell in cells if cell['cell_type'] == 'code')
    assert load_paths(code) == expected, 'Notebook and source must load the same catalogue project'
    assert all(not cell.get('outputs') for cell in cells), (
        'Disabled tutorials must have no saved outputs'
    )


def test_exclusions_name_every_selected_notebook_and_its_runner():
    rows = yaml.safe_load((TUTORIALS / 'execution-exclusions.yml').read_text())['excluded']
    expected = {
        f'{case}.ipynb': 'sequential-scan-tutorial'
        if case.endswith('_scan')
        else 'tutorial-runner'
        for case in SELECTED
    }
    assert len(rows) == len(expected), 'Every selected tutorial must have exactly one exclusion'
    assert {row['notebook']: row['unblocked_by'] for row in rows} == expected, (
        'Only selected tutorials may be excluded, with the matching ordinary or scan runner'
    )


@pytest.mark.parametrize(
    'record',
    [row for row in RETAINED if row['id'] != 'pd-xray-cwl_latp_scan-4f'],
    ids=operator.itemgetter('id'),
)
def test_old_projects_keep_their_files_pins_and_execution(record):
    case = record['id']
    directory = CLI / case
    paths = {
        path.relative_to(directory).as_posix(): path
        for path in (directory / 'project').rglob('*')
        if path.is_file()
    }
    paths['expected.json'] = directory / 'expected.json'
    assert set(paths) == set(record['sha256']), (
        'Retained fixtures must keep their complete original file inventory'
    )
    restored = {}
    for name, path in paths.items():
        raw = path.read_bytes()
        digest = hashlib.sha256(raw).hexdigest()
        if digest != record['sha256'][name]:
            raw = historical_excluded_bytes(name.removeprefix('project/'), raw)
        restored[name] = hashlib.sha256(raw).hexdigest()
    assert restored == record['sha256'], (
        'Retained fixture models and numerical expectations must remain byte-identical'
    )
    live = next(row for row in registry() if row['id'] == case)
    assert live['executing'] == record['executing'], (
        'Existing fixture tests must keep their execution status'
    )
    assert live.get('offline', False) == record.get('offline', False), (
        'Existing fixture cadence must be preserved'
    )
    assert not live.get('user-facing', False), 'Old variants must leave the user catalogue'
    assert not (directory / 'index.md').exists(), 'Fixture pages must leave the user navigation'
    assert (directory / 'README.md').is_file(), (
        'Fixture instructions must remain beside the project'
    )


@pytest.mark.parametrize('case', SELECTED)
def test_committed_data_has_a_source_licence_and_content_digest(case):
    directory = CLI / case
    provenance = (directory / 'PROVENANCE.md').read_text()
    assert '## Sources' in provenance, (
        'Each case must document its data sources in a Sources section'
    )
    sources = provenance.split('## Sources', 1)[1]
    for path in (directory / 'data').rglob('*'):
        if path.is_file():
            assert (
                path.name in sources and hashlib.sha256(path.read_bytes()).hexdigest() in sources
            ), 'Every committed dataset must be named with its actual content digest'
    assert re.search(r'licen[cs]e|CC[- ]BY|public domain', sources, re.IGNORECASE), (
        'Each data source must state its licence'
    )
