# SPDX-License-Identifier: BSD-3-Clause
"""Install EasyDiffraction for a tutorial; copied into each notebook's setup cell."""

import html
import importlib
import importlib.metadata
import importlib.util
import json
import os
import re
import subprocess
import sys
import urllib.parse
import urllib.request

RESTART = 'edi is already imported in this kernel. Restart the runtime, then run this cell again.'


def install_edi(index: str) -> None:
    """Install the wheel EasyDiffraction's index lists, and admit ``import edi`` only for it.

    The wheel is installed by its URL and sha256 with pip's settings ignored, so another index or
    pip configuration cannot supply it, and an unreachable index stops here. Its dependencies are
    installed on every run, by name, with the usual pip settings. If edi is already imported in
    this kernel, setup installs what is needed and asks for a restart; it never vouches for a
    loaded module. Otherwise ``import edi`` is admitted when the file it would load is one the
    installed wheel's RECORD lists. A source build is used only when ``EDI_SOURCE_BUILD=1`` asks
    for it; a folder or file that merely happens to be called edi never counts as one.
    """
    if 'edi' in sys.modules:
        if importlib.metadata.packages_distributions().get('edi'):
            _install(index)
        raise RuntimeError(RESTART)
    if os.environ.get('EDI_SOURCE_BUILD') == '1':
        spec = importlib.util.find_spec('edi')
        if spec is None or not spec.origin:
            raise RuntimeError('EDI_SOURCE_BUILD is set, but no edi source build can be imported')
        print('Using the edi source build at', spec.origin)
        return
    url, digest = _install(index)
    importlib.invalidate_caches()
    if not _admitted(url, digest):
        spec = importlib.util.find_spec('edi')
        found = (spec.origin or 'a folder without __init__.py') if spec else 'nothing'
        raise RuntimeError(
            f'import edi would load {found}, not the wheel from {index}; '
            'move or rename that edi and run this cell again'
        )


def _install(index: str) -> tuple[str, str]:
    """Install the approved wheel when it is not installed, then its declared dependencies."""
    url, digest = _wheel(index)
    if not _installed_from(url, digest):
        _pip('--no-deps', '--force-reinstall', f'easydiffraction @ {url}#sha256={digest}')
    importlib.invalidate_caches()
    requires = importlib.metadata.requires('easydiffraction') or []
    if requires:
        _pip(*requires, settings=True)
    return url, digest


def _wheel(index: str) -> tuple[str, str]:
    """The newest wheel on our index that this interpreter can install, with its sha256."""
    try:
        from packaging.tags import sys_tags  # noqa: PLC0415 - optional in a notebook
    except ImportError:
        from pip._vendor.packaging.tags import sys_tags  # noqa: PLC0415, PLC2701 - pip's copy
    supported = [str(tag) for tag in sys_tags()]
    page_url = urllib.parse.urljoin(index.rstrip('/') + '/', 'easydiffraction/')
    # A web index serves the folder's page itself; a local one is read from its index.html.
    page_file = page_url + 'index.html' if page_url.startswith('file:') else page_url
    with urllib.request.urlopen(page_file, timeout=60) as response:  # noqa: S310 - our index URL
        page = response.read().decode('utf-8')
    found = []
    for link in re.findall(r'href="([^"]+)"', page):
        url, _, fragment = urllib.parse.urljoin(page_url, html.unescape(link)).partition('#')
        name = url.rsplit('/', 1)[-1]
        match = re.fullmatch(r'easydiffraction-([0-9.]+)-([^-]+)-([^-]+)-([^-]+)\.whl', name)
        allowed = urllib.parse.urlparse(url).scheme in {
            'https',
            urllib.parse.urlparse(index).scheme,
        }
        if not match or not fragment.startswith('sha256=') or not allowed:
            continue
        tags = {
            f'{i}-{a}-{p}'
            for i in match[2].split('.')
            for a in match[3].split('.')
            for p in match[4].split('.')
        }
        ranks = [supported.index(tag) for tag in tags if tag in supported]
        if ranks:
            version = tuple(int(part) for part in match[1].split('.'))
            found.append((version, -min(ranks), url, fragment.removeprefix('sha256=')))
    if not found:
        raise RuntimeError('No EasyDiffraction wheel for this Python on ' + page_url)
    _, _, url, digest = max(found)
    return url, digest


def _installed_from(url: str, digest: str) -> bool:
    """Whether the installed easydiffraction came from this wheel URL and sha256."""
    try:
        dist = importlib.metadata.distribution('easydiffraction')
    except importlib.metadata.PackageNotFoundError:
        return False
    info = json.loads(dist.read_text('direct_url.json') or '{}')
    archive = info.get('archive_info', {})
    hashes = (
        archive.get('hashes', {}).get('sha256'),
        archive.get('hash', '').removeprefix('sha256='),
    )
    return info.get('url') == url and digest in hashes


def _admitted(url: str, digest: str) -> bool:
    """Whether the file ``import edi`` would load is one the installed wheel's RECORD lists."""
    spec = importlib.util.find_spec('edi')
    if spec is None or not spec.origin or not _installed_from(url, digest):
        return False
    dist = importlib.metadata.distribution('easydiffraction')
    origin = os.path.realpath(spec.origin)
    return any(os.path.realpath(dist.locate_file(file)) == origin for file in dist.files or ())


def _pip(*arguments: str, settings: bool = False) -> None:
    """Run pip, ignoring every pip setting unless ``settings`` asks for the user's own."""
    environment = dict(os.environ)
    if not settings:
        environment = {k: v for k, v in environment.items() if not k.startswith('PIP_')}
        environment['PIP_CONFIG_FILE'] = os.devnull
    subprocess.check_call(
        [sys.executable, '-m', 'pip', 'install', '--only-binary=:all:', *arguments],
        env=environment,
    )
