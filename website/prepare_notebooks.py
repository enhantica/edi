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


# Character widths of the chips' 12 px sans-serif text, in px, so each chip is sized without a font
# library: narrow, wide and other characters, and capitals.
NARROW = set("iljtfrI.,:;|!' ")
WIDE = set('mwMW')


def text_width(text: str, size: float = 12.0) -> float:
    """An upper estimate of a short label's width in a common sans-serif at `size` px."""
    total = 0.0
    for char in text:
        if char in NARROW:
            total += 0.32
        elif char in WIDE:
            total += 0.86
        elif char.isupper() or char.isdigit():
            total += 0.66
        else:
            total += 0.56
    return total * size


def chip_icon(icon: str, color: str, x: float, height: int, size: int) -> tuple[str, int]:
    """A tag's icon as a nested SVG at `x`, vertically centred, and its width; none for no icon."""
    if not icon:
        return '', 0
    svg = (ICONS / f'{icon}.svg').read_text(encoding='utf-8')
    box = re.search(r'viewBox="([\d. ]+)"', svg)
    view = box.group(1) if box else '0 0 512 512'
    _, _, view_width, view_height = (float(value) for value in view.split())
    width = round(size * view_width / view_height)
    paths = ''.join(re.findall(r'<path[^>]*/>', svg))
    nested = (
        f'<svg x="{x}" y="{(height - size) / 2}" width="{width}" height="{size}" '
        f'viewBox="{view}" fill="{color}">{paths}</svg>'
    )
    return nested, width


def tag_chip(label: str, icon: str, color: str) -> str:
    """One tag as a self-contained image, the docs' chip: a tinted rounded box, icon and label.

    It is drawn in an SVG with its own width and height, since Colab drops every style attribute.
    The label stays the image's alt text, readable and searchable.
    """
    height, pad, size = 22, 7, 12
    glyph, icon_width = chip_icon(icon, color, pad, height, size)
    text_x = pad + (icon_width + 4 if icon_width else 0)
    width = round(text_x + text_width(label, size) + pad)
    baseline = f'{height / 2 + size * 0.36:.1f}'
    escaped = label.replace('&', '&amp;').replace('<', '&lt;')
    chip = (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
        f'viewBox="0 0 {width} {height}"><rect width="{width}" height="{height}" rx="4" '
        f'fill="{color}" fill-opacity="0.13"/>{glyph}<text x="{text_x}" y="{baseline}" '
        f'font-family="Noto Sans, Segoe UI, Helvetica, Arial, sans-serif" font-size="{size}" '
        f'fill="{color}">{escaped}</text></svg>'
    )
    data = base64.b64encode(chip.encode('utf-8')).decode('ascii')
    alt = label.replace('"', '&quot;')
    return (
        f'<img src="data:image/svg+xml;base64,{data}" alt="{alt}" '
        f'width="{width}" height="{height}">'
    )


def case_record(case: str) -> dict | None:
    """The case's record (tools/checks/case_records.py), or None."""
    sys.path.insert(0, str(ROOT / 'tools/checks'))
    from case_records import records  # noqa: PLC0415 - the repository's own check

    return next((item for item in records(ROOT) if item['id'] == case), None)


def tags_cell(case: str) -> dict | None:
    """The tutorial's tags as the docs' chips, one image each, a gap between; None for no case.

    One cell under the title, shown alike in Jupyter, Colab and the docs page.
    """
    record = case_record(case)
    if record is None or not record['tags']:
        return None
    registry = json.loads((ROOT / 'app/examples/tags.json').read_text(encoding='utf-8'))
    chips = []
    for tag in record['tags']:
        entry = registry['tags'][tag['facet']][tag['value']]
        color = registry['tones'][entry['tone']]['light']
        chips.append(tag_chip(tag['label'], entry.get('icon', ''), color))
    return {'cell_type': 'markdown', 'metadata': {}, 'source': '&nbsp; '.join(chips)}


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
    if title is not None:
        # The title alone, as the case record names it, then the tags, then the introduction (the
        # tags record: directly under the title, before the text).
        lines = ''.join(notebook['cells'][title]['source']).split('\n')
        record = case_record(source.stem)
        heading = f'# {record["title"]}' if record and record.get('title') else lines[0]
        rest = '\n'.join(lines[1:]).strip()
        notebook['cells'][title] = {**notebook['cells'][title], 'source': heading}
        after = [tags] if tags else []
        if rest:
            after.append({'cell_type': 'markdown', 'metadata': {}, 'source': rest})
        notebook['cells'][title + 1 : title + 1] = after
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
