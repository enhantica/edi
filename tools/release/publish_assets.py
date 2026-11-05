# SPDX-License-Identifier: BSD-3-Clause
"""Publish the already qualified assets without overwriting a release identity."""

import argparse
import hashlib
import json
import subprocess
from pathlib import Path

from plan import markdown_notes, validate_history
from prepare import published_history


def optional_api(repo: str, path: str) -> dict | None:
    """Distinguish a missing release/tag from an authentication or service failure."""
    result = subprocess.run(
        ['gh', 'api', f'repos/{repo}/{path}'], capture_output=True, check=False
    )
    if result.returncode:
        if b'HTTP 404' in result.stderr:
            return None
        raise RuntimeError('Release publication metadata could not be read')
    return json.loads(result.stdout)


def check_progression(history: dict, previous: dict, release: dict) -> None:
    """Refuse stale plans while allowing a retry of the identical published release."""
    validate_history(history)
    validate_history(previous)
    prior = {**history, 'releases': [item for item in history['releases'] if item != release]}
    if previous not in (prior, history):
        raise ValueError('Published history moved; prepare and qualify a new release')
    if release not in history['releases']:
        raise ValueError('Release is missing from the qualified history')


def check_existing(
    existing: dict,
    release: dict,
    notes: str,
    assets: dict[str, str],
    *,
    replace_draft_assets: bool = False,
) -> set[str]:
    """Find matching assets and optionally allow replacements in a matching draft."""
    if existing['target_commitish'] != release['commit'] or existing['body'] != notes:
        raise ValueError('Release tag already names different source or notes')
    found = set()
    for asset in existing['assets']:
        name = asset['name']
        if name not in assets:
            raise ValueError('An existing release asset has a different identity')
        if asset.get('digest') == 'sha256:' + assets[name]:
            found.add(name)
        elif not (replace_draft_assets and existing['draft']):
            raise ValueError('An existing release asset has a different identity')
    if not existing['draft'] and found != set(assets):
        raise ValueError('Published releases cannot be repaired with unqualified assets')
    return found


def publish(repo: str, folder: Path, *, finalize: bool = False) -> None:
    """Create/reuse a matching draft, then finalize only after repository deployment."""
    release = json.loads((folder / 'release.json').read_text())
    history = json.loads((folder / 'assets/release-history.json').read_text())
    check_progression(history, published_history(repo), release)
    notes = (folder / 'notes.md').read_text()
    if notes != markdown_notes(release):
        raise ValueError('Release notes differ from the qualified titles')
    assets = {}
    for path in (folder / 'assets').iterdir():
        if not path.is_file() or path.is_symlink():
            raise ValueError('Release assets must be regular files')
        with path.open('rb') as stream:
            assets[path.name] = hashlib.file_digest(stream, 'sha256').hexdigest()
    tag = 'v' + release['version']
    existing = optional_api(repo, f'releases/tags/{tag}')
    if existing is None:
        if finalize:
            raise ValueError('Create and verify the draft before finalizing publication')
        if optional_api(repo, f'git/ref/tags/{tag}') is not None:
            raise ValueError('A tag already exists without its qualified release')
        subprocess.run(
            [
                'gh',
                'release',
                'create',
                tag,
                '--repo',
                repo,
                '--draft',
                '--target',
                release['commit'],
                '--title',
                'edi ' + release['version'],
                '--notes-file',
                str(folder / 'notes.md'),
            ],
            check=True,
        )
        existing = optional_api(repo, f'releases/tags/{tag}')
        if existing is None:
            raise RuntimeError('Created release could not be verified')
    found = check_existing(existing, release, notes, assets)
    if finalize:
        if found != set(assets):
            raise ValueError('All qualified assets must be uploaded before publication')
        subprocess.run(
            ['gh', 'release', 'edit', tag, '--repo', repo, '--draft=false', '--latest'], check=True
        )
    else:
        for name in sorted(set(assets) - found):
            subprocess.run(
                ['gh', 'release', 'upload', tag, str(folder / 'assets' / name), '--repo', repo],
                check=True,
            )
        verified = optional_api(repo, f'releases/tags/{tag}')
        if verified is None or check_existing(verified, release, notes, assets) != set(assets):
            raise RuntimeError('Uploaded release assets could not be verified')


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--repo', required=True)
    parser.add_argument('--folder', required=True, type=Path)
    parser.add_argument('--finalize', action='store_true')
    args = parser.parse_args()
    publish(args.repo, args.folder, finalize=args.finalize)


if __name__ == '__main__':
    main()
