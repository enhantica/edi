# SPDX-License-Identifier: BSD-3-Clause
"""Publish portable Python tutorial bundles from the maintained example projects."""

import argparse
import hashlib
import json
import re
import zipfile
from pathlib import Path

from prepare_notebooks import notebook_from_source, setup_source

ROOT = Path(__file__).resolve().parents[1]
DATA_CALL = re.compile(r"edi\.download_data\('([\w.-]+)'")


def tutorial_bundle(
    notebook: Path, output: Path, published: Path | None = None
) -> tuple[str, str]:
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
            cases.update(DATA_CALL.findall(text))
            cell['execution_count'] = None
            cell['outputs'] = []
        cell['source'] = text.splitlines(keepends=True)
        cells.append(cell)
    description = next(
        (
            ''.join(cell['source']).strip().split('\n\n')[1]
            for cell in document['cells']
            if cell['cell_type'] == 'markdown'
            and ''.join(cell['source']).startswith('# ')
            and '\n\n' in ''.join(cell['source']).strip()
        ),
        '',
    )
    # A tutorial downloads its own case's entries only: its project, or its structure and data
    # (whose ids begin with the case id, edi ADR-0080).
    if not title or not cases or any(not case.startswith(notebook.stem) for case in cases):
        raise ValueError(f"Tutorial must download its own case's data: {notebook.name}")
    document['cells'] = [
        {
            **document['cells'][0],
            'source': setup_source(notebook.stem).splitlines(keepends=True),
        },
        *cells,
    ]
    for index, cell in enumerate(document['cells']):
        cell['id'] = str(index)
    folder = published or output.parent
    folder.mkdir(parents=True, exist_ok=True)
    text = json.dumps(document, ensure_ascii=False, indent=1) + '\n'
    (folder / notebook_name).write_text(text, encoding='utf-8')
    import jupytext  # noqa: PLC0415 - only the site build needs it

    source_text = jupytext.writes(jupytext.reads(text, fmt='ipynb'), fmt='py:percent')
    (folder / notebook.with_suffix('.py').name).write_text(source_text, encoding='utf-8')
    case = ROOT / 'docs/user/cli' / notebook.stem
    with zipfile.ZipFile(output, 'w', zipfile.ZIP_DEFLATED) as archive:
        archive.writestr(notebook_name, json.dumps(document, ensure_ascii=False, indent=1))
        archive.write(case / 'PROVENANCE.md', 'PROVENANCE.md')
        for path in sorted((case / 'project').rglob('*')):
            if path.is_file():
                archive.write(path, path.relative_to(case).as_posix())
    return title, ' '.join(description.split())


def tutorial_entry(folder: Path, stem: str, title: str, description: str, order: int) -> dict:
    """One tutorial in the collection format (ADR-0075): its notebook and Python source."""
    files = []
    for suffix, file_format in (('.ipynb', 'ipynb'), ('.py', 'py')):
        data = (folder / (stem + suffix)).read_bytes()
        files.append({
            'path': stem + suffix,
            'format': file_format,
            'sha256': hashlib.sha256(data).hexdigest(),
            'bytes': len(data),
        })
    return {
        'id': stem,
        'kind': 'tutorial',
        'name': title,
        'description': description,
        'order': order,
        'files': files,
    }


def render_tutorials(output: Path, published: Path) -> None:
    """Build the downloadable examples and the tutorial index.

    The ZIPs go to `output`; each notebook, its Python source and `index.json` go to `published`,
    which the site serves at `tutorials/` for list_tutorials and download_tutorial (ADR-0075).
    """
    output.mkdir(parents=True, exist_ok=True)
    # The run notebooks under docs/user/tutorials are left as they are: the bundles are made
    # from the sources, and the docs pages from the run notebooks (pixi run notebooks-run).
    entries = []
    for notebook in sorted((ROOT / 'docs/user/tutorials').glob('*.py')):
        name = notebook.stem + '.zip'
        title, description = tutorial_bundle(notebook, output / name, published)
        entries.append(
            tutorial_entry(published, notebook.stem, title, description, len(entries) + 1)
        )
    # What list_tutorials and download_tutorial read, in Python and python -m edi (ADR-0075).
    index = {'schema': 'edi-data-index/1', 'entries': entries}
    (published / 'index.json').write_text(
        json.dumps(index, ensure_ascii=False, indent=1) + '\n', 'utf-8'
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True, help='folder for the example ZIPs')
    parser.add_argument(
        '--published',
        type=Path,
        default=ROOT / 'website/.tutorials',
        help='folder for the notebooks, their Python sources and index.json',
    )
    args = parser.parse_args()
    render_tutorials(args.output, args.published)


if __name__ == '__main__':
    main()
