# SPDX-License-Identifier: BSD-3-Clause
"""The About page's contributor row, and the command that refreshes its avatars (edi ADR-0092).

The avatars are committed with the site so it builds offline. `refresh` downloads each from GitHub
and replaces a file only with a PNG or JPEG image that decodes whole (Pillow, and pypng for a PNG's
rows), written beside it and moved into place, so a cut-off download or a failed write never leaves
a broken avatar; any failure keeps the old file and warns, so the deploy never fails on it.
"""

from __future__ import annotations

import os
import sys
import urllib.request
import zlib
from collections.abc import Callable
from html import escape
from io import BytesIO
from pathlib import Path

import png
import yaml
from PIL import Image

ROOT = Path(__file__).resolve().parent
DATA = ROOT / 'contributors.yml'
AVATARS = ROOT / 'surfaces/docs/assets/about/contributors'
MARKER = '<!-- contributors -->'
TIMEOUT = 10
# GitHub serves avatars as PNG or JPEG; the browser reads either under the .png name.
IMAGE_FORMATS = {'PNG', 'JPEG'}


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


def _decoded_size(data: bytes) -> tuple[str, int, int] | None:
    """The format and size Pillow decodes the image to, or None when it does not decode."""
    try:
        with Image.open(BytesIO(data)) as image:
            image.load()
            return image.format, image.width, image.height
    except (OSError, ValueError, SyntaxError, Image.DecompressionBombError):
        return None


def _png_rows(data: bytes) -> int:
    """How many rows pypng reads from a PNG; -1 when it does not read."""
    try:
        _, _, rows, _ = png.Reader(bytes=data).read()
        return sum(1 for _ in rows)
    except (png.Error, ValueError, zlib.error):
        return -1


def is_image(data: bytes) -> bool:
    """A PNG or JPEG image that decodes whole, with a size: a cut-off download is refused.

    Pillow decodes it. Pillow fills a PNG's missing rows with zeros, so pypng also reads a PNG,
    which must yield every row Pillow found the image to have.
    """
    decoded = _decoded_size(data)
    if decoded is None:
        return False
    kind, width, height = decoded
    if kind not in IMAGE_FORMATS or width <= 0 or height <= 0:
        return False
    return kind != 'PNG' or _png_rows(data) == height


def replace_file(target: Path, data: bytes) -> None:
    """Write beside the target, then move into place: the old file stays whole until then."""
    temporary = target.with_name(f'.{target.name}.download')
    try:
        temporary.write_bytes(data)
        temporary.replace(target)
    finally:
        temporary.unlink(missing_ok=True)


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
        if target.is_file() and target.read_bytes() == data:
            continue
        try:
            replace_file(target, data)
        except OSError as error:
            warnings.append(
                f'{login}: the avatar could not be written ({error}); keeping the existing avatar'
            )
    return warnings


def main() -> None:
    AVATARS.mkdir(parents=True, exist_ok=True)
    prefix = '::warning::' if os.environ.get('GITHUB_ACTIONS') else 'warning: '
    for warning in refresh(load()):
        print(prefix + warning, file=sys.stderr)


if __name__ == '__main__':
    main()
