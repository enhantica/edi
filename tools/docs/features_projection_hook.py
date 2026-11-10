# SPDX-License-Identifier: BSD-3-Clause
"""MkDocs hook: project the user-facing Features page from the developer catalog.

The developer feature catalog (``docs/dev/features.md``) is the single hand-maintained
record — Feature | LIB | CLI | APP | WEB | Milestone. The user-facing Features page is
its **projection**: capability status per surface, with the Milestone (delivery
schedule — developer-facing) column dropped. Generated at build time and never
committed, so the two cannot drift (a user-facing Features page is the projection of
the dev-side coverage record, never a second hand-maintained list).

Fail-closed like the Doxygen hook: a missing or unparseable source aborts the build
rather than publishing a stale or empty user page.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import TYPE_CHECKING

from mkdocs.exceptions import PluginError
from mkdocs.structure.files import File

if TYPE_CHECKING:
    from mkdocs.config.defaults import MkDocsConfig
    from mkdocs.structure.files import Files

_CATALOG_COLUMNS = 6  # Feature | LIB | CLI | APP | WEB | Milestone

_SOURCE = 'dev/features.md'
_TARGET = 'user/features.md'

_HEADER = (
    '# Features\n'
    '\n'
    '> Generated at build time from the developer feature catalog\n'
    '> (`docs/dev/features.md`) — the single source of truth. Do not edit.\n'
    '\n'
    'What edi can do today, per surface: **LIB** = `import edi` · **CLI** = the\n'
    '`easydiffraction` binary · **APP** = desktop app · **WEB** = the web app.\n'
    '☑ shipped · 🚧 in progress · ☐ planned · ➖ not applicable by design.\n'  # noqa: RUF001 — the catalog legend's own glyph
)


def _project(source_text: str) -> str:
    out: list[str] = [_HEADER]
    pending_heading: str | None = None
    skip_section = False
    for line in source_text.splitlines():
        heading = re.match(r'^(#{2,3}) +(.*)$', line)
        if heading:
            title = heading.group(2)
            skip_section = 'skipped' in title.lower() or 'how to read' in title.lower()
            pending_heading = f'{heading.group(1)} {title}'
            continue
        if skip_section:
            continue
        cells = [c.strip() for c in line.split('|')[1:-1]] if line.startswith('|') else None
        if not cells or len(cells) < _CATALOG_COLUMNS:
            continue
        feature, surfaces = cells[0], cells[1:5]
        if feature.lower() == 'feature' or set(feature) <= {'-', ' ', ':'}:
            continue
        if pending_heading is not None:
            header_rows = [
                '',
                pending_heading,
                '',
                '| Feature | LIB | CLI | APP | WEB |',
                '| --- | :-: | :-: | :-: | :-: |',
            ]
            out.extend(header_rows)
            pending_heading = None
        out.append('| ' + ' | '.join([feature, *surfaces]) + ' |')
    if len(out) == 1:
        message = f'features projection: no feature rows found in {_SOURCE}'
        raise PluginError(message)
    return '\n'.join(out) + '\n'


def on_files(files: Files, config: MkDocsConfig) -> Files:
    """Inject the generated user Features page (mkdocs `on_files` hook)."""
    source = Path(config['docs_dir']) / _SOURCE
    if not source.is_file():
        message = f'features projection: source {_SOURCE} is missing'
        raise PluginError(message)
    content = _project(source.read_text(encoding='utf-8'))
    files.append(File.generated(config, _TARGET, content=content))
    return files
