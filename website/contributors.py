# SPDX-License-Identifier: BSD-3-Clause
"""The About page's contributor row, and the command that refreshes its avatars (edi ADR-0092).

The avatars are committed with the site so it builds offline. `refresh` downloads each from GitHub
and replaces a file only with a real image; a failed download keeps the old file and warns, so the
deploy never fails on it.
"""

from __future__ import annotations

import os
import sys
import urllib.request
from collections.abc import Callable
from html import escape
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent
DATA = ROOT / 'contributors.yml'
AVATARS = ROOT / 'surfaces/docs/assets/about/contributors'
MARKER = '<!-- contributors -->'
TIMEOUT = 10
# GitHub serves avatars as PNG or JPEG; the browser reads either under the .png name.
IMAGE_SIGNATURES = (b'\x89PNG\r\n\x1a\n', b'\xff\xd8\xff')


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
            raise SystemExit(f'Missing avatar for {login}: run `pixi run site-contributors`')
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


def is_image(data: bytes) -> bool:
    return len(data) > 64 and data.startswith(IMAGE_SIGNATURES)


def download(url: str) -> bytes:
    # The URL is always the fixed https GitHub address built in refresh.
    request = urllib.request.Request(url, headers={'User-Agent': 'edi-site-build'})  # noqa: S310
    with urllib.request.urlopen(request, timeout=TIMEOUT) as response:  # noqa: S310
        return response.read()


def refresh(
    people: list[dict[str, str]],
    avatars: Path = AVATARS,
    fetch: Callable[[str], bytes] = download,
) -> list[str]:
    """Replace each avatar that downloads as an image; return a warning for each that did not."""
    warnings = []
    for person in people:
        login = person['github']
        url = f'https://github.com/{login}.png?size=144'
        try:
            data = fetch(url)
        except Exception as error:  # noqa: BLE001 - any failure keeps the committed avatar
            warnings.append(f'{login}: download failed ({error}); keeping the existing avatar')
            continue
        if not is_image(data):
            warnings.append(f'{login}: the download is not an image; keeping the existing avatar')
            continue
        target = avatars / f'{login}.png'
        if not target.is_file() or target.read_bytes() != data:
            target.write_bytes(data)
    return warnings


def main() -> None:
    AVATARS.mkdir(parents=True, exist_ok=True)
    prefix = '::warning::' if os.environ.get('GITHUB_ACTIONS') else 'warning: '
    for warning in refresh(load()):
        print(prefix + warning, file=sys.stderr)


if __name__ == '__main__':
    main()
