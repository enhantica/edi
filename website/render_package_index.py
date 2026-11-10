# SPDX-License-Identifier: BSD-3-Clause
"""Generate a pip-compatible index that serves the published wheels from the site itself."""

import hashlib
import html
import re
import subprocess
from collections.abc import Callable
from pathlib import Path

WHEEL = re.compile(
    r'easydiffraction-(?P<version>\d{4}\.\d{1,2}\.\d+)-cp312-abi3-'
    r'(?:linux_x86_64|win_amd64|macosx_14_0_arm64)\.whl'
)
REPOSITORY = 'enhantica/edi'
RELEASES = f'https://github.com/{REPOSITORY}/releases/download'

Fetch = Callable[[str, str, Path], None]


def gh_download(tag: str, name: str, folder: Path) -> None:
    """Download one release asset through the authenticated API (GH_TOKEN), not the public URL."""
    subprocess.run(
        [
            'gh', 'release', 'download', tag, '--repo', REPOSITORY,
            '--pattern', name, '--dir', str(folder), '--clobber',
        ],
        check=True,
    )  # fmt: skip


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open('rb') as handle:
        for block in iter(lambda: handle.read(1 << 20), b''):
            digest.update(block)
    return digest.hexdigest()


def listed_wheels(pages: list[list[dict]]) -> dict[str, tuple[str, str]]:
    """Published, uploaded wheels with a GitHub-recorded SHA-256: name -> (tag, hex digest)."""
    wheels = {}
    for release in (release for page in pages for release in page):
        if release['draft']:
            continue
        for asset in release.get('assets', []):
            name = asset['name']
            match = WHEEL.fullmatch(name)
            if match is None or release['tag_name'] != 'v' + match['version']:
                continue
            digest = asset.get('digest') or ''
            if (
                asset.get('state') == 'uploaded'
                and asset.get('browser_download_url') == f'{RELEASES}/{release["tag_name"]}/{name}'
                and re.fullmatch(r'sha256:[a-f0-9]{64}', digest)
            ):
                wheels[name] = (release['tag_name'], digest.split(':', 1)[1])
    return wheels


def version_key(name: str) -> tuple[int, ...]:
    return tuple(int(part) for part in WHEEL.fullmatch(name)['version'].split('.'))


def write_package_index(output: Path, pages: list[list[dict]], fetch: Fetch = gh_download) -> None:
    """Serve the current release's wheels beside the index; link older versions to their releases.

    The newest listed version is the current release. Its wheels are fetched, checked against the
    digest their release recorded and linked relatively, so installing it needs nothing but this
    site. Older versions link their GitHub release assets with the same digests. Any other wheel
    file is removed, so the site serves exactly the current release.
    """
    root = output / 'pypi/simple'
    project = root / 'easydiffraction'
    project.mkdir(parents=True, exist_ok=True)
    wheels = listed_wheels(pages)
    newest = max(map(version_key, wheels), default=None)
    current = {name for name in wheels if version_key(name) == newest}
    for stale in project.glob('*.whl'):
        if stale.name not in current:
            stale.unlink()
    links = []
    for name, (tag, digest) in sorted(wheels.items(), key=lambda item: version_key(item[0])):
        href = f'{RELEASES}/{tag}/{name}'
        if name in current:
            href = name
            wheel = project / name
            if not wheel.is_file() or sha256(wheel) != digest:
                fetch(tag, name, project)
            if not wheel.is_file() or sha256(wheel) != digest:
                wheel.unlink(missing_ok=True)
                raise SystemExit(f'{name} from {tag} does not match its recorded sha256 {digest}')
        links.append(
            f'<a href="{html.escape(href)}#sha256={digest}" '
            f'data-requires-python="&gt;=3.12">{name}</a>'
        )
    for path, body in (
        (root, '<a href="easydiffraction/">easydiffraction</a>'),
        (project, '\n'.join(links)),
    ):
        (path / 'index.html').write_text(
            f'<!doctype html>\n<html><body>\n{body}\n</body></html>\n', encoding='utf-8'
        )
