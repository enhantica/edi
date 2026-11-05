# SPDX-License-Identifier: BSD-3-Clause
"""Prepare a GitHub prerelease draft from qualified online installers."""

import argparse
import hashlib
import json
import re
import subprocess
import tempfile
from pathlib import Path

from plan import markdown_note, note_interfaces
from publish_assets import check_existing, optional_api

PLATFORMS = {'linux-x86_64', 'macos-arm64', 'windows-x86_64'}


def prepare(
    commit: str,
    deliveries: list[Path],
    *,
    mac_linux_only: bool = False,
) -> tuple[dict, str, list[tuple[Path, str]]]:
    """Validate all platform deliveries against their shared release history."""
    expected = PLATFORMS - {'windows-x86_64'} if mac_linux_only else PLATFORMS
    archives = {}
    history = None
    for delivery in deliveries:
        payload = (delivery / 'preview-history.json').read_bytes()
        if history is not None and payload != history:
            raise ValueError('Platform release histories differ')
        history = payload
        metadata = json.loads((delivery / 'installer.json').read_bytes())
        receipt = json.loads((delivery / 'qualification.json').read_bytes())
        platform = metadata['platform']
        version = metadata['version']
        if platform not in expected or platform in archives:
            raise ValueError('Unexpected or duplicate installer platform')
        if not re.fullmatch(r'[0-9]{4}\.(0[1-9]|1[0-2])\.(0|[1-9][0-9]*)', version):
            raise ValueError('Expected a calendar version')
        archive = delivery / f'EasyDiffraction-{version}-{platform}-online.zip'
        if (
            metadata['edi_commit'] != commit
            or metadata['kind'] != 'online'
            or metadata['zip'] != archive.name
            or metadata['repository_url']
            != f'https://enhantica.github.io/edi/repository/testing/{platform}/'
        ):
            raise ValueError(f'Installer identity differs for {platform}')
        if (
            receipt['passed'] is not True
            or receipt['smoke']['passed'] is not True
            or receipt['smoke']['app_version'] != version
            or receipt['smoke']['release_history_sha256'] != hashlib.sha256(payload).hexdigest()
        ):
            raise ValueError(f'Installer qualification differs for {platform}')
        with archive.open('rb') as stream:
            digest = hashlib.file_digest(stream, 'sha256').hexdigest()
        if metadata['zip_sha256'] != digest:
            raise ValueError(f'Installer checksum differs for {platform}')
        archives[platform] = (archive, digest)
    if set(archives) != expected:
        raise ValueError('A qualified platform is missing')
    recorded = json.loads(history)
    (release,) = recorded['releases']
    if (
        recorded['schema'] != 'edi.preview-releases/1'
        or recorded['sequence'] != 'calendar'
        or release['commit'] != commit
        or any(
            path.name != f'EasyDiffraction-{release["version"]}-{platform}-online.zip'
            for platform, (path, _) in archives.items()
        )
    ):
        raise ValueError('Release history differs from the qualified installers')
    return release, _preview_notes(release), list(archives.values())


def _preview_notes(release: dict) -> str:
    notes = []
    for group, entries in release['notes'].items():
        if entries:
            if notes:
                notes.append('')
            notes.extend([f'## {group}', ''])
            for entry in entries:
                if not note_interfaces(entry):
                    raise ValueError('Every preview release note needs an interface')
                notes.append(markdown_note(entry))
    return '\n'.join(notes) + '\n'


def publish(repo: str, release: dict, notes: str, archives: list[tuple[Path, str]]) -> None:
    """Create the draft and attach only assets missing from a matching release."""
    version = release['version']
    tag = 'v' + version
    title = 'edi ' + version
    command = ['gh', 'release']

    def read_release():
        pages = subprocess.check_output([
            'gh',
            'api',
            '--paginate',
            '--slurp',
            f'repos/{repo}/releases?per_page=100',
        ])
        matches = [item for page in json.loads(pages) for item in page if item['tag_name'] == tag]
        if len(matches) > 1:
            raise ValueError('Multiple releases use the same calendar tag')
        if matches:
            return optional_api(repo, f'releases/{matches[0]["id"]}')
        return None

    existing = read_release()
    if existing is None:
        if optional_api(repo, f'git/ref/tags/{tag}') is not None:
            raise ValueError('Release tag already exists')
        with tempfile.TemporaryDirectory() as temporary:
            notes_file = Path(temporary) / 'notes.md'
            notes_file.write_text(notes, encoding='utf-8')
            subprocess.run(
                [
                    *command,
                    'create',
                    tag,
                    '--repo',
                    repo,
                    '--draft',
                    '--prerelease',
                    '--latest=false',
                    '--target',
                    release['commit'],
                    '--title',
                    title,
                    '--notes-file',
                    str(notes_file),
                ],
                check=True,
            )
        existing = read_release()
    assets = {path.name: digest for path, digest in archives}

    def verified_assets(metadata):
        if metadata is None or not metadata['prerelease'] or metadata['name'] != title:
            raise ValueError('Expected the matching testing prerelease')
        return check_existing(metadata, release, notes, assets)

    found = verified_assets(existing)
    for path, _ in archives:
        if path.name not in found:
            subprocess.run([*command, 'upload', tag, str(path), '--repo', repo], check=True)
    verified = read_release()
    if verified_assets(verified) != set(assets):
        raise RuntimeError('Uploaded release assets could not be verified')
    print(verified['html_url'])


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--repo', required=True)
    parser.add_argument('--commit', required=True)
    parser.add_argument('--mac-linux-only', action='store_true')
    parser.add_argument('deliveries', nargs='+', type=Path)
    args = parser.parse_args()
    publish(
        args.repo,
        *prepare(
            args.repo,
            args.commit,
            args.deliveries,
            mac_linux_only=args.mac_linux_only,
        ),
    )
