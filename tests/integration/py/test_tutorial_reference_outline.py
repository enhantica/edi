# SPDX-License-Identifier: BSD-3-Clause
"""Every published notebook has an editable source and a clean declared setup route."""

import ast
import json
import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
DIRECTORY = ROOT / 'docs/user/tutorials'
SOURCE_NAMES = {path.stem for path in DIRECTORY.glob('*.py')}
NOTEBOOK_NAMES = {path.stem for path in DIRECTORY.glob('*.ipynb')}
NOTEBOOKS = sorted(SOURCE_NAMES | NOTEBOOK_NAMES)


def test_every_published_tutorial_has_source_and_notebook():
    assert NOTEBOOKS, 'The published tutorial catalogue must not be empty'
    assert SOURCE_NAMES == NOTEBOOK_NAMES, (
        'Every published notebook and editable tutorial source must have its matching pair'
    )


@pytest.mark.parametrize('name', NOTEBOOKS)
def test_published_notebook_setup_and_clean_cells(name):
    path = DIRECTORY / (name + '.ipynb')
    assert path.is_file(), 'Every tutorial selected for publication must have a notebook'
    notebook = json.loads(path.read_text(encoding='utf-8'))
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
