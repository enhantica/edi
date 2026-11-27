# SPDX-License-Identifier: BSD-3-Clause
"""Create a release identity and user notes from recorded merged PRs."""

import argparse
import datetime
import json
import re
import sys
from operator import itemgetter
from pathlib import Path

# The version rules live in versions.py, which the installer and site tools import too; the
# release tools take them from here.
sys.path.insert(0, str(Path(__file__).resolve().parent))
from versions import (
    PATTERN,  # noqa: F401
    installer_stem,  # noqa: F401
    is_version,  # noqa: F401
    next_version,
    release_title,  # noqa: F401
    version_key,
)

INTERFACES = json.loads(
    (Path(__file__).resolve().parents[2] / 'data/release-interfaces.json').read_text(
        encoding='utf-8'
    )
)

# Every label of ADR-0101, as GitHub stores it, with its group and the colour that marks the group.
# A name is compared whole, so some emoji keep their variation selector (U+FE0F).
LABELS = {
    '🐞 bug': ('scope', 'd73a4a'),
    '✨ enhancement': ('scope', 'd73a4a'),
    '📘 documentation': ('scope', 'd73a4a'),
    '🧹 maintenance': ('scope', 'd73a4a'),
    '💥 significant': ('scope', 'd73a4a'),
    '⚠️ scope needed': ('scope', 'd73a4a'),
    '🔥 highest': ('priority', 'fbca04'),
    '🔴 high': ('priority', 'fbca04'),
    '🟠 medium': ('priority', 'fbca04'),
    '🟡 low': ('priority', 'fbca04'),
    '⚪ lowest': ('priority', 'fbca04'),
    '⚠️ priority needed': ('priority', 'fbca04'),
    '🌍 all': ('interface', '0079b7'),
    '🪟 app': ('interface', '0079b7'),
    '🖥️ desktop': ('interface', '0079b7'),
    '🌐 web': ('interface', '0079b7'),
    '🐍 py': ('interface', '0079b7'),
    '⌨️ cli': ('interface', '0079b7'),
    '📦 cli-py': ('interface', '0079b7'),
    '🙋 user': ('source', 'c5def5'),
    '🔧 maintainer': ('source', 'c5def5'),
    '🤖 agent': ('source', 'c5def5'),
    '🌙 nightly': ('source', 'c5def5'),
    '👯 duplicate': ('maintainer', '0e8a16'),
    '🚫 invalid': ('maintainer', '0e8a16'),
    '❓ question': ('maintainer', '0e8a16'),
    '🙅 wontfix': ('maintainer', '0e8a16'),
    '🤔 needs owner decision': ('status', '9333EA'),
    '🚧 in progress': ('status', '9333EA'),
    '🚀 release': ('bot', '5319e7'),
}

# The section of the notes a scope stands for, and the interfaces an interface label stands for.
# "app" and "all" are short for several: a note names each interface, so a site built from an older
# commit can still show it. The emoji belong to the GitHub labels only, not to the notes.
GROUPS = {
    '💥 significant': 'Added',
    '✨ enhancement': 'Added',
    '🐞 bug': 'Fixed',
    '🧹 maintenance': 'Changed',
    '📘 documentation': 'Changed',
}
INTERFACE_LABELS = {
    '🌍 all': tuple(INTERFACES),
    '🪟 app': ('desktop', 'web'),
    '🖥️ desktop': ('desktop',),
    '🌐 web': ('web',),
    '🐍 py': ('python',),
    '⌨️ cli': ('cli-standalone',),
    '📦 cli-py': ('cli-python',),
}

# edi has no develop branch, so its only bot pull request is the release one (ADR-0101).
BOT_LABELS = frozenset(name for name, (group, _) in LABELS.items() if group == 'bot')

# The names the labels had before. GitHub renames a label on every pull request that has it, merged
# ones too, so an old name comes only from before the rename: the labels themselves, or a re-run of
# a check, which repeats the labels it started with. GitHub allows re-runs for 30 days, so this
# table can go 30 days after the labels are renamed.
OLD_NAMES = {
    '[scope] bug': '🐞 bug',
    '[scope] enhancement': '✨ enhancement',
    '[scope] documentation': '📘 documentation',
    '[scope] maintenance': '🧹 maintenance',
    '[scope] significant': '💥 significant',
    '[scope] ⚠️ label needed': '⚠️ scope needed',
    '[priority] highest': '🔥 highest',
    '[priority] high': '🔴 high',
    '[priority] medium': '🟠 medium',
    '[priority] low': '🟡 low',
    '[priority] lowest': '⚪ lowest',
    '[priority] ⚠️ label needed': '⚠️ priority needed',
    '[interface] desktop': '🖥️ desktop',
    '[interface] web': '🌐 web',
    '[interface] py': '🐍 py',
    '[interface] cli': '⌨️ cli',
    '[interface] cli-py': '📦 cli-py',
    '[source] user': '🙋 user',
    '[source] maintainer': '🔧 maintainer',
    '[source] agent': '🤖 agent',
    '[source] 🌙 nightly': '🌙 nightly',
    '[maintainer] duplicate': '👯 duplicate',
    '[maintainer] invalid': '🚫 invalid',
    '[maintainer] question': '❓ question',
    '[maintainer] wontfix': '🙅 wontfix',
    '[status] needs owner decision': '🤔 needs owner decision',
    '[status] 🚧 in progress': '🚧 in progress',
    '[bot] release': '🚀 release',
}


def current_names(labels: set[str]) -> set[str]:
    """The labels under their present names, so a name from before the rename still counts."""
    return {OLD_NAMES.get(label, label) for label in labels}


def label_problem(labels: set[str]) -> str | None:
    """Why a pull request's labels cannot make its release note, or None when they can.

    One rule for the release notes and the pull-request label check: a bot release has that label
    alone, so a change in the notes cannot hide behind it; any other pull request needs one scope
    label and an interface label, and no label that is not listed, so a misspelt interface is not
    lost from the note.
    """
    labels = current_names(labels)
    if labels & BOT_LABELS:
        if labels <= BOT_LABELS:
            return None
        others = ', '.join(f'`{name}`' for name in sorted(labels - BOT_LABELS))
        return f'has a release label beside others ({others})'
    if len(labels & GROUPS.keys()) != 1:
        return 'needs exactly one release scope label'
    if not labels & INTERFACE_LABELS.keys():
        return 'needs at least one release interface label'
    if labels - LABELS.keys():
        names = ', '.join(f'`{name}`' for name in sorted(labels - LABELS.keys()))
        return f'has an unknown label ({names})'
    return None


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
    """The next YY.N for today (versions.py); the name stays for the tools that call it."""
    return next_version(versions, today)


def _new_identity(
    known: dict, reserved: tuple[str, ...], today: datetime.date, identity
) -> tuple[str, datetime.date]:
    """The given reserved identity, else the next free version for today."""
    if identity is None:
        published = [release['version'] for release in known.values()]
        return next_calendar_version([*published, *reserved], today), today
    if version_key(identity[0]) in known:
        raise ValueError('The reserved version is already published for another source')
    return identity


RELEASE_DATE = re.compile(r'<!-- edi release date ([0-9]{4}-[0-9]{2}-[0-9]{2}) -->')


def release_body(notes: str, date: str) -> str:
    """A GitHub release's text: its notes, then the release date kept as a hidden comment.

    The date is chosen when the version is reserved and must survive into publication, and no
    GitHub field records it (``created_at`` is the source commit's date).
    """
    return (
        f'{notes}\n<!-- edi release date {date} -->\n'
        if notes
        else f'<!-- edi release date {date} -->\n'
    )


def release_date(body: str | None) -> str | None:
    """The release date a release body records, if any."""
    match = RELEASE_DATE.search(body or '')
    return match[1] if match else None


def release_plan(
    pull_requests: list[dict],
    releases: list[dict],
    commit: str,
    included_commits: set[str],
    today: datetime.date,
    *,
    reserved_versions: tuple[str, ...] = (),
    identity: tuple[str, datetime.date] | None = None,
) -> dict:
    """Choose a retry-stable identity and group only PRs included in this release.

    ``identity`` is a version and date already reserved for this commit; it is used as given.
    """
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
    version, today = _new_identity(known, reserved_versions, today, identity)
    notes = {group: [] for group in ['Added', 'Fixed', 'Changed']}
    seen = set()
    for request in sorted(pull_requests, key=itemgetter('number')):
        if not request.get('merged_at') or request.get('merge_commit_sha') not in included_commits:
            continue
        number = request['number']
        if type(number) is not int or number <= 0 or number in seen:
            raise ValueError('Merged pull request numbers must be positive and unique')
        seen.add(number)
        labels = current_names({
            label['name'] if isinstance(label, dict) else label for label in request['labels']
        })
        problem = label_problem(labels)
        if problem:
            raise ValueError(f'Pull request {number} {problem}')
        if labels & BOT_LABELS:
            continue
        entry = {'title': check_title(request['title']), 'pull_request': number}
        interfaces = note_interfaces({
            'interfaces': list({
                interface
                for label in labels & INTERFACE_LABELS.keys()
                for interface in INTERFACE_LABELS[label]
            }),
        })
        entry['interfaces'] = interfaces
        (scope,) = labels & GROUPS.keys()
        notes[GROUPS[scope]].append(entry)
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
        labels = ' '.join(f'`{INTERFACES[key][2]}`' for key in interfaces)
        title += f' {labels} <!-- interfaces: {",".join(interfaces)} -->'
    return '- ' + title


def markdown_notes(release: dict) -> str:
    """Render the same recorded titles for GitHub and application release history.

    The release title already names the version, so the notes start at the first section.
    """
    lines = []
    for group, entries in release['notes'].items():
        if entries:
            lines.extend([f'## {group}', ''])
            lines.extend(map(markdown_note, entries))
            lines.append('')
    return '\n'.join(lines)


def check_labels(names: list[str]) -> int:
    """The pull-request label check: print the problem and return 1, or return 0."""
    problem = label_problem(set(names))
    if problem:
        scopes = ', '.join(f'`{name}`' for name in GROUPS)
        interfaces = ', '.join(f'`{name}`' for name in INTERFACE_LABELS)
        print(
            f'This pull request {problem}: one of {scopes}, and one or more of {interfaces} '
            f'(or {", ".join(f"`{name}`" for name in sorted(BOT_LABELS))}).'
        )
        return 1
    print('Release labels: ' + ', '.join(sorted(names)))
    return 0


def main() -> None:
    if sys.argv[1:2] == ['--check-labels']:
        raise SystemExit(check_labels(json.loads(sys.argv[2])))
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
