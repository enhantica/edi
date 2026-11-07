# SPDX-License-Identifier: BSD-3-Clause
"""Convert tutorial Python sources to clean notebooks with a setup cell."""

import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PACKAGE_INDEX = 'https://enhantica.github.io/edi/pypi/simple/'
INSTALL = Path(__file__).with_name('notebook_install.py')


def setup_source(case: str, *, portable: bool = False, index: str = PACKAGE_INDEX) -> str:
    """Install the Python package when needed and provide project files in Colab.

    The install code is ``notebook_install.py``, copied in whole so the notebook needs nothing
    else; ADR-0018 explains how it keeps the package to the wheel our index lists.
    """
    relative = 'project' if portable else f'../cli/{case}/project'
    install = INSTALL.read_text(encoding='utf-8').split('\n', 2)[2]
    return (
        '# Install EasyDiffraction and prepare the example when running in Colab.\n'
        + install
        + f'\ninstall_edi({index!r})\n\n'
        'import io\n'
        'import os\n'
        'import tempfile\n'
        'import urllib.request\n'
        'import zipfile\n'
        'from pathlib import Path\n\n'
        'if "google.colab" in sys.modules:\n'
        '    workspace = Path(tempfile.mkdtemp(prefix="edi-tutorial-"))\n'
        '    (workspace / "notebooks").mkdir()\n'
        '    os.chdir(workspace / "notebooks")\n'
        f'    target = Path({relative!r}).parent.resolve()\n'
        '    target.mkdir(parents=True, exist_ok=True)\n'
        f'    url = "https://enhantica.github.io/edi/assets/tutorials/{case}.zip"\n'
        '    with urllib.request.urlopen(url, timeout=60) as response:\n'
        '        data = response.read()\n'
        '    with zipfile.ZipFile(io.BytesIO(data)) as bundle:\n'
        '        for member in bundle.infolist():\n'
        '            if not (target / member.filename).resolve().is_relative_to(target):\n'
        '                raise ValueError("Unexpected path in tutorial bundle")\n'
        '        bundle.extractall(target)\n'
    )


REPORT_CELLS = (
    {
        'cell_type': 'markdown',
        'metadata': {},
        'source': (
            '## Explore the interactive report\n\n'
            'Run the cell and trust the notebook to interact with the report. '
            'It includes Plotly plots and three.js structures where available.'
        ),
    },
    {
        'cell_type': 'code',
        'execution_count': None,
        'metadata': {},
        'outputs': [],
        'source': 'project.report.html_offline = True\nproject.report',
    },
)


def notebook_from_source(source: Path) -> dict:
    """Regenerate all cells from the Python source with stable sequential IDs."""
    import jupytext  # noqa: PLC0415 - the setup cell alone is used where jupytext is absent

    notebook = dict(jupytext.read(source, fmt='py:percent'))
    notebook['cells'].insert(
        0,
        {
            'cell_type': 'code',
            'execution_count': None,
            'metadata': {'tags': ['hide-in-docs']},
            'outputs': [],
            'source': setup_source(source.stem),
        },
    )
    # Colab opens this notebook and the ZIP carries the same cells, so both end with the report.
    notebook['cells'].extend(dict(cell) for cell in REPORT_CELLS)
    for index, cell in enumerate(notebook['cells']):
        cell['id'] = str(index)
        cell['source'] = ''.join(cell['source']).splitlines(keepends=True)
        if cell['cell_type'] == 'code':
            cell['execution_count'] = None
            cell['outputs'] = []
    return notebook


def prepare_notebooks(directory: Path) -> None:
    """Write the generated notebook beside each editable tutorial source."""
    for source in sorted(directory.glob('*.py')):
        source.with_suffix('.ipynb').write_text(
            json.dumps(notebook_from_source(source), ensure_ascii=False, indent=1) + '\n',
            encoding='utf-8',
        )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('directory', nargs='?', type=Path, default=ROOT / 'docs/user/tutorials')
    args = parser.parse_args()
    prepare_notebooks(args.directory)


if __name__ == '__main__':
    main()
