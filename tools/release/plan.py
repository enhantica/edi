# SPDX-License-Identifier: BSD-3-Clause
"""Create a calendar release identity and user notes from recorded merged PRs."""

import argparse
import datetime
import json
import re
from operator import itemgetter
from pathlib import Path

INTERFACES = json.loads(
    (Path(__file__).resolve().parents[2] / 'data/release-interfaces.json').read_text(
        encoding='utf-8'
    )
)
INTERFACE_LABEL_PREFIX = '[interface] '

GROUPS = {
    '[scope] significant': 'Added',
    '[scope] enhancement': 'Added',
    '[scope] bug': 'Fixed',
    '[scope] maintenance': 'Changed',
    '[scope] documentation': 'Changed',
}


def version_key(version: str) -> tuple[int, int, int]:
    """Validate and compare calendar versions numerically, including two-digit sequences."""
    match = re.fullmatch(r'([0-9]{4})\.(0[1-9]|1[0-2])\.(0|[1-9][0-9]*)', version)
    if not match or int(match[1]) < 2000:
        raise ValueError(f'Invalid calendar release version: {version}')
    return tuple(map(int, match.groups()))


def check_title(title: str) -> str:
    """Require a public, user-oriented PR title before it becomes a release note."""
    if (
        not isinstance(title, str)
        or not title.strip()
        or title != title.strip()
        or '\n' in title
        or '\r' in title
    ):
        raise ValueError('Release titles must be one nonempty line')
    if re.search(r'\b(?:E|C)[0-9]+-T[0-9]+\b|\bI-[0-9]{4}\b', title):
        raise ValueError('Use a user-facing title without internal coordination identifiers')
    if re.match(r'(?i)(?:feat|fix|chore|refactor|docs|test|ci)(?:\([^)]*\))?!?:', title):
        raise ValueError('Describe the user outcome without a commit-type prefix')
    return title


def validate_history(history: dict) -> None:
    """Validate persisted release identities and note entries before building a distribution."""
    if (
        not isinstance(history, dict)
        or history.get('schema') != 'edi.releases/1'
        or not isinstance(history.get('releases'), list)
    ):
        raise ValueError('Unknown release-history schema')
    if not re.fullmatch(r'[0-9a-f]{40}', history.get('baseline_commit', '')):
        raise ValueError('Release history requires the complete baseline commit')
    versions, commits = set(), set()
    for release in history['releases']:
        version = version_key(release['version'])
        commit = release['commit']
        if not re.fullmatch(r'[0-9a-f]{40}', commit) or version in versions or commit in commits:
            raise ValueError('Release identities must be unique and source-bound')
        versions.add(version)
        commits.add(commit)
        try:
            date = datetime.date.fromisoformat(release['date'])
        except ValueError as error:
            raise ValueError('Release date is invalid') from error
        if date.isoformat() != release['date']:
            raise ValueError('Release dates must use ISO format')
        notes = release['notes']
        if (
            not isinstance(notes, dict)
            or set(notes) != {'Added', 'Fixed', 'Changed'}
            or not any(notes.values())
        ):
            raise ValueError('Release notes require the declared user-facing groups')
        for entries in notes.values():
            if not isinstance(entries, list):
                raise TypeError('Release-note groups must contain entries')
            for entry in entries:
                if (
                    len(check_title(entry['title'])) > 512
                    or type(entry['pull_request']) is not int
                    or entry['pull_request'] <= 0
                ):
                    raise ValueError(
                        'Release-note entries require a title and pull request number'
                    )
                note_interfaces(entry)


def note_interfaces(entry: dict) -> list[str]:
    """Read optional interface identifiers in a stable display order."""
    values = entry.get('interfaces', [])
    if (
        not isinstance(values, list)
        or any(not isinstance(value, str) or value not in INTERFACES for value in values)
        or len(set(values)) != len(values)
    ):
        raise ValueError('Release note interfaces must be unique known identifiers')
    return [key for key in INTERFACES if key in values]


def next_calendar_version(versions: list[str], today: datetime.date) -> str:
    known = [version_key(version) for version in versions]
    current = today.year, today.month
    if known and max(known)[:2] > current:
        raise ValueError('The release calendar cannot move backwards')
    sequence = max((key[2] for key in known if key[:2] == current), default=-1) + 1
    return f'{today.year:04d}.{today.month:02d}.{sequence}'


def release_plan(
    pull_requests: list[dict],
    releases: list[dict],
    commit: str,
    included_commits: set[str],
    today: datetime.date,
    *,
    reserved_versions: tuple[str, ...] = (),
) -> dict:
    """Choose a retry-stable identity and group only PRs included in this release."""
    if not re.fullmatch(r'[0-9a-f]{40}', commit):
        raise ValueError('A release requires the complete source commit')
    known = {}
    for release in releases:
        key = version_key(release['version'])
        if key in known:
            raise ValueError('Published release versions must be unique')
        known[key] = release
    repeated = [release for release in releases if release['commit'] == commit]
    if repeated:
        if len(repeated) != 1:
            raise ValueError('A source commit has conflicting published release identities')
        return repeated[0]
    version = next_calendar_version(
        [*[release['version'] for release in releases], *reserved_versions], today
    )
    notes = {group: [] for group in ['Added', 'Fixed', 'Changed']}
    seen = set()
    for request in sorted(pull_requests, key=itemgetter('number')):
        if not request.get('merged_at') or request.get('merge_commit_sha') not in included_commits:
            continue
        number = request['number']
        if type(number) is not int or number <= 0 or number in seen:
            raise ValueError('Merged pull request numbers must be positive and unique')
        seen.add(number)
        labels = {
            label['name'] if isinstance(label, dict) else label for label in request['labels']
        }
        if labels.intersection({'[bot] release', '[bot] backmerge'}):
            continue
        scopes = labels.intersection(GROUPS)
        if len(scopes) != 1:
            raise ValueError(f'Pull request {number} needs exactly one release scope label')
        entry = {'title': check_title(request['title']), 'pull_request': number}
        interfaces = note_interfaces({
            'interfaces': [
                label.removeprefix(INTERFACE_LABEL_PREFIX)
                for label in labels
                if label.startswith(INTERFACE_LABEL_PREFIX)
            ],
        })
        if not interfaces:
            raise ValueError(f'Pull request {number} needs at least one release interface label')
        entry['interfaces'] = interfaces
        notes[GROUPS[scopes.pop()]].append(entry)
    if not any(notes.values()):
        raise ValueError('No user-facing merged changes are included in this release')
    return {
        'version': version,
        'date': today.isoformat(),
        'commit': commit,
        'notes': notes,
    }


def notes_since(releases: list[dict], previous: str, current: str) -> list[dict]:
    """Return all skipped release notes between the last used and current release."""
    lower, upper = version_key(previous), version_key(current)
    if lower >= upper:
        return []
    return sorted(
        (release for release in releases if lower < version_key(release['version']) <= upper),
        key=lambda release: version_key(release['version']),
        reverse=True,
    )


def markdown_note(entry: dict) -> str:
    """Render interface names in GitHub Markdown and preserve the docs metadata."""
    title = entry['title']
    for character in ['\\', '`', '*', '_', '[', ']', '<', '>']:
        title = title.replace(character, '\\' + character)
    if 'pull_request' in entry:
        number = entry['pull_request']
        title += f' ([#{number}](https://github.com/enhantica/edi/pull/{number}))'
    interfaces = note_interfaces(entry)
    if interfaces:
        labels = ' '.join(f'`{INTERFACES[key][1]}`' for key in interfaces)
        title += f' {labels} <!-- interfaces: {",".join(interfaces)} -->'
    return '- ' + title


def markdown_notes(release: dict) -> str:
    """Render the same recorded titles for GitHub and application release history."""
    lines = [f'# EasyDiffraction {release["version"]}', '']
    for group, entries in release['notes'].items():
        if entries:
            lines.extend([f'## {group}', ''])
            lines.extend(map(markdown_note, entries))
            lines.append('')
    return '\n'.join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--pull-requests', type=Path, required=True)
    parser.add_argument('--history', type=Path, required=True)
    parser.add_argument('--commits', type=Path, required=True)
    parser.add_argument('--commit', required=True)
    parser.add_argument('--date', type=datetime.date.fromisoformat, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    history = json.loads(args.history.read_text(encoding='utf-8'))
    validate_history(history)
    release = release_plan(
        json.loads(args.pull_requests.read_text(encoding='utf-8')),
        history['releases'],
        args.commit,
        set(args.commits.read_text(encoding='utf-8').splitlines()),
        args.date,
    )
    args.output.mkdir(parents=True)
    (args.output / 'release.json').write_text(
        json.dumps(release, indent=2) + '\n', encoding='utf-8'
    )
    (args.output / 'notes.md').write_text(markdown_notes(release), encoding='utf-8')


if __name__ == '__main__':
    main()
