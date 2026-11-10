# SPDX-License-Identifier: BSD-3-Clause
"""Turn the run tutorial notebooks into native site pages, before Zensical builds the site.

Zensical cannot render notebooks, so each run notebook becomes a Markdown page: text cells as
they are, code cells as Python blocks, their outputs as text blocks, images and the HTML the
notebook showed (the report views of ``project.display``). A cell tagged ``hide-in-docs`` (the
install cell) is left out. Each page opens with Open in Google Colab and Download Notebook
buttons. The notebooks are run before, by ``pixi run notebooks-run``; this step never runs them
and refuses a notebook without outputs.
"""

from __future__ import annotations

import base64
import html
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path
from urllib.parse import quote

ROOT = Path(__file__).resolve().parents[1]
DOCS = Path(__file__).resolve().parent / 'surfaces/docs'
HIDDEN = 'hide-in-docs'
COLAB = 'https://colab.research.google.com/github/enhantica/edi/blob/{ref}/docs/user/tutorials/'


ANSI = re.compile(r'\x1b\[[0-9;]*[A-Za-z]')
# The site's text font (Zensical's default, as the built pages load it) and its brand colours.
SITE_FONT = 'Inter'
SITE_FONT_CSS = (
    'https://fonts.googleapis.com/css?family=Inter:300,400,400i,500,700&display=fallback'
)
BRAND_CSS = DOCS / 'assets/brand-colors.css'
# The site's table text as a built page computes it (Zensical's .md-typeset table: 12.8 px, the
# typeset colour), so a view's tables and charts read as the page's own tables.
SITE_TABLE_SIZE = '12.8px'
SITE_TEXT_COLOUR = 'rgba(0, 0, 0, 0.87)'
# A report view of ``project.display``: a frame whose document carries the drawn data.
FRAME = re.compile(r'<iframe ([^>]*?)srcdoc="([^"]*)"></iframe>')


def _view_fonts() -> str:
    """What a view on a docs page sets so it reads as the site.

    The report's font and link variables (core/src/report_html.cpp) get the site's text font and
    link colour, and that font is loaded as the site loads it. Tables, captions and charts keep
    their own rules.
    """
    accent = re.search(
        r'--ed-brand-accent:\s*(#[0-9a-fA-F]{6})', BRAND_CSS.read_text(encoding='utf-8')
    )
    if accent is None:
        raise SystemExit(f'{BRAND_CSS.relative_to(ROOT)} names no --ed-brand-accent')
    font = f'"{SITE_FONT}", -apple-system, BlinkMacSystemFont, Helvetica, Arial, sans-serif'
    return (
        f'<link rel="stylesheet" href="{html.escape(SITE_FONT_CSS)}">\n'
        f'<style>:root {{ --body-font: {font}; --head-font: {font}; '
        f'--body-size: {SITE_TABLE_SIZE}; --ink: {SITE_TEXT_COLOUR}; '
        f'--chart-ink: {SITE_TEXT_COLOUR}; '
        f'--link: {accent.group(1)}; --link-hover: {accent.group(1)}; }}</style>\n'
    )


def _docs_ref() -> str:
    """The version the docs are built from, which Open in Colab opens.

    EDI_DOCS_REF (a tag, say) when set, else the built commit: a main build opens main's notebook,
    the dev site its branch head's, so Colab opens the notebook the page offers for download.
    """
    ref = os.environ.get('EDI_DOCS_REF', '').strip()
    if ref:
        return ref
    command = ['git', '-C', str(ROOT), 'rev-parse', 'HEAD']
    return subprocess.check_output(command, text=True).strip()


sys.path.insert(0, str(ROOT / 'tools/checks'))
from case_records import records  # noqa: E402 - the repository's own check


def _text(value: str | list[str]) -> str:
    return value if isinstance(value, str) else ''.join(value)


def _fenced(language: str, text: str) -> str:
    text = text.rstrip('\n')
    fence = '```'
    while fence in text:
        fence += '`'
    return f'{fence}{language}\n{text}\n{fence}\n'


class _Views:
    """Writes each report view's document to a file of its own, loaded when it scrolls into view.

    A view inlined in the page would put its data (the pattern, the structure) into the page's
    text and the site's search index, and make every page carry all its charts up front.
    """

    def __init__(self, folder: Path, url: str) -> None:
        self.folder, self.url, self.count = folder, url, 0

    def __call__(self, match: re.Match) -> str:
        self.count += 1
        name = f'{self.count}.html'
        self.folder.mkdir(parents=True, exist_ok=True)
        document = html.unescape(match.group(2)).replace('</head>', _view_fonts() + '</head>', 1)
        (self.folder / name).write_text(document, encoding='utf-8')
        return f'<iframe {match.group(1)}loading="lazy" src="{self.url}{name}"></iframe>'


def _rich(data: dict, views: _Views) -> str:
    """A display output: the notebook's HTML, else an image, else its text."""
    if 'text/html' in data:
        # Raw HTML stays one block, kept out of the Markdown parser.
        text = FRAME.sub(views, _text(data['text/html']).strip())
        return f'<div class="ed-notebook-output" markdown="0">\n{text}\n</div>\n'
    if 'image/png' in data:
        image = _text(data['image/png']).replace('\n', '')
        base64.b64decode(image, validate=True)
        return (
            f'<p class="ed-notebook-output"><img alt="" src="data:image/png;base64,{image}"></p>\n'
        )
    if 'image/svg+xml' in data:
        svg = _text(data['image/svg+xml']).strip()
        return f'<div class="ed-notebook-output">\n{svg}\n</div>\n'
    return _fenced('text', _text(data['text/plain'])) if 'text/plain' in data else ''


def coalesce_streams(outputs: list) -> list:
    """A cell's outputs with consecutive stream outputs of one name joined.

    As nbconvert's coalesce_streams does: a fit's progress rows, printed one by one, read as
    one block.
    """
    merged: list = []
    for output in outputs:
        previous = merged[-1] if merged else None
        if (
            output.get('output_type') == 'stream'
            and previous is not None
            and previous.get('output_type') == 'stream'
            and previous.get('name') == output.get('name')
        ):
            previous['text'] = _text(previous.get('text', '')) + _text(output.get('text', ''))
            continue
        merged.append(dict(output))
    return merged


def _output(output: dict, views: _Views) -> str:
    kind = output.get('output_type')
    if kind == 'stream':
        return _fenced('text', ANSI.sub('', _text(output.get('text', ''))))
    if kind == 'error':
        return _fenced('text', ANSI.sub('', '\n'.join(output.get('traceback', []))))
    return _rich(output.get('data', {}), views)


def _buttons(name: str, download: str, ref: str) -> str:
    colab = COLAB.format(ref=quote(ref, safe='')) + quote(name)
    # One column, Colab on top, both as wide as the wider (site-components.css).
    return (
        '<div class="ed-tutorial-buttons" markdown>\n'
        f'[:simple-googlecolab: Open in Google Colab]({colab})'
        '{ .md-button .ed-tutorial-button target="_blank" rel="noopener" }\n'
        f'[:fa5-download: Download Notebook]({download})'
        '{ .md-button .ed-tutorial-button download }\n'
        '</div>\n'
    )


def page(
    notebook: dict, record: dict, download: str, views: _Views, ref: str = 'main'
) -> tuple[str, str]:
    """The page text of one notebook, and its title.

    The page's chrome comes from the case record, as in diffraction-lib: the Colab and Download
    buttons above the title, then the title. The notebook's own tags cell follows it, the one the
    notebook shows in Jupyter and Colab; its title line and its hidden install cell are left out.
    """
    name = Path(record['tutorials']['python']).name
    title = record['title'] or record['id']
    parts = [_buttons(name, download, ref), f'# {title}\n']
    headed = False
    for cell in notebook['cells']:
        if HIDDEN in cell.get('metadata', {}).get('tags', []):
            continue
        source = _text(cell.get('source', ''))
        if cell['cell_type'] == 'markdown':
            if not headed and re.search(r'^# ', source, re.MULTILINE):
                source, headed = re.sub(r'^# .*\n?', '', source, count=1, flags=re.MULTILINE), True
            if source.strip():
                parts.append(source.strip() + '\n')
        elif cell['cell_type'] == 'code' and source.strip():
            parts.append(_fenced('python', source))
            outputs = coalesce_streams(cell.get('outputs', []))
            parts.extend(text for text in (_output(o, views) for o in outputs) if text)
    return '\n'.join(parts), title


NOT_RUN = (
    '!!! note "Not run"\n\n'
    '    This notebook has not been run in this build, so the page shows its code without its '
    'results. Run `pixi run notebooks-run` to see them.\n'
)
SKIPPED = (
    '!!! note "Skipped in this build"\n\n'
    '    This build left out the tutorial notebooks (`--no-notebooks`). A full build shows this '
    'tutorial here.\n'
)


def render_notebook_pages(
    notebooks: Path, *, require_outputs: bool = False, skip: bool = False
) -> list[tuple[str, str, str]]:
    """Write a page for each case notebook under ``notebooks``; return (section, title, page path).

    A notebook without outputs is refused with ``require_outputs`` (the published site), and
    otherwise shows its code under a note that it was not run. ``skip`` writes a placeholder per
    tutorial instead, so links and the navigation stay valid in a quick local build.

    The pages, the notebooks they offer for download and their report views are build outputs,
    under ``python/tutorials/cases/``, ``assets/tutorials/notebooks/`` and
    ``assets/tutorials/views/<case>/``.
    """
    pages = DOCS / 'python/tutorials/cases'
    downloads = DOCS / 'assets/tutorials/notebooks'
    shutil.rmtree(DOCS / 'assets/tutorials/views', ignore_errors=True)
    for folder in (pages, downloads):
        shutil.rmtree(folder, ignore_errors=True)
        folder.mkdir(parents=True)
    written = []
    ref = _docs_ref()
    for record in records(ROOT):
        name = Path(record['tutorials']['python']).name
        source = notebooks / name
        if not source.is_file():
            continue
        target = pages / f'{record["id"]}.md'
        entry = (
            record['section'],
            record['nav_title'] or record['title'] or record['id'],
            f'python/tutorials/cases/{record["id"]}.md',
        )
        if skip:
            title = record['title'] or record['id']
            target.write_text(f'# {title}\n\n{SKIPPED}', encoding='utf-8')
            written.append(entry)
            continue
        notebook = json.loads(source.read_text(encoding='utf-8'))
        run = any(cell.get('outputs') for cell in notebook['cells'])
        if not run and require_outputs:
            raise SystemExit(
                f'{source.relative_to(ROOT)} has no outputs: run `pixi run notebooks-run` first'
            )
        shutil.copyfile(source, downloads / name)
        text, title = page(
            notebook,
            record,
            f'../../../assets/tutorials/notebooks/{name}',
            _Views(
                DOCS / 'assets/tutorials/views' / record['id'],
                f'../../../assets/tutorials/views/{record["id"]}/',
            ),
            ref,
        )
        if not run:
            heading = f'# {title}\n'
            text = text.replace(heading, heading + '\n' + NOT_RUN, 1)
        target.write_text(text, encoding='utf-8')
        written.append((
            record['section'],
            record['nav_title'] or title,
            f'python/tutorials/cases/{record["id"]}.md',
        ))
    return written
