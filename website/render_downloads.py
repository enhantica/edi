# SPDX-License-Identifier: BSD-3-Clause
"""Link download cards to public GitHub release assets."""

import re
from datetime import date
from operator import itemgetter

PLATFORMS = ('macos-arm64', 'windows-x86_64', 'linux-x86_64')
TAG = re.compile(r'v([0-9]{4})\.(0[1-9]|1[0-2])\.(0|[1-9][0-9]*)')


def render(page: str, pages: list[list[dict]], *, kind: str = 'online') -> str:
    """Prefer stable releases, and leave missing platform cards unavailable.

    The desktop page (kind 'online') holds the online and the offline installers, each button with
    its kind and its size in whole MB from the release's asset list; the command line page has one
    kind.
    """
    kinds = ('online', 'offline') if kind == 'online' else (kind,)
    candidates = []
    for release in (item for page in pages for item in page):
        tag = release['tag_name']
        match = TAG.fullmatch(tag)
        if release['draft'] or match is None:
            continue
        version = tag[1:]
        sizes = {
            asset['browser_download_url']: asset.get('size', 0)
            for asset in release.get('assets', [])
            if asset.get('state') == 'uploaded'
        }
        installers = {}
        for each in kinds:
            for platform in PLATFORMS:
                url = (
                    f'https://github.com/enhantica/edi/releases/download/{tag}/'
                    f'EasyDiffraction-{version}-{platform}-{each}.zip'
                )
                if url in sizes:
                    installers[platform, each] = url, sizes[url]
        if any(each == kinds[0] for _, each in installers):
            rank = not release['prerelease'], tuple(map(int, match.groups()))
            candidates.append((rank, version, installers, release['published_at']))
    if not candidates:
        return page
    _, version, installers, published = max(candidates, key=itemgetter(0))
    day = date.fromisoformat(published[:10])
    display_date = f'{day.day} {day:%b %Y}'
    page = page.replace(
        {
            'online': 'Desktop installers will appear here when published.',
            'cli': 'Command line downloads will appear here when published.',
        }[kind],
        f'Latest version {version} ({display_date})',
    )
    for (platform, each), (url, size) in installers.items():
        if kind == 'online':
            page = page.replace(
                f'data-download-platform="{platform}" data-download-kind="{each}" '
                'aria-disabled="true"',
                f'data-download-platform="{platform}" data-download-kind="{each}" href="{url}"',
            )
            page = page.replace(
                f'<small data-download-size="{platform}-{each}">{each.capitalize()}</small>',
                f'<small data-download-size="{platform}-{each}">{each.capitalize()} · '
                f'{round(size / 1_000_000)} MB</small>',
            )
        else:
            page = page.replace(
                f'data-download-platform="{platform}" aria-disabled="true"',
                f'data-download-platform="{platform}" href="{url}"',
            )
    return page
