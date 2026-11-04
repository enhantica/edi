#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-3-Clause
"""Publish one site component while preserving the last deployed counterpart."""

import argparse
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
        match = re.fullmatch(r'pages-site-(docs|wasm)-(\d+)', name)
        if name != 'github-pages' and not match:
            continue
        component = match[1] if match else None
        attempt = int(match[2]) if match else None
        step_name = (
            f'Deploy {"documentation" if component == "docs" else "WebAssembly"} to GitHub Pages'
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
        if not (incoming / 'index.html').is_file() or (incoming / 'webapp').exists():
            raise RuntimeError('Documentation must have an index and must not own /webapp/')
        for child in site.iterdir():
            if child.name == 'webapp':
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
    else:
        raise ValueError('Unknown site component')


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--repo', required=True)
    parser.add_argument('--component', choices=('docs', 'wasm'), required=True)
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


if __name__ == '__main__':
    main()
