# SPDX-License-Identifier: BSD-3-Clause
"""Generate a pip-compatible index of qualified, published GitHub wheels."""

import html
import re
from pathlib import Path

WHEEL = re.compile(
    r'easydiffraction-(?P<version>\d{4}\.\d{1,2}\.\d+)-cp312-abi3-'
    r'(?:linux_x86_64|win_amd64|macosx_14_0_arm64)\.whl'
)
RELEASES = 'https://github.com/enhantica/edi/releases/download'


def write_package_index(output: Path, pages: list[list[dict]]) -> None:
    """Index only immutable release assets with a GitHub-provided SHA-256 digest."""
    root = output / 'pypi/simple'
    project = root / 'easydiffraction'
    project.mkdir(parents=True, exist_ok=True)
    links = {}
    for release in (release for page in pages for release in page):
        if release['draft']:
            continue
        for asset in release.get('assets', []):
            name = asset['name']
            match = WHEEL.fullmatch(name)
            if match is None or release['tag_name'] != 'v' + match['version']:
                continue
            url = f'{RELEASES}/{release["tag_name"]}/{name}'
            digest = asset.get('digest') or ''
            if (
                asset.get('state') == 'uploaded'
                and asset.get('browser_download_url') == url
                and re.fullmatch(r'sha256:[a-f0-9]{64}', digest)
            ):
                links[name] = url + '#' + digest.replace(':', '=', 1)
    for path, body in (
        (root, '<a href="easydiffraction/">easydiffraction</a>'),
        (
            project,
            '\n'.join(
                f'<a href="{html.escape(url)}" data-requires-python="&gt;=3.12">{name}</a>'
                for name, url in sorted(links.items())
            ),
        ),
    ):
        (path / 'index.html').write_text(
            f'<!doctype html>\n<html><body>\n{body}\n</body></html>\n', encoding='utf-8'
        )
