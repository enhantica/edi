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
from operator import itemgetter
from pathlib import Path


def deployed_base(artifacts, read_jobs) -> dict:
    """Find the newest artifact with a successful matching deployment step."""
    for artifact in sorted(artifacts, key=itemgetter('created_at'), reverse=True):
        if artifact.get('expired'):
            continue
        name = artifact['name']
        match = re.fullmatch(r'pages-site-(docs|wasm|installers)-(\d+)', name)
        if name != 'github-pages' and not match:
            continue
        component = match[1] if match else None
        attempt = int(match[2]) if match else None
        labels = {'docs': 'documentation', 'wasm': 'WebAssembly', 'installers': 'installers'}
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
            (incoming / name).exists() for name in ['webapp', 'repository', 'third-party']
        ):
            raise RuntimeError(
                'Documentation must have an index and must not own '
                '/webapp/, /repository/ or /third-party/'
            )
        for child in site.iterdir():
            if child.name in {'webapp', 'repository', 'third-party'}:
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
    elif component == 'installers':
        overlay_installers(site, incoming)
    else:
        raise ValueError('Unknown site component')


def overlay_installers(site: Path, incoming: Path) -> None:
    """Replace complete platform repositories while retaining the other published platforms."""
    channels = list(incoming.iterdir())
    allowed = {'linux-x86_64', 'macos-arm64', 'windows-x86_64'}
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
        parts = list(channel.iterdir())
        if not parts or any(
            part.name not in allowed or not part.is_dir() or part.is_symlink() for part in parts
        ):
            raise RuntimeError('Installer input must contain known platform directories')
        for part in parts:
            if not (part / 'Updates.xml').is_file():
                raise RuntimeError(f'Installer repository is incomplete: {part.name}')
            repositories.append((part, site / 'repository' / channel.name / part.name))
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


def check_site_size(site: Path, limit: int = 1_000_000_000) -> int:
    """Refuse a site larger than GitHub Pages' documented one-GB limit."""
    size = sum(path.stat().st_size for path in site.rglob('*') if path.is_file())
    if size > limit:
        raise RuntimeError(f'Assembled Pages site is too large: {size} bytes (limit {limit})')
    print(f'Assembled Pages site: {size} bytes')
    return size


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--repo', required=True)
    parser.add_argument('--component', choices=('docs', 'wasm', 'installers'), required=True)
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
