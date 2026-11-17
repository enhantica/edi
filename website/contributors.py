# SPDX-License-Identifier: BSD-3-Clause
"""The About page's contributor row (edi ADR-0092); the avatars are committed with the site."""

from __future__ import annotations

from html import escape
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent
DATA = ROOT / 'contributors.yml'
AVATARS = ROOT / 'surfaces/docs/assets/about/contributors'
MARKER = '<!-- contributors -->'


def load(path: Path = DATA) -> list[dict[str, str]]:
    """The contributors in page order, each with a name and a GitHub login."""
    people = yaml.safe_load(path.read_text(encoding='utf-8'))
    if not isinstance(people, list) or not people:
        raise SystemExit(f'{path.name}: expected a list of contributors')
    for person in people:
        if not isinstance(person, dict) or set(person) != {'name', 'github'}:
            raise SystemExit(f'{path.name}: each contributor needs a name and a github login')
    return people


def render(people: list[dict[str, str]], avatars: Path = AVATARS) -> str:
    """One line of HTML, so Markdown keeps it as a single raw block inside the signature card."""
    links = []
    for index, person in enumerate(people):
        login, name = person['github'], escape(person['name'])
        if not (avatars / f'{login}.png').is_file():
            raise SystemExit(f'Missing avatar for {login}: add {login}.png beside the others')
        avatar = f'../assets/about/contributors/{escape(login)}.png'
        links.append(
            f'<a class="ed-contributor" href="https://github.com/{escape(login)}"'
            f' aria-label="{name}" style="--i:{index}">'
            f'<img src="{avatar}" alt="" width="72" height="72">'
            f'<span class="ed-contributor-name" aria-hidden="true">{name}</span></a>'
        )
    return (
        '<div class="ed-contributors"><div class="ed-contributors-stack">'
        + ''.join(links)
        + '</div><span class="ed-contributors-label">and<br>contributors</span></div>'
    )


def with_contributors(page: str, people: list[dict[str, str]], avatars: Path = AVATARS) -> str:
    if page.count(MARKER) != 1:
        raise SystemExit(f'about/index.md: expected one {MARKER} line')
    return page.replace(MARKER, render(people, avatars))
