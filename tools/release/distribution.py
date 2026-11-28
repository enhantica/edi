#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-3-Clause
"""Write one release's downloads as three copies of one layout, and check them.

One distribution scheme for every download (edi ADR-0071 as amended): the wheels and their index,
the command-line zips, the installers, the installer components and the update feeds share one
layout, written as three copies:

- ``release/``: every file attached to the GitHub release, the component repositories as one
  archive per channel and platform, each stable component archive on its own, a small index of
  each stable repository, and ``SHA256SUMS`` over all of them;
- ``pages/``: the layout as GitHub Pages serves it at the current release;
- ``offsite/``: the same tree, kept as the publish run's ``offsite`` artifact.

The layout of ``pages/`` and ``offsite/``: ``pypi/simple/easydiffraction/`` the package index with
the current wheels beside it and older versions linked to their GitHub releases (the docs build
writes the same index, website/render_package_index.py), ``releases/<version>/`` every file,
``repository/<channel>/<platform>/`` the installers' component repositories,
``releases/stable-v2.json`` the update feed, ``releases/stable.json`` the feed apps up to
v2026.11.31 read (legacy_feed.py), and ``SHA256SUMS`` over the whole tree.

The apps' feed bases (data/distribution.json) do not serve ``pages/`` or ``offsite/``: the site
behind both is built by enhantica/edi-download from the GitHub release's assets with these tools,
its two feeds with ``legacy_feed.write_feeds``. The download site serves each stable repository
from its index, ``repoindex-stable-<platform>.tar.gz``: everything but the component archives, and
``redirect.htaccess``, the rules edi-download puts in the site's ``.htaccess`` to redirect each
archive to its release asset (edi ADR-0071).

    python tools/release/distribution.py --publication publication --output copies --repo <repo>
    python tools/release/distribution.py --dry-run --output copies   # a fixture, then the checks
"""

from __future__ import annotations

import argparse
import functools
import gzip
import hashlib
import http.server
import json
import os
import re
import shutil
import subprocess
import sys
import tarfile
import tempfile
import threading
import urllib.parse
import xml.etree.ElementTree as ET  # noqa: S405 - promote.py bounded the metadata, no DTDs
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'website'))
sys.path.insert(0, str(ROOT / 'tools/release'))
from legacy_feed import write_feeds  # noqa: E402
from promote import ARCHIVE_NAME, COMPONENT_ID, component_asset, withheld  # noqa: E402
from render_package_index import RELEASES, write_package_index  # noqa: E402
from versions import PATTERN, version_key  # noqa: E402

PROJECT = 'easydiffraction'


def sha256(path: Path) -> str:
    """The file's sha256, hex."""
    return hashlib.sha256(path.read_bytes()).hexdigest()


def manifest(folder: Path, skip: str = 'SHA256SUMS') -> str:
    """`SHA256SUMS` over every file under `folder`, by its path inside it."""
    files = sorted(p for p in folder.rglob('*') if p.is_file() and p.name != skip)
    return ''.join(f'{sha256(p)}  {p.relative_to(folder).as_posix()}\n' for p in files)


def current_release(version: str, files: Path) -> dict:
    """The release as GitHub will list it once published, so the index can name its wheels."""
    return {
        'draft': False,
        'tag_name': f'v{version}',
        'assets': [
            {
                'name': wheel.name,
                'state': 'uploaded',
                'browser_download_url': f'{RELEASES}/v{version}/{wheel.name}',
                'digest': f'sha256:{sha256(wheel)}',
            }
            for wheel in sorted(files.glob('*.whl'))
        ],
    }


def published_releases(repo: str, version: str) -> list[list[dict]]:
    """The repository's releases as GitHub lists them, page by page, without this version."""
    pages = json.loads(
        subprocess.check_output(['gh', 'api', '--paginate', '--slurp', f'repos/{repo}/releases'])
    )
    return [[r for r in page if r.get('tag_name') != f'v{version}'] for page in pages]


def build(publication: Path, output: Path, published: list[list[dict]] | None = None) -> None:
    """The three copies of the release in `publication` (tools/release/promote.py's output).

    `published` is the repository's releases as GitHub lists them: the index links their wheels.
    """
    release = json.loads((publication / 'release.json').read_text(encoding='utf-8'))
    version = release['version']
    assets, incoming = publication / 'assets', publication / 'incoming'
    shutil.rmtree(output, ignore_errors=True)
    tree = output / 'pages'
    files = tree / 'releases' / version
    files.mkdir(parents=True)
    # The builds' own component zips are left out: the release carries the same repositories as one
    # archive per channel and platform with the copies' paths, written below.
    for asset in sorted(assets.iterdir()):
        if asset.name != 'SHA256SUMS' and not asset.name.endswith('-components.zip'):
            shutil.copy2(asset, files / asset.name)
    # Each channel's repositories at the paths the installers read (data/distribution.json).
    paths = json.loads((ROOT / 'data/distribution.json').read_text(encoding='utf-8'))
    for channel in sorted((incoming / 'repository').iterdir()):
        for platform in sorted(channel.iterdir()):
            where = paths['repository_paths'][channel.name].format(platform=platform.name)
            shutil.copytree(platform, tree / where.rstrip('/'))
    # The update feeds: stable-v2.json, and the legacy stable.json apps up to v2026.11.31 read.
    for feed in ('stable-v2.json', 'stable.json'):
        shutil.copy2(incoming / 'releases' / feed, tree / 'releases' / feed)
    write_package_index(
        tree,
        [*(published or []), [current_release(version, files)]],
        fetch=lambda _tag, name, folder: shutil.copy2(files / name, folder / name),
    )
    (tree / 'SHA256SUMS').write_text(manifest(tree), encoding='utf-8')
    shutil.copytree(tree, output / 'offsite')
    # The release: every file of this version, and each component repository as one archive.
    attached = output / 'release'
    attached.mkdir()
    for asset in sorted(files.iterdir()):
        shutil.copy2(asset, attached / asset.name)
    for channel in sorted((incoming / 'repository').iterdir()):
        for platform in sorted(channel.iterdir()):
            where = paths['repository_paths'][channel.name].format(platform=platform.name)
            name = f'repository-{channel.name}-{platform.name}.tar.gz'
            reproducible_archive(tree / where.rstrip('/'), where.rstrip('/'), attached / name)
    # The stable archives on their own, and what the download site serves itself (edi ADR-0071).
    with tempfile.TemporaryDirectory() as scratch:
        for platform in sorted((incoming / 'repository/stable').iterdir()):
            where = paths['repository_paths']['stable'].format(platform=platform.name).rstrip('/')
            index = Path(scratch) / platform.name
            attach_components(tree / where, where, platform.name, attached, index)
            name = f'repoindex-stable-{platform.name}.tar.gz'
            reproducible_archive(index, where, attached / name)
    (attached / 'SHA256SUMS').write_text(manifest(attached), encoding='utf-8')


def downloadable_archives(repository: Path) -> list[tuple[str, str, str]]:
    """Each archive a component repository's Updates.xml lists: component, version, file name."""
    updates = ET.fromstring((repository / 'Updates.xml').read_bytes())  # noqa: S314 - see import
    return [
        (package.findtext('Name'), package.findtext('Version'), name)
        for package in updates.findall('PackageUpdate')
        for name in package.findtext('DownloadableArchives', '').split(',')
        if name
    ]


def attach_components(
    repository: Path, where: str, platform: str, attached: Path, index: Path
) -> None:
    """Attach each archive of a stable repository as a release asset; copy the rest to `index`.

    The index is what the download site serves itself at `where`: Updates.xml, every .sha1 and
    meta.7z, and the redirect rules that send the archives to their assets.
    """
    archives = {}
    for component, version, name in downloadable_archives(repository):
        if withheld(component):
            raise ValueError(f'{component} is withheld from public downloads')
        archives[f'{component}/{version}{name}'] = component_asset(
            platform, component, version, name
        )
    index.mkdir(parents=True)
    for path in sorted(p for p in repository.rglob('*') if p.is_file()):
        relative = path.relative_to(repository).as_posix()
        target = attached / archives[relative] if relative in archives else index / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, target)
    (index / RULE_FILE).write_text(redirect_rules(where, platform), encoding='utf-8')


# The index file holding the redirect rules. edi-download puts them in the download site's
# .htaccess, so their paths start at the site root.
RULE_FILE = 'redirect.htaccess'


def redirect_rules(where: str, platform: str) -> str:
    """The download site's redirect rules for one platform's stable repository at `where`.

    A component archive the site does not hold is redirected to the asset of the release its
    version names. Every file the site holds is served as it is, Updates.xml, the .sha1 files and
    meta.7z among them: the installer fetches an archive from wherever its .sha1 finally came
    from, so a redirected .sha1 fails.
    """
    return (
        'RewriteCond %{REQUEST_FILENAME} !-f\n'
        f'RewriteRule ^{where}/({COMPONENT_ID})/({PATTERN})({ARCHIVE_NAME})$'
        f' {RELEASES}/v$2/component-{platform}-$1-$2$3 [R=302,L]\n'
    )


def redirected(rules: str, path: str) -> str | None:
    """Where rules from redirect_rules send a request for a `path` the site does not hold."""
    for line in rules.splitlines():
        if line.startswith('RewriteRule '):
            _, pattern, target, _ = line.split(' ')
            if match := re.match(pattern, path):
                return re.sub(r'\$(\d)', lambda m: match[int(m[1])], target)
    return None


def reproducible_archive(folder: Path, root: str, archive: Path) -> None:
    """`folder` as a gzipped tar under `root`, the same bytes whenever it is rebuilt.

    A retried publication rebuilds the archives and must match what it uploaded first, so the
    gzip header carries no time and every member a fixed time, owner and mode, in path order.
    """

    def entry(path: Path) -> tarfile.TarInfo:
        relative = path.relative_to(folder).as_posix()
        info = tarfile.TarInfo(root if relative == '.' else f'{root}/{relative}')
        info.mtime, info.uid, info.gid, info.uname, info.gname = 0, 0, 0, '', ''
        if path.is_dir():
            info.type, info.mode = tarfile.DIRTYPE, 0o755
        else:
            info.size, info.mode = path.stat().st_size, 0o644
        return info

    with (
        archive.open('wb') as raw,
        gzip.GzipFile(fileobj=raw, mode='wb', mtime=0, filename='') as zipped,
        tarfile.open(fileobj=zipped, mode='w', format=tarfile.PAX_FORMAT) as tar,
    ):
        for path in [folder, *sorted(folder.rglob('*'))]:
            if path.is_symlink():
                raise ValueError(f'{path}: component repositories hold no links')
            info = entry(path)
            if path.is_dir():
                tar.addfile(info)
            else:
                with path.open('rb') as data:
                    tar.addfile(info, data)


def attachment_problems(pages: Path, attached: Path, version: str) -> list[str]:
    """A release file not attached as published, or component archives that differ."""
    problems = [
        f'release: {path.name} is not attached as published'
        for path in sorted((pages / 'releases' / version).iterdir())
        if not (attached / path.name).is_file() or sha256(attached / path.name) != sha256(path)
    ]
    with tempfile.TemporaryDirectory() as scratch:
        for archive in sorted(attached.glob('repository-*.tar.gz')):
            with tarfile.open(archive) as opened:
                opened.extractall(scratch, filter='data')
        if manifest(Path(scratch) / 'repository') != manifest(pages / 'repository'):
            problems.append('release: the component archives differ from the repositories')
    return problems


def component_problems(pages: Path, attached: Path, version: str) -> list[str]:
    """Every stable platform's index and archive assets, checked against its repository."""
    full = sorted(p.name.removeprefix('repository-') for p in attached.glob('repository-stable-*'))
    indexes = sorted(attached.glob('repoindex-stable-*.tar.gz'))
    problems = []
    if full != [p.name.removeprefix('repoindex-') for p in indexes]:
        problems.append('release: not every stable platform has its repository index')
    paths = json.loads((ROOT / 'data/distribution.json').read_text(encoding='utf-8'))
    named: set[str] = set()
    with tempfile.TemporaryDirectory() as scratch:
        for archive in indexes:
            platform = archive.name.removeprefix('repoindex-stable-').removesuffix('.tar.gz')
            where = paths['repository_paths']['stable'].format(platform=platform).rstrip('/')
            with tarfile.open(archive) as opened:
                opened.extractall(Path(scratch) / platform, filter='data')
            index = Path(scratch) / platform / where
            problems += [
                f'{archive.name}: {problem}'
                for problem in repository_index_problems(
                    index, pages / where, where, attached, version, named
                )
            ]
    if named != {p.name for p in attached.glob('component-*')}:
        problems.append('release: the component assets are not exactly the stable archives')
    return problems


def repository_index_problems(
    index: Path, repository: Path, where: str, attached: Path, version: str, named: set[str]
) -> list[str]:
    """What the download site would serve wrongly from one platform's index at `where`.

    The site serves every file it holds, and no rule may match a .sha1. Each archive, which it
    does not hold, must be redirected to its own release asset. The asset names go into `named`.
    """
    rules = (index / RULE_FILE).read_text(encoding='utf-8')
    archives = {f'{c}/{v}{n}' for c, v, n in downloadable_archives(repository)}
    served = {p.relative_to(index).as_posix() for p in index.rglob('*') if p.is_file()}
    problems, expected = [], {RULE_FILE}
    for path in sorted(p for p in repository.rglob('*') if p.is_file()):
        relative = path.relative_to(repository).as_posix()
        target = redirected(rules, f'{where}/{relative}')
        if relative not in archives:
            expected.add(relative)
            if relative not in served or sha256(index / relative) != sha256(path):
                problems.append(f'{relative} is not served as it is')
            elif target and relative.endswith('.sha1'):
                problems.append(f'{relative}: a rule matches it')
            continue
        asset = (target or '').removeprefix(f'{RELEASES}/v{version}/')
        named.add(asset)
        if (
            '/' in asset
            or not (attached / asset).is_file()
            or sha256(attached / asset) != sha256(path)
        ):
            problems.append(f'{relative} is not sent to its release asset')
    return problems + [
        f'{extra} does not belong in the index' for extra in sorted(served - expected)
    ]


def link_problems(copy: Path) -> list[str]:
    """An index link that leaves its copy, leads nowhere, or names another file's sha256."""
    problems = []
    pattern = r'href="([^"#]+)(?:#sha256=([0-9a-f]+))?"'
    for page in copy.rglob('index.html'):
        for href, digest in re.findall(pattern, page.read_text(encoding='utf-8')):
            if href.startswith(RELEASES + '/'):
                continue  # an older version, on its GitHub release
            target = (page.parent / urllib.parse.unquote(href)).resolve()
            where = page.relative_to(copy)
            if not str(target).startswith(str(copy.resolve())) or not target.exists():
                problems.append(f'{copy.name}: {where} links {href} outside or nowhere')
            elif digest and sha256(target) != digest:
                problems.append(f'{copy.name}: {href} does not match its sha256')
    return problems


def index_problems(copy: Path, published: list[list[dict]]) -> list[str]:
    """A published older wheel the index does not link to its GitHub release."""
    page = (copy / 'pypi/simple' / PROJECT / 'index.html').read_text(encoding='utf-8')
    return [
        f'{copy.name}: the index does not link {asset["name"]}'
        for release in (r for p in published for r in p if not r.get('draft'))
        for asset in release.get('assets', [])
        if asset['name'].endswith('.whl') and asset.get('browser_download_url', '') not in page
    ]


def check(output: Path, version: str, published: list[list[dict]] = ()) -> list[str]:
    """Every way the three copies could disagree, named; empty when they agree."""
    problems = index_problems(output / 'pages', published)
    pages, offsite, attached = output / 'pages', output / 'offsite', output / 'release'
    if manifest(pages) != manifest(offsite):
        problems.append('the Pages and off-GitHub trees differ')
    problems += [
        f'{folder.name}: SHA256SUMS does not describe it'
        for folder in (pages, offsite, attached)
        if (folder / 'SHA256SUMS').read_text(encoding='utf-8') != manifest(folder)
    ]
    problems += attachment_problems(pages, attached, version)
    problems += component_problems(pages, attached, version)
    return problems + link_problems(pages) + link_problems(offsite)


class Failover(http.server.SimpleHTTPRequestHandler):
    """The download address in front of the copies: the off-GitHub copy, else Pages."""

    copies: tuple[Path, ...] = ()

    def translate_path(self, path: str) -> str:
        """The first copy that holds the path."""
        relative = urllib.parse.unquote(urllib.parse.urlsplit(path).path).lstrip('/')
        for copy in self.copies:
            candidate = copy / relative
            if candidate.exists():
                return str(candidate)
        return str(self.copies[-1] / relative)

    def log_message(self, *args: object) -> None:
        """Say nothing."""


def install_through(copies: tuple[Path, ...], version: str) -> str:
    """Fetch the wheel with pip through the failover address; the error, or empty on success."""
    handler = type('Handler', (Failover,), {'copies': copies})
    server = http.server.ThreadingHTTPServer(
        ('127.0.0.1', 0), functools.partial(handler, directory=str(copies[-1]))
    )
    threading.Thread(target=server.serve_forever, daemon=True).start()
    try:
        with tempfile.TemporaryDirectory() as scratch:
            index = f'http://127.0.0.1:{server.server_address[1]}/pypi/simple/'
            result = subprocess.run(
                [
                    sys.executable,
                    '-m',
                    'pip',
                    'download',
                    '--no-deps',
                    '--no-cache-dir',
                    '--isolated',
                    '--index-url',
                    index,
                    '--dest',
                    scratch,
                    f'{PROJECT}=={version}',
                ],
                capture_output=True,
                text=True,
                check=False,
                timeout=120,
            )
            got = list(Path(scratch).glob('*.whl'))
            return (
                ''
                if result.returncode == 0 and got
                else (result.stderr.strip().splitlines() or ['no wheel'])[-1]
            )
    finally:
        server.shutdown()


def fixture(folder: Path, version: str = '2026.11.0') -> None:
    """A release as promote.py stages it: installers, CLI zips, wheels, components and the feed."""
    assets, incoming = folder / 'assets', folder / 'incoming'
    assets.mkdir(parents=True)
    for platform, tag in (
        ('linux-x86_64', 'linux_x86_64'),
        ('macos-arm64', 'macosx_14_0_arm64'),
        ('windows-x86_64', 'win_amd64'),
    ):
        wheel = assets / f'{PROJECT}-{version}-cp312-abi3-{tag}.whl'
        info = f'{PROJECT}-{version}.dist-info'
        with zipfile.ZipFile(wheel, 'w') as archive:
            archive.writestr(
                f'{info}/METADATA', f'Metadata-Version: 2.1\nName: {PROJECT}\nVersion: {version}\n'
            )
            archive.writestr(
                f'{info}/WHEEL',
                f'Wheel-Version: 1.0\nRoot-Is-Purelib: false\nTag: cp312-abi3-{tag}\n',
            )
            archive.writestr(f'{info}/RECORD', '')
        (assets / f'easydiffraction-cli-{version}-{platform}.zip').write_bytes(
            f'cli {platform}'.encode()
        )
        (assets / f'EasyDiffraction-{version}-{platform}-installer.bin').write_bytes(
            f'installer {platform}'.encode()
        )
        (assets / f'EasyDiffraction-{version}-{platform}-stable-components.zip').write_bytes(
            f'components {platform}'.encode()
        )
        # One component in repogen's layout: its archives, their .sha1 files and its meta.7z.
        components = incoming / 'repository/stable' / platform
        app = components / 'org.easydiffraction.app'
        app.mkdir(parents=True)
        for name in ('bin.7z', 'EasyDiffraction.app.7z', 'meta.7z'):
            (app / f'{version}{name}').write_bytes(f'{name} {platform}'.encode())
            if name != 'meta.7z':
                digest = hashlib.sha1((app / f'{version}{name}').read_bytes()).hexdigest()  # noqa: S324
                (app / f'{version}{name}.sha1').write_text(digest)
        (components / 'Updates.xml').write_text(
            '<Updates><PackageUpdate><Name>org.easydiffraction.app</Name>'
            f'<Version>{version}</Version>'
            '<DownloadableArchives>bin.7z,EasyDiffraction.app.7z</DownloadableArchives>'
            '</PackageUpdate></Updates>\n'
        )
    release = {'version': version}
    (folder / 'release.json').write_text(json.dumps(release) + '\n')
    (assets / 'release.json').write_text(json.dumps(release) + '\n')
    (assets / 'release-history.json').write_text(json.dumps(fixture_history(version), indent=2))
    write_feeds(assets / 'release-history.json', incoming / 'releases')


def fixture_history(version: str) -> dict:
    """A release history as plan.py records it: the last old-form release, then `version`."""

    def release(name: str, day: str, commit: str, number: int) -> dict:
        note = {'title': f'Change {number}', 'pull_request': number, 'interfaces': ['desktop']}
        return {
            'version': name,
            'date': day,
            'commit': commit * 40,
            'notes': {'Added': [note], 'Fixed': [], 'Changed': []},
        }

    releases = [release(version, '2026-11-27', 'b', 2)]
    if version_key(version) > version_key('2026.11.31'):
        releases.insert(0, release('2026.11.31', '2026-11-25', 'a', 1))
    return {'schema': 'edi.releases/1', 'baseline_commit': 'c' * 40, 'releases': releases}


def older_release(version: str) -> dict:
    """A published earlier release as GitHub lists it, with one wheel."""
    name = f'{PROJECT}-{version}-cp312-abi3-linux_x86_64.whl'
    return {
        'draft': False,
        'tag_name': f'v{version}',
        'assets': [
            {
                'name': name,
                'state': 'uploaded',
                'browser_download_url': f'{RELEASES}/v{version}/{name}',
                'digest': 'sha256:' + '0' * 64,
            }
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument('--publication', type=Path, help="promote.py's output")
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument(
        '--repo', help='the GitHub repository whose older releases the index links'
    )
    parser.add_argument(
        '--dry-run', action='store_true', help='build a fixture release and check it'
    )
    args = parser.parse_args()
    with tempfile.TemporaryDirectory() as scratch:
        publication = args.publication
        published: list[list[dict]] = []
        if args.dry_run:
            publication = Path(scratch) / 'publication'
            # A YY.N release, so the legacy feed for 2026.11.x apps carries its alias.
            fixture(publication, '26.17')
            published = [[older_release('2026.10.0')]]
        if publication is None:
            parser.error('--publication or --dry-run')
        version = json.loads((publication / 'release.json').read_text(encoding='utf-8'))['version']
        if args.repo:
            published = published_releases(args.repo, version)
        build(publication, args.output, published)
        # A retried publication rebuilds the copies: the release's bytes must not depend on when.
        for path in publication.rglob('*'):
            os.utime(path, (path.stat().st_atime, path.stat().st_mtime + 3600))
        rebuilt = Path(scratch) / 'rebuilt'
        build(publication, rebuilt, published)
        same = manifest(rebuilt / 'release') == manifest(args.output / 'release')
    problems = check(args.output, version, published)
    if not same:
        problems.append('release: a rebuild an hour later writes different bytes')
    print(
        'copies agree: identical trees and manifests, every file attached, links inside each copy'
        if not problems
        else 'copies disagree:\n' + '\n'.join(problems)
    )
    # An empty off-GitHub copy: the download address still installs, from Pages.
    with tempfile.TemporaryDirectory() as empty:
        error = install_through((Path(empty), args.output / 'pages'), version)
    print(
        'empty off-GitHub copy: pip installs from Pages'
        if not error
        else f'empty off-GitHub copy: {error}'
    )
    error_full = install_through((args.output / 'offsite', args.output / 'pages'), version)
    print(
        'full off-GitHub copy: pip installs from it'
        if not error_full
        else f'full off-GitHub copy: {error_full}'
    )
    return 1 if problems or error or error_full else 0


if __name__ == '__main__':
    sys.exit(main())
