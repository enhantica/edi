# SPDX-License-Identifier: BSD-3-Clause
"""Prepare reviewable release inputs.

The only change made on GitHub is the empty draft that reserves the calendar version; nothing
is tagged or published here.
"""

import argparse
import datetime
import json
import re
import subprocess
from pathlib import Path

from plan import (
    markdown_notes,
    next_calendar_version,
    release_plan,
    validate_history,
    version_key,
)

ROOT = Path(__file__).resolve().parents[2]


def git(*arguments: str) -> str:
    """Read source provenance from the checked-out repository."""
    return subprocess.check_output(['git', *arguments], cwd=ROOT, text=True).strip()


def published_history(repo: str) -> dict:
    """Read the latest published history, failing closed except for a first release."""
    result = subprocess.run(
        ['gh', 'api', f'repos/{repo}/releases/latest'], capture_output=True, check=False
    )
    if result.returncode:
        if b'HTTP 404' in result.stderr:
            return json.loads((ROOT / 'data/releases.json').read_text(encoding='utf-8'))
        raise RuntimeError('Published release metadata could not be read')
    release = json.loads(result.stdout)
    assets = [asset for asset in release['assets'] if asset['name'] == 'release-history.json']
    if len(assets) != 1:
        raise RuntimeError('The latest release must have one versioned history asset')
    content = subprocess.check_output([
        'gh',
        'api',
        f'repos/{repo}/releases/assets/{assets[0]["id"]}',
        '-H',
        'Accept: application/octet-stream',
    ])
    if len(content) > 1024 * 1024:
        raise RuntimeError('Published release history exceeds the application limit')
    return json.loads(content)


def merged_requests(repo: str) -> list[dict]:
    """Read only the PR fields used for notes and source-membership checks."""
    content = subprocess.check_output([
        'gh',
        'api',
        '--paginate',
        f'repos/{repo}/pulls?state=closed&per_page=100',
        '--jq',
        '.[] | {number,title,merged_at,merge_commit_sha,labels:[.labels[].name]}',
    ])
    return [json.loads(line) for line in content.splitlines()]


def calendar_tags(repo: str) -> list[str]:
    content = subprocess.check_output([
        'gh',
        'api',
        '--paginate',
        '--slurp',
        f'repos/{repo}/git/matching-refs/tags/v',
    ])
    tags = [
        item['ref'].removeprefix('refs/tags/v') for page in json.loads(content) for item in page
    ]
    releases = subprocess.check_output([
        'gh',
        'api',
        '--paginate',
        '--slurp',
        f'repos/{repo}/releases?per_page=100',
    ])
    tags.extend(
        item['tag_name'].removeprefix('v')
        for page in json.loads(releases)
        for item in page
        if item['draft'] and item['tag_name'].startswith('v')
    )
    return [
        tag for tag in tags if re.fullmatch(r'[0-9]{4}\.(0[1-9]|1[0-2])\.(0|[1-9][0-9]*)', tag)
    ]


CALENDAR_TAG = re.compile(r'v[0-9]{4}\.(0[1-9]|1[0-2])\.(0|[1-9][0-9]*)')


def list_releases(repo: str) -> list[dict]:
    """Every release the token can see, drafts included."""
    content = subprocess.check_output([
        'gh',
        'api',
        '--paginate',
        '--slurp',
        f'repos/{repo}/releases?per_page=100',
    ])
    return [item for page in json.loads(content) for item in page]


def reserve_identity(
    repo: str, commit: str, today: datetime.date, *, prerelease: bool, attempts: int = 5
) -> tuple[str, datetime.date]:
    """The calendar version and date of this source in its channel, held by an empty draft.

    A retry finds the draft already made for the same commit and channel and keeps its version
    and date. A new version is reserved at once by creating an empty draft, so other allocators
    skip it while this source is built; if two take the same number at the same moment, the
    later draft is withdrawn and the next number tried.
    """
    for _ in range(attempts):
        own = [
            item
            for item in list_releases(repo)
            if item['draft']
            and item['target_commitish'] == commit
            and item['prerelease'] == prerelease
            and CALENDAR_TAG.fullmatch(item['tag_name'])
        ]
        if len(own) > 1:
            raise ValueError('Several drafts claim this source')
        if own:
            return own[0]['tag_name'][1:], datetime.date.fromisoformat(own[0]['created_at'][:10])
        version = next_calendar_version(calendar_tags(repo), today)
        payload = {
            'tag_name': 'v' + version,
            'target_commitish': commit,
            'name': 'edi ' + version,
            'body': '',
            'draft': True,
            'prerelease': prerelease,
            'make_latest': 'false',
        }
        created = json.loads(
            subprocess.check_output(
                ['gh', 'api', '--method', 'POST', f'repos/{repo}/releases', '--input', '-'],
                input=json.dumps(payload).encode(),
            )
        )
        rivals = [item['id'] for item in list_releases(repo) if item['tag_name'] == 'v' + version]
        if min(rivals) == created['id']:
            return version, datetime.date.fromisoformat(created['created_at'][:10])
        subprocess.run(
            ['gh', 'api', '--method', 'DELETE', f'repos/{repo}/releases/{created["id"]}'],
            check=True,
            capture_output=True,
        )
    raise RuntimeError('No calendar version could be reserved')


def prepare(repo: str, source: str, output: Path, today: datetime.date) -> dict:
    """Choose one identity from published history and the exact included source commits."""
    if not re.fullmatch(r'[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+', repo):
        raise ValueError('Expected a GitHub owner/repository identity')
    history = published_history(repo)
    validate_history(history)
    commit = git('rev-parse', '--verify', '--end-of-options', source + '^{commit}')
    releases = history['releases']
    baseline = (
        max(releases, key=lambda item: version_key(item['version']))['commit']
        if releases
        else history['baseline_commit']
    )
    if not re.fullmatch(r'[0-9a-f]{40}', baseline):
        raise ValueError('Release history requires the complete baseline commit')
    subprocess.run(['git', 'merge-base', '--is-ancestor', baseline, commit], cwd=ROOT, check=True)
    included = set(git('rev-list', baseline + '..' + commit).splitlines())
    published = any(item['commit'] == commit for item in releases)
    release = release_plan(
        merged_requests(repo),
        releases,
        commit,
        included,
        today,
        identity=None if published else reserve_identity(repo, commit, today, prerelease=False),
    )
    reused = any(item['version'] == release['version'] for item in releases)
    if not reused:
        history = {**history, 'releases': [*releases, release]}
    payload = json.dumps(history, indent=2) + '\n'
    if len(payload.encode('utf-8')) > 1024 * 1024:
        raise ValueError('Release history exceeds the application limit')
    output.mkdir(parents=True)
    for name, value in [
        ('release.json', release),
        ('release-history.json', history),
        ('plan.json', {'version': release['version'], 'commit': commit, 'reused': reused}),
    ]:
        (output / name).write_text(json.dumps(value, indent=2) + '\n', encoding='utf-8')
    (output / 'notes.md').write_text(markdown_notes(release), encoding='utf-8')
    return {'release': release, 'reused': reused}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--repo', required=True)
    parser.add_argument('--source', default='HEAD')
    parser.add_argument(
        '--date',
        type=datetime.date.fromisoformat,
        default=datetime.datetime.now(datetime.UTC).date(),
    )
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    result = prepare(args.repo, args.source, args.output, args.date)
    print(json.dumps({'version': result['release']['version'], 'reused': result['reused']}))


if __name__ == '__main__':
    main()
