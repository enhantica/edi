# SPDX-License-Identifier: BSD-3-Clause
"""The update feeds for apps of both version forms (edi ADR-0106).

Apps up to v2026.11.31 read ``releases/stable.json`` (``testing.json`` on the testing channel) and
show nothing at all when one entry's version is not YYYY.MM.N. Newer apps read ``stable-v2.json``
and ``testing-v2.json``, which hold the feed as it is. The old names hold a legacy feed: the old
releases as published, and the newest YY.N release once more as 2026.11.<31 + k>, k the YY.N
releases the feed holds, so the old apps offer it. The Maintenance Tool then updates them by
content checksum.

The checker follows the old apps' parser, ``release_changes`` as ``fetchNext`` calls it, read with
``git show v2026.11.31:app/src/desktop_updates.cpp``; the line numbers below are that file's. It
refuses a little more, in bytes the release tools never write: a byte-order mark, a repeated
key and a number out of range.

    python tools/release/legacy_feed.py check releases/stable.json
    python tools/release/legacy_feed.py write --history release-history.json --output releases
"""

import argparse
import datetime
import json
import re
import shutil
import sys
import unicodedata
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from versions import is_new, version_key

SCHEMA = 'edi.releases/1'
PREVIEW_SCHEMA = 'edi.preview-releases/1'
# The old parser's limits and patterns.
SIZE_LIMIT = 1024 * 1024  # line 87, and the read cap in lines 202-205
OLD_VERSION = re.compile(r'([0-9]{4})\.(0[1-9]|1[0-2])\.(0|[1-9][0-9]*)')  # line 30
COMMIT = re.compile(r'[0-9a-f]{40}')  # line 101
GROUPS = ('Added', 'Fixed', 'Changed')  # line 107
TITLE_LIMIT = 512  # line 116, in UTF-16 code units as QString counts them

# The last release of the old form: old apps see the k-th YY.N release as 2026.11.<31 + k>.
LAST_OLD = (2026, 11, 31)
BRIDGE = 'This update is EasyDiffraction {}: releases are now numbered by year (26.17, 27.1, ...)'


class RejectedError(ValueError):
    """A feed that apps up to v2026.11.31 drop whole, with the rule it breaks."""


def old_version(value: object) -> tuple[int, int, int] | None:
    """calendar_version (lines 29-41): YYYY.MM.N from the year 2000, each part a quint64."""
    match = OLD_VERSION.fullmatch(value) if isinstance(value, str) else None
    if match is None:
        return None
    parts = tuple(int(part) for part in match.groups())
    if parts[2] >= 2**64 or parts[0] < 2000:
        return None
    return parts


def _integer(value: object) -> int:
    """QJsonValue::toInteger: a whole number that fits in qint64, else 0."""
    if type(value) is int:
        return value if -(2**63) <= value < 2**63 else 0
    if type(value) is float and value.is_integer() and -(2.0**63) <= value < 2.0**63:
        return int(value)
    return 0


def _blank(text: str) -> bool:
    """Whether QString::trimmed leaves nothing: QChar::isSpace on every character."""
    return all(
        character in '\t\n\v\f\r \x85\xa0' or unicodedata.category(character) in {'Zs', 'Zl', 'Zp'}
        for character in text
    )


def _object(pairs: list[tuple[str, object]]) -> dict:
    if len({key for key, _ in pairs}) != len(pairs):
        raise ValueError('a key is repeated')
    return dict(pairs)


def _number(text: str) -> float:
    value = float(text)
    if value in {float('inf'), float('-inf')}:
        raise ValueError('a number is out of range')
    return value


def _constant(name: str) -> None:
    raise ValueError(f'{name} is not JSON')


def check(content: bytes, *, testing: bool = False) -> list[str]:
    """The versions an app up to v2026.11.31 lists from a feed, newest first.

    Raises RejectedError, naming the rule, for a feed that app drops whole. ``testing`` is a feed
    it reads as releases/testing.json, which may use the preview schema too (line 210). The app
    passes no current version (line 211), so every accepted release is listed.
    """
    if len(content) > SIZE_LIMIT:
        raise RejectedError(f'the feed is over {SIZE_LIMIT} bytes (line 87)')
    try:
        document = json.loads(
            content.decode('utf-8'),
            object_pairs_hook=_object,
            parse_float=_number,
            parse_constant=_constant,
        )
    except (UnicodeDecodeError, ValueError, RecursionError) as error:
        raise RejectedError(f'the feed is not one JSON document: {error} (line 88)') from error
    if not isinstance(document, dict):
        raise RejectedError('the feed is not a JSON object (line 89)')
    schema = document.get('schema')
    preview = testing and schema == PREVIEW_SCHEMA
    if not preview and schema != SCHEMA:
        raise RejectedError(f'the schema {schema!r} is not {SCHEMA} (lines 90-93)')
    if not isinstance(document.get('releases'), list):
        raise RejectedError('releases is not an array (line 93)')
    shown = {}
    for value in document['releases']:
        # toObject() of anything else is an empty object, which fails as one.
        release = value if isinstance(value, dict) else {}
        version = release.get('version')
        key = old_version(version)
        if key is None:
            raise RejectedError(f'the version {version!r} is not YYYY.MM.N (lines 98-99, 103)')
        if version in shown:
            raise RejectedError(f'{version} is listed twice (line 103)')
        _check_identity(version, release)
        _check_notes(version, release.get('notes'), preview=preview)
        shown[version] = key
    return sorted(shown, key=shown.__getitem__, reverse=True)


def _check_identity(version: str, release: dict) -> None:
    """The date and commit of one release (lines 100-104)."""
    day = release.get('date')
    if (
        not isinstance(day, str)
        or not re.fullmatch(r'[0-9]{4}-[0-9]{2}-[0-9]{2}', day)
        or not _iso_date(day)
    ):
        raise RejectedError(f'{version} has no ISO date (line 103)')
    commit = release.get('commit')
    if not isinstance(commit, str) or not COMMIT.fullmatch(commit):
        raise RejectedError(f'{version} has no full commit (line 104)')


def _check_notes(version: str, notes: object, *, preview: bool) -> None:
    """The notes of one release (lines 102-121); a preview needs no pull request numbers."""
    if not isinstance(notes, dict) or not notes:
        raise RejectedError(f'{version} has no notes (line 104)')
    listed = False
    for group in GROUPS:
        if not isinstance(notes.get(group), list):
            raise RejectedError(f'{version} has no {group} list (line 108)')
        for entry in notes[group]:
            item = entry if isinstance(entry, dict) else {}
            title = item.get('title') if isinstance(item.get('title'), str) else ''
            if (
                _blank(title)
                or len(title.encode('utf-16-le', 'surrogatepass')) // 2 > TITLE_LIMIT
                or '\n' in title
                or '\r' in title
            ):
                raise RejectedError(f'{version} has a title that is not one short line (line 116)')
            if not preview and _integer(item.get('pull_request')) <= 0:
                raise RejectedError(f'{version} has a note without its pull request (line 116)')
            listed = True
    if not listed:
        raise RejectedError(f'{version} has no note (line 121)')


def _iso_date(text: str) -> bool:
    """QDate::fromString(Qt::ISODate) is valid and gives the text back (line 103)."""
    try:
        return datetime.date.fromisoformat(text).isoformat() == text
    except ValueError:
        return False


def alias_version(count: int) -> str:
    """The version old apps see for the count-th YY.N release: 26.17, the first, is 2026.11.32."""
    year, month, last = LAST_OLD
    return f'{year}.{month}.{last + count}'


def alias(release: dict, count: int) -> dict:
    """A YY.N release as old apps can read it, its notes led by one line naming the release.

    The new line takes the release's first pull request number, which the stable schema needs.
    """
    notes = release['notes']
    numbers = [
        entry['pull_request']
        for group in GROUPS
        for entry in notes.get(group, [])
        if 'pull_request' in entry
    ]
    bridge = {'title': BRIDGE.format(release['version'])}
    if numbers:
        bridge['pull_request'] = numbers[0]
    return {
        'version': alias_version(count),
        'date': release['date'],
        'commit': release['commit'],
        'notes': {
            'Added': [bridge, *notes.get('Added', [])],
            'Fixed': list(notes.get('Fixed', [])),
            'Changed': list(notes.get('Changed', [])),
        },
    }


def _new(release: object) -> bool:
    version = release.get('version') if isinstance(release, dict) else None
    return isinstance(version, str) and is_new(version)


def has_new(feed: dict) -> bool:
    """Whether the feed holds a YY.N release, which old apps need the alias for."""
    return any(map(_new, feed['releases']))


def legacy(feed: dict) -> dict:
    """The feed for old apps: its YYYY.MM.N releases unchanged, its newest YY.N one as an alias.

    The alias takes the newest YY.N release's place; the other YY.N releases are left out, so
    every version is one old apps read. Other fields are kept.
    """
    new = [release for release in feed['releases'] if _new(release)]
    newest = max(new, key=lambda release: version_key(release['version']), default=None)
    releases = []
    for release in feed['releases']:
        if release is newest:
            releases.append(alias(release, len(new)))
        elif isinstance(release, dict) and old_version(release.get('version')) is not None:
            releases.append(release)
    return {**feed, 'releases': releases}


def serialize(feed: dict) -> bytes:
    return (json.dumps(feed, indent=2) + '\n').encode()


def publishable(feed: dict, *, testing: bool = False, original: bytes | None = None) -> bytes:
    """The legacy feed's bytes, refused unless old apps accept it and offer its newest release.

    ``original`` is the feed's own bytes, kept as they are when there is nothing to change.
    """
    old = legacy(feed)
    content = original if original is not None and old == feed else serialize(old)
    try:
        shown = check(content, testing=testing)
    except RejectedError as error:
        raise RejectedError(
            f'Apps up to v2026.11.31 would drop the legacy feed: {error}'
        ) from error
    if has_new(feed):
        expected = alias_version(sum(map(_new, feed['releases'])))
        if not shown or shown[0] != expected:
            raise RejectedError(f'Apps up to v2026.11.31 would not offer the alias {expected}')
    return content


def write_feeds(history: Path, folder: Path, channel: str = 'stable') -> None:
    """``<channel>-v2.json``, a copy of ``history``, and ``<channel>.json``, its legacy feed.

    The legacy feed is checked first, so nothing is written when old apps would drop it. The site
    the apps fetch the feeds from is built by enhantica/edi-download, which calls this at the
    release tag, so a change of its arguments needs a change there too.
    """
    original = history.read_bytes()
    content = publishable(
        json.loads(original.decode('utf-8')), testing=channel == 'testing', original=original
    )
    folder.mkdir(parents=True, exist_ok=True)
    shutil.copy2(history, folder / f'{channel}-v2.json')
    (folder / f'{channel}.json').write_bytes(content)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    commands = parser.add_subparsers(dest='command', required=True)
    checking = commands.add_parser('check', help='list what apps up to v2026.11.31 show')
    checking.add_argument('feed', type=Path)
    checking.add_argument('--testing', action='store_true', help='read as releases/testing.json')
    writing = commands.add_parser('write', help='write the current and the legacy feed')
    writing.add_argument('--history', type=Path, required=True)
    writing.add_argument('--output', type=Path, required=True)
    writing.add_argument('--channel', choices=('stable', 'testing'), default='stable')
    args = parser.parse_args()
    try:
        if args.command == 'check':
            shown = check(args.feed.read_bytes(), testing=args.testing)
        else:
            write_feeds(args.history, args.output, args.channel)
    except RejectedError as error:
        print(error, file=sys.stderr)
        return 1
    if args.command == 'check':
        print(f'{args.feed}: apps up to v2026.11.31 list {", ".join(shown) or "nothing"}')
    else:
        print(f'{args.output}: {args.channel}-v2.json and the checked {args.channel}.json')
    return 0


if __name__ == '__main__':
    sys.exit(main())
