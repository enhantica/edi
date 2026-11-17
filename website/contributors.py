# SPDX-License-Identifier: BSD-3-Clause
"""The About page's contributor row, and the command that refreshes its avatars (edi ADR-0092).

The avatars are committed with the site so it builds offline. `refresh` downloads each from GitHub
and replaces a file only with a whole PNG or JPEG image, written beside it and moved into place, so a
cut-off download or a failed write never leaves a broken avatar; any failure keeps the old file and
warns, so the deploy never fails on it.
"""

from __future__ import annotations

import os
import struct
import sys
import urllib.request
import zlib
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
PNG_SIGNATURE = b'\x89PNG\r\n\x1a\n'
# The JPEG frame headers (baseline, progressive and the rarer codings), one of which every image has.
JPEG_FRAMES = {0xC0, 0xC1, 0xC2, 0xC3, 0xC5, 0xC6, 0xC7, 0xC9, 0xCA, 0xCB, 0xCD, 0xCE, 0xCF}


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


def _whole_png(data: bytes) -> bool:
    """Every chunk complete with its checksum, from IHDR to IEND, and the image data a complete zlib stream."""
    at, first, pixels = len(PNG_SIGNATURE), True, zlib.decompressobj()
    while at + 12 <= len(data):
        (length,) = struct.unpack('>I', data[at : at + 4])
        kind = data[at + 4 : at + 8]
        end = at + 12 + length
        if end > len(data) or (first and kind != b'IHDR'):
            return False
        body = data[at + 8 : at + 8 + length]
        if zlib.crc32(kind + body) != struct.unpack('>I', data[end - 4 : end])[0]:
            return False
        if kind == b'IDAT':
            try:
                pixels.decompress(body)
            except zlib.error:
                return False
        if kind == b'IEND':
            return pixels.eof
        at, first = end, False
    return False


def _whole_jpeg(data: bytes) -> bool:
    """Its segments complete up to the scan, a frame header among them, and the end-of-image marker last."""
    at, frame = 2, False
    while at + 4 <= len(data):
        if data[at] != 0xFF:
            return False
        marker = data[at + 1]
        if marker == 0xFF:  # fill byte
            at += 1
            continue
        (length,) = struct.unpack('>H', data[at + 2 : at + 4])
        if length < 2 or at + 2 + length > len(data):
            return False
        frame = frame or marker in JPEG_FRAMES
        if marker == 0xDA:  # start of scan: the coded data runs to the end marker
            return frame and data.rstrip(b'\x00').endswith(b'\xff\xd9') and len(data) > at + 2 + length + 2
        at += 2 + length
    return False


def is_image(data: bytes) -> bool:
    """A whole PNG or JPEG image: a download cut off after its first bytes is refused."""
    if data.startswith(PNG_SIGNATURE):
        return _whole_png(data)
    if data.startswith(b'\xff\xd8\xff'):
        return _whole_jpeg(data)
    return False


def replace_file(target: Path, data: bytes) -> None:
    """Write beside the target and move into place, so the old file stays whole until the new one is."""
    temporary = target.with_name(f'.{target.name}.download')
    try:
        temporary.write_bytes(data)
        os.replace(temporary, target)
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
            warnings.append(f'{login}: the avatar could not be written ({error}); keeping the existing avatar')
    return warnings


def main() -> None:
    AVATARS.mkdir(parents=True, exist_ok=True)
    prefix = '::warning::' if os.environ.get('GITHUB_ACTIONS') else 'warning: '
    for warning in refresh(load()):
        print(prefix + warning, file=sys.stderr)


if __name__ == '__main__':
    main()
