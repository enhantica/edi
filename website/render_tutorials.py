# SPDX-License-Identifier: BSD-3-Clause
"""Publish portable Python tutorial bundles from the maintained example projects."""

import argparse
import json
import re
import subprocess
import zipfile
from pathlib import Path
from urllib.parse import quote

from prepare_notebooks import notebook_from_source, prepare_notebooks, setup_source

ROOT = Path(__file__).resolve().parents[1]
PROJECT_PATH = re.compile(r'\.\./cli/([\w.-]+)/project')
START = '<!-- python-tutorials -->'
END = '<!-- /python-tutorials -->'


def tutorial_bundle(notebook: Path, output: Path) -> str:
    """Bundle a notebook and its exact starting project for local execution."""
    document = notebook_from_source(notebook)
    notebook_name = notebook.with_suffix('.ipynb').name
    title = ''
    cases = set()
    cells = []
    for cell in document['cells'][1:]:
        text = ''.join(cell['source'])
        if cell['cell_type'] == 'markdown':
            if not title and text.startswith('# '):
                title = text.splitlines()[0][2:]
            if text.startswith('> This tutorial is not run'):
                continue
        else:
            cases.update(PROJECT_PATH.findall(text))
            text = PROJECT_PATH.sub('project', text)
            cell['execution_count'] = None
            cell['outputs'] = []
        cell['source'] = text.splitlines(keepends=True)
        cells.append(cell)
    if not title or cases != {notebook.stem}:
        raise ValueError(f'Tutorial must name its starting project: {notebook.name}')
    cells.extend([
        {
            'cell_type': 'markdown',
            'id': 'interactive-report-heading',
            'metadata': {},
            'source': [
                '## Explore the interactive report\n',
                '\n',
                (
                    'Run the cell and trust the notebook to interact with the report. '
                    'It includes Plotly plots and three.js structures where available.'
                ),
            ],
        },
        {
            'cell_type': 'code',
            'id': 'interactive-report',
            'execution_count': None,
            'metadata': {},
            'outputs': [],
            'source': [
                'project.report.html_offline = True\n',
                'project.report',
            ],
        },
    ])
    document['cells'] = [
        {
            **document['cells'][0],
            'source': setup_source(notebook.stem, portable=True).splitlines(keepends=True),
        },
        *cells,
    ]
    for index, cell in enumerate(document['cells']):
        cell['id'] = str(index)
    case = ROOT / 'docs/user/cli' / notebook.stem
    with zipfile.ZipFile(output, 'w', zipfile.ZIP_DEFLATED) as archive:
        archive.writestr(notebook_name, json.dumps(document, ensure_ascii=False, indent=1))
        archive.write(case / 'PROVENANCE.md', 'PROVENANCE.md')
        for path in sorted((case / 'project').rglob('*')):
            if path.is_file():
                archive.write(path, path.relative_to(case).as_posix())
    return title


def render_tutorials(output: Path, source: str) -> str:
    """Build the downloadable examples and render the catalogue."""
    output.mkdir(parents=True, exist_ok=True)
    prepare_notebooks(ROOT / 'docs/user/tutorials')
    revision = subprocess.check_output(
        ['git', '-C', str(ROOT), 'rev-parse', 'HEAD'], text=True
    ).strip()
    rows = []
    for notebook in sorted((ROOT / 'docs/user/tutorials').glob('*.py')):
        name = notebook.stem + '.zip'
        title = tutorial_bundle(notebook, output / name)
        colab = (
            'https://colab.research.google.com/github/enhantica/edi/blob/'
            f'{revision}/docs/user/tutorials/{quote(notebook.with_suffix(".ipynb").name)}'
        )
        rows.append(
            f'| {title} | [Download notebook and project](../../assets/tutorials/{name}) '
            f'| [Open in Colab]({colab}) |'
        )
    before, rest = source.split(START, 1)
    _, after = rest.split(END, 1)
    table = '\n'.join(['| Tutorial | Files | Google Colab |', '| --- | --- | --- |', *rows])
    return f'{before}{START}\n\n{table}\n\n{END}{after}'


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    source = (ROOT / 'website/surfaces/docs/python/examples/index.md').read_text(encoding='utf-8')
    render_tutorials(args.output, source)


if __name__ == '__main__':
    main()
