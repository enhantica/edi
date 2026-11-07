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

ORIGIN_CHECK = """
import importlib.metadata as m, importlib.util as u, json, pathlib, sys
url, digest, imported = sys.argv[1:4]
try:
    dist = m.distribution("easydiffraction")
except m.PackageNotFoundError:
    sys.exit(print("false"))
info = json.loads(dist.read_text("direct_url.json") or "{}")
archive = info.get("archive_info", {})
hashed = digest in (archive.get("hashes", {}).get("sha256"), archive.get("hash", "")[7:])
root = pathlib.Path(dist.locate_file("")).resolve()
spec = u.find_spec("edi")
paths = [spec.origin if spec else "", imported or (spec.origin if spec else "")]
inside = all(path and pathlib.Path(path).resolve().is_relative_to(root) for path in paths)
owners = m.packages_distributions().get("edi")
print(json.dumps(info.get("url") == url and hashed and inside and owners == ["easydiffraction"]))
"""


def install_edi(index: str) -> None:
    """Make ``import edi`` load the wheel EasyDiffraction's index lists, and prove it did.

    pip never chooses the package: the wheel's URL and sha256 come from our index page and are
    installed as a direct reference, so other indexes, find-links or pip configuration cannot
    supply it, and an unreachable index stops here. Its dependencies are then installed by name
    with the usual pip settings, which cannot reselect the package itself. An edi that no pip
    distribution owns is a source build and is used as it is.
    """
    spec = importlib.util.find_spec('edi')
    if spec is not None and not importlib.metadata.packages_distributions().get('edi'):
        print('Using edi from', spec.origin, '(a source build, not installed by pip)')
        return
    url, digest = _wheel(index)
    imported = getattr(sys.modules.get('edi'), '__file__', '') or ''
    if _ours(url, digest, imported):
        return
    if 'edi' in sys.modules:
        raise RuntimeError(
            'A different edi is already imported. Restart the kernel and run this cell first.'
        )
    _pip('--no-deps', '--force-reinstall', f'easydiffraction @ {url}#sha256={digest}')
    requires = subprocess.check_output(
        [
            sys.executable,
            '-c',
            (
                'import importlib.metadata as m, json; '
                "print(json.dumps(m.requires('easydiffraction') or []))"
            ),
        ],
        text=True,
    )
    if json.loads(requires):
        _pip(*json.loads(requires), settings=True)
    if not _ours(url, digest, ''):
        raise RuntimeError('The installed easydiffraction is not the wheel from ' + index)
    importlib.invalidate_caches()


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


def _ours(url: str, digest: str, imported: str) -> bool:
    result = subprocess.run(
        [sys.executable, '-c', ORIGIN_CHECK, url, digest, imported],
        capture_output=True,
        text=True,
        check=True,
    )
    return json.loads(result.stdout)


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
