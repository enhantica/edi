# SPDX-License-Identifier: BSD-3-Clause
"""The notebook Colab opens and the notebook in the download ZIP carry the same cells.

Both are generated from the tutorial's .py source; the ZIP only swaps in its portable setup and
project-relative paths. Every one includes the report or step displays, cell IDs count from zero,
and committed executed notebooks retain the same generated teaching cells.
"""

import json
import re
import subprocess
import sys
import zipfile
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'website'))
import prepare_notebooks  # noqa: E402
import render_tutorials  # noqa: E402

SOURCES = sorted((ROOT / 'docs/user/tutorials').glob('*.py'))
REPORT = ['project.report.html_offline = True\n', 'project.report']


def text(cell):
    return ''.join(cell['source'])


@pytest.mark.parametrize('source', SOURCES, ids=lambda path: path.stem)
def test_colab_and_zip_notebooks_share_the_report_and_the_committed_file_is_generated(
    source, tmp_path
):
    colab = prepare_notebooks.notebook_from_source(source)
    committed = json.loads(source.with_suffix('.ipynb').read_text(encoding='utf-8'))

    def teaching_cells(document):
        return [
            (cell['cell_type'], text(cell), cell.get('metadata', {}).get('tags', []), cell['id'])
            for cell in document['cells']
        ]

    assert teaching_cells(committed) == teaching_cells(colab), (
        'Run outputs and kernel metadata preserve every generated teaching cell and tag.'
    )
    assert any(
        'project.display' in text(cell) or 'project.report' in text(cell)
        for cell in colab['cells']
        if cell['cell_type'] == 'code'
    ), 'Every generated notebook includes the report or the shared step displays.'

    archive = tmp_path / f'{source.stem}.zip'
    render_tutorials.tutorial_bundle(source, archive)
    with zipfile.ZipFile(archive) as bundle:
        portable = json.loads(bundle.read(source.with_suffix('.ipynb').name))
    path = re.compile(r'\.\./cli/[\w.-]+/project')
    shared = [
        (cell['cell_type'], path.sub('project', text(cell)))
        for cell in colab['cells'][1:]
        if not text(cell).startswith('> This tutorial is not run')
    ]
    assert [(cell['cell_type'], text(cell)) for cell in portable['cells'][1:]] == shared, (
        'Colab and ZIP notebooks share the report and the committed file is generated.'
    )
    for notebook in (colab, portable):
        assert [cell['id'] for cell in notebook['cells']] == [
            str(i) for i in range(len(notebook['cells']))
        ], 'Colab and ZIP notebooks share the report and the committed file is generated.'
        for cell in notebook['cells']:
            if cell['cell_type'] == 'code':
                assert cell['outputs'] == [] and cell['execution_count'] is None, (
                    'Colab and ZIP notebooks share the report and the committed file is generated.'
                )


def test_the_renderer_entry_point_publishes_the_tutorial_index(tmp_path):
    subprocess.run(
        [
            sys.executable,
            str(ROOT / 'website/render_tutorials.py'),
            '--output',
            str(tmp_path / 'zips'),
            '--published',
            str(tmp_path / 'published'),
        ],
        check=True,
        capture_output=True,
    )
    index = json.loads((tmp_path / 'published/index.json').read_text(encoding='utf-8'))
    files = [file['path'] for entry in index['entries'] for file in entry['files']]
    assert index['entries'] and all((tmp_path / 'published' / path).is_file() for path in files), (
        'The renderer run on its own must publish every tutorial file its index lists.'
    )
    assert {Path(path).suffix for path in files} == {'.ipynb', '.py'}, (
        'Each tutorial must be published as a notebook and as Python.'
    )
