# SPDX-License-Identifier: BSD-3-Clause
"""Highlight CIF and Edi code blocks on the docs site as the app's Text view colours them.

The owner's record (2026-11-09): every CIF and Edi block is coloured with the same token kinds and
colours as the app's Text tab (app/src/edi_text_highlighter.cpp, AppColors). The rules are that
highlighter's, line by line: a `data_` line is a datablock name, `loop_` a loop keyword, an item
name after `loop_` a loop column, any other item name an item; a `;` text field and everything
else stay plain. The docs build registers `fence` for ```edi and ```cif blocks (mkdocs.yml).
"""

from __future__ import annotations

import html
import re

from pygments.lexer import Lexer
from pygments.token import Keyword, Name, Text

# The app's four token kinds as Pygments tokens; site-components.css gives each the app's colour.
DATABLOCK = Name.Namespace
ITEM = Name.Tag
LOOP_COLUMN = Name.Attribute
LOOP = Keyword

OUTSIDE, LOOP_KEYS, TEXT_FIELD = range(3)


class EdiLexer(Lexer):
    """The app's Text-view rules for `.edi` and CIF text."""

    name = 'Edi'
    aliases = ['edi', 'cif']  # noqa: RUF012 - Pygments reads class attributes
    filenames = ['*.edi', '*.cif']  # noqa: RUF012

    def get_tokens_unprocessed(self, text: str):  # noqa: ANN201, PLR6301 - Pygments' own signature
        """Each line's first token in its kind, the rest plain, as the app colours it."""
        state = OUTSIDE
        position = 0
        for line in text.splitlines(keepends=True):
            previous = state
            kind = None
            if previous == TEXT_FIELD:
                state = OUTSIDE if line.startswith(';') else TEXT_FIELD
            elif line.startswith(';'):
                state = TEXT_FIELD
            elif line.startswith('data_'):
                state, kind = OUTSIDE, DATABLOCK
            elif line.strip() == 'loop_':
                state, kind = LOOP_KEYS, LOOP
            elif line.startswith('_'):
                state = LOOP_KEYS if previous == LOOP_KEYS else OUTSIDE
                kind = LOOP_COLUMN if previous == LOOP_KEYS else ITEM
            else:
                state = OUTSIDE
            end = len(re.match(r'\S*', line).group(0)) if kind else 0
            if end:
                yield position, kind, line[:end]
            if line[end:]:
                yield position + end, Text, line[end:]
            position += len(line)


CLASSES = {DATABLOCK: 'nn', ITEM: 'nt', LOOP_COLUMN: 'na', LOOP: 'k'}


def fence(source: str, language: str, css_class: str, *_args: object, **_kwargs: object) -> str:
    """A superfences formatter: the block as the site's highlighted code, in the app's kinds."""
    spans = []
    for _position, token, value in EdiLexer().get_tokens_unprocessed(source):
        text = html.escape(value)
        spans.append(f'<span class="{CLASSES[token]}">{text}</span>' if token in CLASSES else text)
    return (
        f'<div class="language-{language} {css_class}"><pre><span></span><code>'
        + ''.join(spans)
        + '</code></pre></div>'
    )


# A code block that reads as CIF or Edi: at least two lines that start a datablock, a loop or an
# item name with a category (`_cell.length_a`, `_cell_length_a`).
LOOKS_LIKE = re.compile(r'^(?:data_\S*|loop_|_[A-Za-z][\w.\[\]-]*)(?:\s|$)', re.MULTILINE)


def looks_like_cif(text: str) -> bool:
    """Whether a code block's text is CIF or Edi (the site check refuses it unhighlighted)."""
    return len(LOOKS_LIKE.findall(text)) >= 2
