# SPDX-License-Identifier: BSD-3-Clause
"""The notebook Colab opens and the notebook in the download ZIP carry the same cells.

Both are generated from the tutorial's .py source; the ZIP only swaps in its portable setup and
project-relative paths. Every one ends with the interactive report, outputs are cleared and cell
IDs count from zero, and the committed notebooks are exactly what generation writes.
"""

import json
import re
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
    assert committed == colab
    assert colab['cells'][-1]['source'] == REPORT
    assert text(colab['cells'][-2]).startswith('## Explore the interactive report')

    archive = tmp_path / f'{source.stem}.zip'
    render_tutorials.tutorial_bundle(source, archive)
    with zipfile.ZipFile(archive) as bundle:
        portable = json.loads(bundle.read(source.with_suffix('.ipynb').name))
    assert portable['cells'][-1]['source'] == REPORT
    path = re.compile(r'\.\./cli/[\w.-]+/project')
    shared = [
        (cell['cell_type'], path.sub('project', text(cell)))
        for cell in colab['cells'][1:]
        if not text(cell).startswith('> This tutorial is not run')
    ]
    assert [(cell['cell_type'], text(cell)) for cell in portable['cells'][1:]] == shared
    for notebook in (colab, portable):
        assert [cell['id'] for cell in notebook['cells']] == [
            str(i) for i in range(len(notebook['cells']))
        ]
        for cell in notebook['cells']:
            if cell['cell_type'] == 'code':
                assert cell['outputs'] == [] and cell['execution_count'] is None
