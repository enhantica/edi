# SPDX-License-Identifier: BSD-3-Clause
"""Link desktop download cards to public GitHub release assets."""

import re
from datetime import date
from operator import itemgetter

PLATFORMS = ('macos-arm64', 'windows-x86_64', 'linux-x86_64')
TAG = re.compile(r'v([0-9]{4})\.(0[1-9]|1[0-2])\.(0|[1-9][0-9]*)')


def render(page: str, pages: list[list[dict]]) -> str:
    """Prefer stable installers, and leave missing platform cards unavailable."""
    candidates = []
    for release in (item for page in pages for item in page):
        tag = release['tag_name']
        match = TAG.fullmatch(tag)
        if release['draft'] or match is None:
            continue
        version = tag[1:]
        links = {
            asset['browser_download_url']
            for asset in release.get('assets', [])
            if asset.get('state') == 'uploaded'
        }
        installers = {}
        for platform in PLATFORMS:
            url = (
                f'https://github.com/enhantica/edi/releases/download/{tag}/'
                f'EasyDiffraction-{version}-{platform}-online.zip'
            )
            if url in links:
                installers[platform] = url
        if installers:
            rank = not release['prerelease'], tuple(map(int, match.groups()))
            candidates.append((rank, version, installers, release['published_at']))
    if not candidates:
        return page
    _, version, installers, published = max(candidates, key=itemgetter(0))
    day = date.fromisoformat(published[:10])
    display_date = f'{day.day} {day:%b %Y}'
    page = page.replace(
        'Desktop installers will appear here when published.',
        f'Latest version {version} ({display_date})',
    )
    for platform, url in installers.items():
        page = page.replace(
            f'data-download-platform="{platform}" aria-disabled="true"',
            f'data-download-platform="{platform}" href="{url}"',
        )
    return page
