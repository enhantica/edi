# SPDX-License-Identifier: BSD-3-Clause
"""MkDocs hook: write each notebook view's document in single quotes.

nbconvert puts a frame's ``srcdoc`` in double quotes, so every quote of the view's JSON model
becomes ``&quot;`` and a tutorial page grows by about a third.
"""

from __future__ import annotations

import html
import re
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from mkdocs.config.defaults import MkDocsConfig
    from mkdocs.structure.pages import Page

FRAME = re.compile(r'srcdoc="([^"]*)"')


def _single_quoted(match: re.Match) -> str:
    document = html.unescape(match.group(1))
    return "srcdoc='" + document.replace('&', '&amp;').replace("'", '&#39;') + "'"


def on_post_page(output: str, page: Page, config: MkDocsConfig) -> str:  # noqa: ARG001 - hook signature
    return FRAME.sub(_single_quoted, output)
