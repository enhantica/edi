# SPDX-License-Identifier: BSD-3-Clause
"""Link download cards to public GitHub release assets."""

import re
from datetime import date
from operator import itemgetter

PLATFORMS = ('macos-arm64', 'windows-x86_64', 'linux-x86_64')
TAG = re.compile(r'v([0-9]{4})\.(0[1-9]|1[0-2])\.(0|[1-9][0-9]*)')
# The desktop installers' downloads: a disk image on macOS, the installer itself on Windows, a ZIP
# on Linux; releases before single-file installers had a ZIP everywhere.
SUFFIXES = {'macos-arm64': ('.dmg', '.zip'), 'windows-x86_64': ('.exe', '.zip')}


def asset_url(sizes: dict, tag: str, stem: str, platform: str) -> str | None:
    """The uploaded asset of one download, preferring the platform's current file type."""
    suffixes = SUFFIXES.get(platform, ('.zip',)) if not stem.endswith('-cli') else ('.zip',)
    for suffix in suffixes:
        url = f'https://github.com/enhantica/edi/releases/download/{tag}/{stem}{suffix}'
        if url in sizes:
            return url
    return None


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
                found = asset_url(
                    sizes, tag, f'EasyDiffraction-{version}-{platform}-{each}', platform
                )
                if found:
                    installers[platform, each] = found, sizes[found]
        if any(each == kinds[0] for _, each in installers):
            rank = not release['prerelease'], tuple(map(int, match.groups()))
            candidates.append((rank, version, installers, release['published_at']))
    if not candidates:
        return page
    _, version, installers, published = max(candidates, key=itemgetter(0))
    if kind == 'online':
        # The home page names the latest version and its date, so the desktop page drops its
        # placeholder instead of repeating them.
        page = re.sub(
            r'<p[^>]*>Desktop installers will appear here when published\.</p>\n*', '', page
        )
    else:
        day = date.fromisoformat(published[:10])
        page = page.replace(
            'Command line downloads will appear here when published.',
            f'Latest version {version} ({day.day} {day:%b %Y})',
        )
    for (platform, each), (url, size) in installers.items():
        if kind == 'online':
            page = page.replace(
                f'data-download-platform="{platform}" data-download-kind="{each}" '
                'aria-disabled="true"',
                f'data-download-platform="{platform}" data-download-kind="{each}" href="{url}"',
            )
            page = page.replace(
                f'<small data-download-size="{platform}-{each}">'
                f'{each.capitalize()} installer</small>',
                f'<small data-download-size="{platform}-{each}">{each.capitalize()} installer · '
                f'{round(size / 1_000_000)} MB</small>',
            )
        else:
            page = page.replace(
                f'data-download-platform="{platform}" aria-disabled="true"',
                f'data-download-platform="{platform}" href="{url}"',
            )
    return page
