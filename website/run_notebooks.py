# SPDX-License-Identifier: BSD-3-Clause
"""Run the tutorial notebooks and write their outputs into them, for the docs pages.

    python website/run_notebooks.py [CASE ...]        # pixi run notebooks-run

Each tutorial source becomes its notebook (``prepare_notebooks``) and is run in a fresh folder,
cell by cell; a cell that fails fails the run, naming the notebook. With ``EDI_SOURCE_BUILD`` set
the install cell (tagged ``hide-in-docs``) is skipped, as this checkout's edi is used; the cell
stays in the written notebook. ``EDI_COLLECTION`` points the downloads at another collection.
"""

from __future__ import annotations

import argparse
import copy
import json
import os
import sys
import tempfile
import warnings
from pathlib import Path

import nbformat
from prepare_notebooks import notebook_from_source
from render_notebook_pages import coalesce_streams

# nbclient's import parses a date as Python 3.14 deprecates; the warning says nothing of the run.
with warnings.catch_warnings():
    warnings.simplefilter('ignore', DeprecationWarning)
    from nbclient import NotebookClient

ROOT = Path(__file__).resolve().parents[1]
TUTORIALS = ROOT / 'docs/user/tutorials'
HIDDEN = 'hide-in-docs'
TIMEOUT = 900


def run(source: Path) -> Path:
    """Run one tutorial and write its notebook, with the outputs, beside its source."""
    document = notebook_from_source(source)
    for cell in document['cells']:
        cell['source'] = ''.join(cell['source'])
    notebook = nbformat.from_dict(document)
    skip = bool(os.environ.get('EDI_SOURCE_BUILD'))
    hidden = [
        index
        for index, cell in enumerate(notebook.cells)
        if skip and HIDDEN in cell.metadata.get('tags', [])
    ]
    runnable = copy.deepcopy(notebook)
    runnable.cells = [cell for index, cell in enumerate(runnable.cells) if index not in hidden]
    with tempfile.TemporaryDirectory(prefix=f'edi-tutorial-{source.stem}-') as folder:
        resources = {'metadata': {'path': folder}}
        NotebookClient(
            runnable, timeout=TIMEOUT, kernel_name='python3', resources=resources
        ).execute()
    # Each print is its own stream output; joined, a fit's progress table is one block.
    for cell in runnable.cells:
        if cell.cell_type == 'code':
            cell.outputs = [nbformat.from_dict(o) for o in coalesce_streams(cell.outputs)]
    ran = iter(runnable.cells)
    notebook.cells = [
        cell if index in hidden else next(ran) for index, cell in enumerate(notebook.cells)
    ]
    target = source.with_suffix('.ipynb')
    target.write_text(json.dumps(notebook, ensure_ascii=False, indent=1) + '\n', encoding='utf-8')
    return target


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split('\n\n', 1)[0])
    parser.add_argument('cases', nargs='*', help='case ids; all tutorials without any')
    args = parser.parse_args()
    sources = [TUTORIALS / f'{case}.py' for case in args.cases] or sorted(TUTORIALS.glob('*.py'))
    failed = []
    for source in sources:
        try:
            print(f'ran {run(source)}', flush=True)
        except Exception as error:  # noqa: BLE001 - every notebook is run and every failure named
            failed.append(source.stem)
            print(f'FAILED {source.stem}: {error}', file=sys.stderr, flush=True)
    if failed:
        print(f'{len(failed)} notebook(s) failed: {", ".join(failed)}', file=sys.stderr)
    return 1 if failed else 0


if __name__ == '__main__':
    raise SystemExit(main())
