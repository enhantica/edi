# SPDX-License-Identifier: BSD-3-Clause
"""Recover qualified desktop components for Pages publication."""

import argparse
import json
import shutil
import subprocess
import tempfile
from pathlib import Path

from promote import PLATFORMS, ROOT, api, digest, extract, validate_repository


def stage(repo: str, branch: str, run_id: int, output: Path) -> None:
    run = api(repo, f'actions/runs/{run_id}')
    if (
        run['path'] != '.github/workflows/installers.yml'
        or run['status'] != 'completed'
        or run['head_branch'] != branch
        or run['head_repository']['full_name'] != repo
    ):
        raise ValueError('Preview requires a completed desktop installer run on this branch')
    artifacts = api(repo, f'actions/runs/{run_id}/artifacts?per_page=100')['artifacts']
    attempt = qualified_attempt(repo, run_id, run['run_attempt'], artifacts)
    history = None
    output.mkdir(parents=True)
    with tempfile.TemporaryDirectory(prefix='edi-installer-preview-') as temporary:
        scratch = Path(temporary)
        for platform in PLATFORMS:
            delivery = recover_artifact(
                repo, artifacts, f'installer-{platform}-{attempt}', scratch
            )
            components = recover_artifact(
                repo, artifacts, f'installer-components-{platform}-{attempt}', scratch
            )
            recorded = delivery / 'preview-history.json'
            if not recorded.is_file():
                raise ValueError('Only a calendar preview can be recovered for publication')
            payload = recorded.read_bytes()
            if history is not None and payload != history:
                raise ValueError('Preview release histories differ')
            history = payload
            record = json.loads(payload)
            (release,) = record['releases']
            if record['sequence'] != 'calendar' or release['commit'] != run['head_sha']:
                raise ValueError('Preview history differs from the qualified source')
            version = release['version']
            copy_preview(
                delivery, components, output, PLATFORMS[platform], version, run['head_sha']
            )
    (output / 'components/testing/feed.json').write_bytes(history)
    print(f'Qualified preview {version} from {run["head_sha"]}, attempt {attempt}')


def qualified_attempt(repo: str, run_id: int, latest: int, artifacts: list[dict]) -> int:
    """The newest attempt that built and kept every platform itself.

    A rerun of only the draft job makes a later attempt with no installers, so the last attempt
    is not necessarily the qualified one; platforms are never combined across attempts.
    """
    retained = {item['name'] for item in artifacts if not item['expired']}
    for attempt in range(latest, 0, -1):
        jobs = api(repo, f'actions/runs/{run_id}/attempts/{attempt}/jobs?per_page=100')['jobs']
        built = all(
            [job['conclusion'] for job in jobs if job['name'] == f'installer · {platform}']
            == ['success']
            and {f'installer-{platform}-{attempt}', f'installer-components-{platform}-{attempt}'}
            <= retained
            for platform in PLATFORMS
        )
        if built:
            return attempt
    raise ValueError('No attempt of this run built and kept every platform')


def recover_artifact(repo: str, artifacts: list[dict], name: str, scratch: Path) -> Path:
    matches = [item['id'] for item in artifacts if item['name'] == name and not item['expired']]
    if len(matches) != 1:
        raise ValueError(f'Missing or ambiguous preview artifact: {name}')
    archive = scratch / (name + '.zip')
    with archive.open('wb') as stream:
        subprocess.run(
            ['gh', 'api', f'repos/{repo}/actions/artifacts/{matches[0]}/zip'],
            stdout=stream,
            check=True,
        )
    folder = scratch / name
    extract(archive, folder)
    archive.unlink()
    return folder


def copy_preview(
    delivery: Path, components: Path, output: Path, platform: str, version: str, commit: str
) -> None:
    policy = json.loads((ROOT / 'data/distribution.json').read_text())
    name = f'EasyDiffraction-{version}-{platform}-online.zip'
    url = policy['primary_base'] + policy['repository_paths']['testing'].format(platform=platform)
    metadata = json.loads((delivery / 'installer.json').read_text())
    build = json.loads((delivery / 'build-inputs.json').read_text())
    qualification = json.loads((delivery / 'qualification.json').read_text())
    expected = {
        'zip': name,
        'version': version,
        'platform': platform,
        'kind': 'online',
        'edi_commit': commit,
        'repository_url': url,
    }
    if (
        any(metadata.get(key) != value for key, value in expected.items())
        or build['edi_commit'] != commit
        or qualification.get('passed') is not True
        or qualification.get('smoke', {}).get('passed') is not True
        or digest(delivery / name) != metadata['zip_sha256']
    ):
        raise ValueError(f'Preview delivery identity or qualification differs: {platform}')
    repository = components / 'testing' / platform
    packages = frozenset(item.name for item in repository.iterdir() if item.is_dir())
    if packages not in (
        {'org.easyscience.edi'},
        {'org.easyscience.edi', 'org.easyscience.edi.assistant'},
    ):
        raise ValueError(f'Unknown preview component set: {platform}')
    validate_repository(repository, version, expected=packages)
    shutil.copytree(repository, output / 'components' / 'testing' / platform)
    (output / 'assets').mkdir(exist_ok=True)
    shutil.copy2(delivery / name, output / 'assets' / name)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--repo', required=True)
    parser.add_argument('--branch', required=True)
    parser.add_argument('--run', type=int, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    stage(args.repo, args.branch, args.run, args.output)


if __name__ == '__main__':
    main()
