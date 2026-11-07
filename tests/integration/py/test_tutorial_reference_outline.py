# SPDX-License-Identifier: BSD-3-Clause
"""Published notebooks follow the independently retained tutorial outlines."""

import ast
import json
import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
DIRECTORY = ROOT / 'docs/user/tutorials'
REFERENCE = json.loads((ROOT / 'tests/fixtures/tutorial_outline/outline.json').read_text())
NOTEBOOKS = sorted(p.stem for p in DIRECTORY.glob('*.py'))


def test_reference_covers_every_published_tutorial():
    assert set(NOTEBOOKS) == set(REFERENCE['notebooks']), (
        'Every tutorial published by the catalogue needs an independent section outline'
    )


@pytest.mark.parametrize('name', NOTEBOOKS)
def test_published_notebook_setup_and_clean_cells(name):
    notebook = json.loads((DIRECTORY / (name + '.ipynb')).read_text())
    cells = notebook['cells']
    assert [cell['id'] for cell in cells] == [str(i) for i in range(len(cells))], (
        'Published notebooks must number every cell sequentially from zero'
    )
    setup = ''.join(cells[0]['source'])
    literals = {
        node.value
        for node in ast.walk(ast.parse(setup))
        if isinstance(node, ast.Constant) and isinstance(node.value, str)
    }
    assert cells[0]['cell_type'] == 'code' and (
        any(re.search(r'\beasydiffraction\b', value) for value in literals)
        and 'https://enhantica.github.io/edi/pypi/simple/' in literals
    ), 'Every published notebook must declare its package and public index setup route'
    code = '\n'.join(''.join(cell['source']) for cell in cells if cell['cell_type'] == 'code')
    calls = [node for node in ast.walk(ast.parse(code)) if isinstance(node, ast.Call)]
    assert any(
        (isinstance(node.func, ast.Name) and node.func.id == 'download_data')
        or (isinstance(node.func, ast.Attribute) and node.func.attr == 'download_data')
        for node in calls
    ), 'Published tutorials must obtain their project data through the public collection API'
    assert 'assets/tutorials/' not in code, (
        'Notebook data setup must use the shared collection rather than website project ZIPs'
    )
    assert all(
        cell.get('execution_count') is None and not cell.get('outputs')
        for cell in cells
        if cell['cell_type'] == 'code'
    ), 'Published notebooks must clear execution counts and outputs'


@pytest.mark.parametrize('name', NOTEBOOKS)
def test_published_sections_follow_independent_technique_outline(name):
    notebook = json.loads((DIRECTORY / (name + '.ipynb')).read_text())
    sections = [
        match[1].strip().casefold()
        for cell in notebook['cells']
        if cell['cell_type'] == 'markdown'
        for line in ''.join(cell['source']).splitlines()
        if (match := re.match(r'^## (.+)', line))
    ]
    expected = [s.casefold() for s in REFERENCE['notebooks'][name]['sections']]
    cursor = iter(sections)
    missing = [title for title in expected if not any(title == actual for actual in cursor)]
    assert not missing, (
        'Tutorial sections must retain the independent technique outline in order; '
        f'missing sections: {missing}'
    )
