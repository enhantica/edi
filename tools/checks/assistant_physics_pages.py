# SPDX-License-Identifier: BSD-3-Clause
"""Bundle the website's physics pages that hold equations into one file of the assistant's skill.

The assistant reads equations there before it searches the website, so it finds them in seconds.
One file keeps the skill sources' shared file count low. `--check` refuses a bundle that differs
from the website's pages.
"""

from __future__ import annotations

import argparse
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / 'website/surfaces/docs/physics'
TARGET = ROOT / 'data/assistant/skills/project-assistance/physics.md'
SITE = 'https://easydiffraction.org/physics/'
EQUATION = re.compile(r'\$\$|\\begin\{')
ANCHOR = re.compile(r'\{#(eq-[A-Za-z0-9_-]+)')
TITLE = re.compile(r'^# (.+)$', re.MULTILINE)


def url(relative: Path) -> str:
    path = relative.with_suffix('').as_posix()
    if path == 'index' or path.endswith('/index'):
        path = path[: -len('index')]
    else:
        path += '/'
    return SITE + path


def expected() -> str:
    """The list of the pages with equations, then each page under its website address."""
    pages = {}
    for source in sorted(SOURCE.rglob('*.md')):
        text = source.read_text(encoding='utf-8')
        if EQUATION.search(text):
            pages[source.relative_to(SOURCE)] = text
    rows = []
    for relative, text in pages.items():
        title = TITLE.search(text)
        anchors = ', '.join(ANCHOR.findall(text)) or '-'
        name = title.group(1) if title else relative.stem
        rows.append(f'| {name} | {anchors} | {url(relative)} |')
    parts = [
        '# Physics pages with equations',
        '',
        "The website's physics pages that hold equations, as they were when this app was built.",
        'Find the page in the table, then its section below, which starts with a line',
        '`Page: <website address>`; cite that address.',
        '',
        '| Title | Equations | Website |',
        '| --- | --- | --- |',
        *rows,
    ]
    for relative, text in pages.items():
        parts += ['', '---', '', f'Page: {url(relative)}', '', text.rstrip('\n')]
    return '\n'.join(parts) + '\n'


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true', help='refuse a stale or missing bundle')
    args = parser.parse_args()
    text = expected()
    if args.check:
        if not TARGET.is_file() or TARGET.read_text(encoding='utf-8') != text:
            print(
                f'assistant physics pages: {TARGET.relative_to(ROOT)} is missing or stale; run '
                "'python tools/checks/assistant_physics_pages.py' to update it"
            )
            return 1
        print('Assistant physics pages are current')
        return 0
    TARGET.write_text(text, encoding='utf-8')
    print(f'Wrote {TARGET.relative_to(ROOT)}, {len(text.encode("utf-8"))} bytes')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
