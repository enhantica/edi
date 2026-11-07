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
from operator import itemgetter
from pathlib import Path

from plan import (
    markdown_notes,
    next_calendar_version,
    release_body,
    release_date,
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


def reservation_only(draft: dict) -> bool:
    """Whether a draft is still only a reservation: no assets and a text that is only its date."""
    date = release_date(draft['body'])
    return (
        draft['draft']
        and not draft['assets']
        and date is not None
        and draft['body'] == release_body('', date)
    )


def settle_own_duplicates(repo: str, own: list[dict]) -> list[dict]:
    """Keep one of several drafts for this source and channel, deleting the reservation-only rest.

    Two allocators for the same source can both reserve before either sees the other, and a lost
    response can hide which one a retry made. The draft kept is the one already claimed by a
    publisher, else the earliest; the tag check after this decides whether it keeps its number.
    More than one claimed draft, or anything else, is ambiguous and refuses.
    """
    claimed = [draft for draft in own if not reservation_only(draft)]
    if len(claimed) > 1:
        raise ValueError('Several drafts claim this source')
    kept = claimed[0] if claimed else min(own, key=itemgetter('id'))
    for draft in own:
        if draft is not kept:
            subprocess.run(
                ['gh', 'api', '--method', 'DELETE', f'repos/{repo}/releases/{draft["id"]}'],
                check=True,
                capture_output=True,
            )
    return [kept]


def reserve_identity(
    repo: str, commit: str, today: datetime.date, *, prerelease: bool, attempts: int = 5
) -> tuple[str, datetime.date]:
    """The calendar version and date of this source in its channel, held by a draft.

    A new version is reserved at once by a draft whose text is only the release date, so other
    allocators skip the number while this source is built. A retry finds that draft for the same
    commit and channel and keeps its version and the date it records. Either way the draft must
    be the first release with its tag; otherwise it is withdrawn and the next number tried, which
    also settles a creation whose response was lost. A source already published in this channel
    is refused: a published release is never rebuilt under a new number.
    """
    for _ in range(attempts):
        own = [
            item
            for item in list_releases(repo)
            if item['target_commitish'] == commit
            and item['prerelease'] == prerelease
            and CALENDAR_TAG.fullmatch(item['tag_name'])
        ]
        published = [item['tag_name'] for item in own if not item['draft']]
        if published:
            raise ValueError(f'This source is already published as {published[0]}')
        if len(own) > 1:
            own = settle_own_duplicates(repo, own)
        if own:
            draft, recorded = own[0], release_date(own[0]['body'])
            if recorded is None:
                raise ValueError('The draft for this source records no release date')
            date = datetime.date.fromisoformat(recorded)
        else:
            date, version = today, next_calendar_version(calendar_tags(repo), today)
            payload = {
                'tag_name': 'v' + version,
                'target_commitish': commit,
                'name': 'edi ' + version,
                'body': release_body('', today.isoformat()),
                'draft': True,
                'prerelease': prerelease,
                'make_latest': 'false',
            }
            draft = json.loads(
                subprocess.check_output(
                    ['gh', 'api', '--method', 'POST', f'repos/{repo}/releases', '--input', '-'],
                    input=json.dumps(payload).encode(),
                )
            )
        rivals = [
            item['id'] for item in list_releases(repo) if item['tag_name'] == draft['tag_name']
        ]
        if min(rivals) == draft['id']:
            return draft['tag_name'][1:], date
        subprocess.run(
            ['gh', 'api', '--method', 'DELETE', f'repos/{repo}/releases/{draft["id"]}'],
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
