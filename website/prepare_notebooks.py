# SPDX-License-Identifier: BSD-3-Clause
"""Convert tutorial Python sources to clean notebooks with a setup cell."""

import argparse
import base64
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
# The package index the notebooks install from, and the release they install. The exact version
# keeps pip from taking the unrelated easydiffraction releases on pypi.org.
PACKAGE_INDEX = 'https://enhantica.github.io/edi-download/pypi/simple/'
PACKAGE_VERSION = '2026.11.0'


def setup_source(
    case: str,
    *,
    portable: bool = False,
    index: str = PACKAGE_INDEX,
    version: str = PACKAGE_VERSION,
) -> str:
    """The notebook's one install cell: diffraction-lib's, with EasyDiffraction's release added.

    It installs only when the package is missing, so a user's own environment is never reinstalled
    or upgraded (owner record 2026-11-09; any change needs the owner's word). The wheel brings
    everything a tutorial needs (edi ADR-0079). ``case`` and ``portable`` do not change the cell.
    """
    del case, portable
    return (
        '# Check whether easydiffraction is installed; install it if needed.\n'
        '# Required for remote environments such as Google Colab.\n'
        'import importlib.util\n'
        '\n'
        "if importlib.util.find_spec('easydiffraction') is None:\n"
        f'    %pip install easydiffraction=={version} --extra-index-url {index}\n'
    )


def data_source(case: str) -> str:
    """The lines that get a tutorial's project from EasyDiffraction's collection (ADR-0075)."""
    return (
        "# Get the tutorial's starting project from EasyDiffraction's collection.\n"
        f"project_path = edi.download_data({case!r}, destination='data')\n"
        'project = edi.Project.load(project_path)'
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


ICONS = ROOT / 'website/surfaces/overrides/.icons/fa5'


def tag_icon(name: str, color: str) -> str:
    """A tag's symbol as a small inline SVG image: the app's glyph in the tag's colour."""
    if not name:
        return ''
    svg = (ICONS / f'{name}.svg').read_text(encoding='utf-8')
    svg = svg.replace('<svg ', f'<svg fill="{color}" ', 1)
    data = base64.b64encode(svg.encode('utf-8')).decode('ascii')
    # Its size as attributes too: Colab drops the style, and an unsized image fills the cell.
    box = re.search(r'viewBox="0 0 ([\d.]+) ([\d.]+)"', svg)
    width = round(14 * float(box.group(1)) / float(box.group(2))) if box else 14
    return (
        f'<img src="data:image/svg+xml;base64,{data}" alt="" width="{width}" height="14" '
        'style="height:0.85em;width:auto;vertical-align:-0.1em;margin-right:0.3em">'
    )


def tags_cell(case: str) -> dict | None:
    """The tutorial's tags as small coloured labels with the app's symbols; None for no case.

    One cell under the title, shown alike in Jupyter, Colab and the docs page.
    """
    sys.path.insert(0, str(ROOT / 'tools/checks'))
    from case_records import records  # noqa: PLC0415 - the repository's own check

    record = next((item for item in records(ROOT) if item['id'] == case), None)
    if record is None or not record['tags']:
        return None
    registry = json.loads((ROOT / 'app/examples/tags.json').read_text(encoding='utf-8'))
    labels = []
    for tag in record['tags']:
        entry = registry['tags'][tag['facet']][tag['value']]
        color = registry['tones'][entry['tone']]['light']
        labels.append(
            f'<span style="color:{color};background:{color}21;border-radius:3px;'
            f'padding:0.1em 0.4em;font-size:0.85em">{tag_icon(entry.get("icon", ""), color)}'
            f'{tag["label"]}</span>'
        )
    return {'cell_type': 'markdown', 'metadata': {}, 'source': ' '.join(labels)}


def notebook_from_source(source: Path) -> dict:
    """Regenerate all cells from the Python source with stable sequential IDs."""
    import jupytext  # noqa: PLC0415 - the setup cell alone is used where jupytext is absent

    notebook = dict(jupytext.read(source, fmt='py:percent'))
    # The source's module docstring is for the repository, not a cell of the tutorial.
    first = notebook['cells'][0] if notebook['cells'] else None
    if (
        first
        and first['cell_type'] == 'code'
        and re.fullmatch(r'\s*("""|\'\'\').*?\1\s*', ''.join(first['source']), re.DOTALL)
    ):
        notebook['cells'] = notebook['cells'][1:]
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
    # The tags under the title, the one tags cell Jupyter, Colab and the docs page all show.
    tags = tags_cell(source.stem)
    title = next(
        (
            index
            for index, cell in enumerate(notebook['cells'])
            if cell['cell_type'] == 'markdown' and ''.join(cell['source']).startswith('# ')
        ),
        None,
    )
    if tags and title is not None:
        notebook['cells'].insert(title + 1, tags)
    # Colab opens this notebook and the ZIP carries the same cells, so both end with the report,
    # unless the tutorial shows its charts and tables step by step with project.display.
    if not any('project.display' in ''.join(cell['source']) for cell in notebook['cells']):
        notebook['cells'].extend(dict(cell) for cell in REPORT_CELLS)
    # The project comes from the collection, not from a repository path, in every notebook.
    load = f"project = edi.Project.load('../cli/{source.stem}/project')"
    for cell in notebook['cells']:
        if cell['cell_type'] == 'code' and load in ''.join(cell['source']):
            cell['source'] = ''.join(cell['source']).replace(load, data_source(source.stem))
    notebook['cells'] = [
        cell
        for cell in notebook['cells']
        if not (
            cell['cell_type'] == 'markdown'
            and ''.join(cell['source']).startswith('> This tutorial is not run')
        )
    ]
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
