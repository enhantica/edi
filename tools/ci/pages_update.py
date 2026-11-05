#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-3-Clause
"""Publish one site component while preserving the last deployed counterpart."""

import argparse
import hashlib
import json
import re
import shutil
import subprocess
import tarfile
import tempfile
import xml.etree.ElementTree as ET  # noqa: S405 - qualified Pages artifacts
from operator import itemgetter
from pathlib import Path


def deployed_base(artifacts, read_jobs) -> dict:
    """Find the newest artifact with a successful matching deployment step."""
    for artifact in sorted(artifacts, key=itemgetter('created_at'), reverse=True):
        if artifact.get('expired'):
            continue
        name = artifact['name']
        match = re.fullmatch(r'pages-site-(docs|wasm|installers|release)-(\d+)', name)
        if name != 'github-pages' and not match:
            continue
        component = match[1] if match else None
        attempt = int(match[2]) if match else None
        labels = {
            'docs': 'documentation',
            'wasm': 'WebAssembly',
            'installers': 'installers',
            'release': 'release',
        }
        step_name = (
            f'Deploy {labels[component]} to GitHub Pages'
            if component
            else 'Deploy to GitHub Pages'
        )
        jobs = read_jobs(artifact['workflow_run']['id'], attempt)
        for job in jobs:
            if any(
                step.get('name') == step_name
                and step.get('conclusion') == 'success'
                and step.get('completed_at', '') >= artifact['created_at']
                for step in job.get('steps', [])
            ):
                return artifact
    raise RuntimeError(
        'No retained deployed site artifact; build and publish a complete site first'
    )


def overlay_component(site: Path, incoming: Path, component: str) -> None:
    """Replace only the built component in a disposable copy of the deployed site."""
    if not (site / 'index.html').is_file() or not (site / 'webapp/index.html').is_file():
        raise RuntimeError('The deployed base must contain documentation and the web app')
    if component == 'docs':
        if not (incoming / 'index.html').is_file() or any(
            (incoming / name).exists()
            for name in ['webapp', 'repository', 'third-party', 'releases']
        ):
            raise RuntimeError(
                'Documentation must have an index and must not own '
                '/webapp/, /repository/, /third-party/ or /releases/'
            )
        for child in site.iterdir():
            if child.name in {'webapp', 'repository', 'third-party', 'releases'}:
                continue
            if child.is_dir() and not child.is_symlink():
                shutil.rmtree(child)
            else:
                child.unlink()
        shutil.copytree(incoming, site, dirs_exist_ok=True)
    elif component == 'wasm':
        shutil.rmtree(site / 'webapp')
        subprocess.run(
            ['bash', str(Path(__file__).with_name('docs-webapp.sh')), str(incoming), str(site)],
            check=True,
        )
    elif component == 'release':
        overlay_release(site, incoming)
    elif component == 'installers':
        overlay_installers(site, incoming)
    else:
        raise ValueError('Unknown site component')


def overlay_release(site: Path, incoming: Path) -> None:
    """Publish matching native repositories and their feed in one site deployment."""
    if {item.name for item in incoming.iterdir()} != {'repository', 'releases'}:
        raise RuntimeError('Release publication requires component repositories and its feed')
    feed = incoming / 'releases/stable.json'
    if feed.is_symlink() or not feed.is_file() or feed.stat().st_size > 1024 * 1024:
        raise RuntimeError('Release feed must be a bounded regular file')
    overlay_installers(site, incoming / 'repository')
    (site / 'releases').mkdir(exist_ok=True)
    shutil.copy2(feed, site / 'releases/stable.json')


def overlay_installers(site: Path, incoming: Path) -> None:
    """Replace complete platform repositories while retaining the other published platforms."""
    channels = list(incoming.iterdir())
    allowed = {'linux-x86_64', 'macos-arm64', 'windows-x86_64'}
    policy = json.loads(
        (Path(__file__).resolve().parents[2] / 'data/distribution.json').read_text(
            encoding='utf-8'
        )
    )
    repositories = []
    if not channels:
        raise RuntimeError('Installer input must contain a publication channel')
    for channel in channels:
        if (
            channel.name not in {'testing', 'stable'}
            or not channel.is_dir()
            or channel.is_symlink()
        ):
            raise RuntimeError('Installer input has an unknown publication channel')
        parts = [
            part
            for part in channel.iterdir()
            if not (channel.name == 'testing' and part.name == 'feed.json')
        ]
        if not parts or any(
            part.name not in allowed or not part.is_dir() or part.is_symlink() for part in parts
        ):
            raise RuntimeError('Installer input must contain known platform directories')
        for part in parts:
            if not (part / 'Updates.xml').is_file():
                raise RuntimeError(f'Installer repository is incomplete: {part.name}')
            path = policy['repository_paths'][channel.name].format(platform=part.name)
            repositories.append((part, site / path))
    for part, target in repositories:
        for source in part.rglob('*'):
            if source.is_symlink():
                raise RuntimeError('Installer repository must not contain symbolic links')
            relative = source.relative_to(part)
            previous = target / relative
            mutable = relative.as_posix() in {
                'Updates.xml',
                'Updates.xml.sha1',
                'Updates.xml.sha256',
            }
            if source.is_file() and previous.exists() and not mutable:
                with source.open('rb') as new, previous.open('rb') as old:
                    if (
                        hashlib.file_digest(new, 'sha256').digest()
                        != hashlib.file_digest(old, 'sha256').digest()
                    ):
                        raise RuntimeError(f'Installer archive identity was reused: {relative}')
    for part, target in repositories:
        shutil.copytree(part, target, dirs_exist_ok=True)
    overlay_testing_feed(site, incoming / 'testing/feed.json')


def overlay_testing_feed(site: Path, feed: Path) -> None:
    if not feed.exists():
        return
    if feed.is_symlink() or not feed.is_file() or feed.stat().st_size > 1024 * 1024:
        raise RuntimeError('Testing update feed must be a bounded regular file')
    current = json.loads(feed.read_text(encoding='utf-8'))
    if current.get('schema') != 'edi.preview-releases/1' or len(current['releases']) != 1:
        raise RuntimeError('Expected one testing release in the incoming feed')
    target = site / 'releases/testing.json'
    if target.is_file():
        previous = json.loads(target.read_text(encoding='utf-8'))
        if previous.get('sequence') == current.get('sequence'):
            version = current['releases'][0]['version']
            if tuple(map(int, version.split('.'))) < tuple(
                map(int, previous['releases'][0]['version'].split('.'))
            ):
                raise RuntimeError('Testing update feed cannot move backwards')
            current['releases'].extend(
                entry for entry in previous['releases'][:19] if entry['version'] != version
            )
        elif current.get('sequence') != 'calendar':
            raise RuntimeError('Testing update feed must use the calendar sequence')
    target.parent.mkdir(exist_ok=True)
    target.write_text(json.dumps(current, indent=2) + '\n', encoding='utf-8')
    if current.get('sequence') == 'calendar' and len(current['releases']) >= 2:
        keep = {entry['version'] for entry in current['releases'][:2]}
        for platform in feed.parent.iterdir():
            if (platform / 'Updates.xml').is_file():
                trim_testing_archives(site / 'repository/testing' / platform.name, keep)


def trim_testing_archives(repository: Path, keep: set[str]) -> None:
    archive_name = re.compile(r'^([0-9]+(?:\.[0-9]+)+)[A-Za-z_-].*\.7z(?:\.sha1)?$')
    packages = {'org.easyscience.edi', 'org.easyscience.edi.assistant'}
    for archive in repository.glob('*/*'):
        match = archive_name.fullmatch(archive.name)
        if (
            archive.parent.name in packages
            and match
            and match[1] not in keep
            and archive.is_file()
        ):
            archive.unlink()


def check_site_size(site: Path, limit: int = 1_000_000_000) -> int:
    """Keep the deployed site within the Pages size limit."""

    def measure():
        return sum(path.stat().st_size for path in site.rglob('*') if path.is_file())

    size = measure()
    if size > limit:
        for metadata in (site / 'repository/testing').glob('*/Updates.xml'):
            document = ET.parse(metadata)  # noqa: S314 - qualified Pages artifact
            versions = {item.findtext('Version') for item in document.findall('PackageUpdate')}
            if versions and None not in versions:
                trim_testing_archives(metadata.parent, versions)
        size = measure()
    if size > limit:
        raise RuntimeError(f'Assembled Pages site is too large: {size} bytes (limit {limit})')
    print(f'Assembled Pages site: {size} bytes')
    return size


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--repo', required=True)
    parser.add_argument(
        '--component', choices=('docs', 'wasm', 'installers', 'release'), required=True
    )
    parser.add_argument('--incoming', type=Path, required=True)
    parser.add_argument('--site', type=Path, required=True)
    args = parser.parse_args()
    if args.site.exists():
        raise RuntimeError('The site assembly destination must be fresh')
    response = subprocess.check_output(
        [
            'gh',
            'api',
            '--paginate',
            '--slurp',
            f'repos/{args.repo}/actions/artifacts?per_page=100',
        ],
        text=True,
    )
    artifacts = [artifact for page in json.loads(response) for artifact in page['artifacts']]

    def read_jobs(run, attempt):
        suffix = f'/attempts/{attempt}' if attempt else ''
        response = subprocess.check_output(
            [
                'gh',
                'api',
                '--paginate',
                '--slurp',
                f'repos/{args.repo}/actions/runs/{run}{suffix}/jobs?per_page=100',
            ],
            text=True,
        )
        return [job for page in json.loads(response) for job in page['jobs']]

    artifact = deployed_base(artifacts, read_jobs)
    print(
        f'Preserving deployed site from run {artifact["workflow_run"]["id"]}, '
        f'artifact {artifact["id"]}'
    )
    with tempfile.TemporaryDirectory(prefix='edi-pages-') as folder:
        subprocess.run(
            [
                'gh',
                'run',
                'download',
                str(artifact['workflow_run']['id']),
                '--repo',
                args.repo,
                '--name',
                artifact['name'],
                '--dir',
                folder,
            ],
            check=True,
        )
        args.site.mkdir(parents=True)
        with tarfile.open(Path(folder) / 'artifact.tar') as archive:
            archive.extractall(args.site, filter='data')
    overlay_component(args.site, args.incoming, args.component)
    check_site_size(args.site)


if __name__ == '__main__':
    main()
