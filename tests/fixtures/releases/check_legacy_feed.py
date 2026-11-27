# SPDX-License-Identifier: BSD-3-Clause
"""The update feed apps up to v2026.11.31 read, and the checker of their parser (edi ADR-0106)."""

import copy
import importlib.util
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'tools/release'))
SPEC = importlib.util.spec_from_file_location('legacy_feed', ROOT / 'tools/release/legacy_feed.py')
FEED = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(FEED)

# The history v2026.11.31 published, as its release-history.json asset holds it.
PUBLISHED = Path(__file__).with_name('release-history-v2026.11.31.json')
OLD_VERSIONS = [
    '2026.11.31',
    '2026.11.30',
    '2026.11.29',
    '2026.11.28',
    '2026.11.27',
    '2026.11.24',
    '2026.11.22',
    '2026.11.20',
    *(f'2026.11.{n}' for n in range(14, 7, -1)),
    '2026.11.0',
]
BRIDGE = 'This update is EasyDiffraction {}: releases are now numbered by year (26.17, 27.1, ...)'


def release(version, commit, *numbers, preview=False):
    """A release as plan.py records it, one Added note then Fixed ones, numbered as given."""

    def note(number):
        entry = {'title': f'Change number {number}', 'interfaces': ['desktop', 'web']}
        if not preview:
            entry['pull_request'] = number
        return entry

    return {
        'version': version,
        'date': '2026-11-27',
        'commit': commit * 40,
        'notes': {
            'Added': [note(numbers[0])],
            'Fixed': [note(number) for number in numbers[1:]],
            'Changed': [],
        },
    }


def history(*releases):
    published = json.loads(PUBLISHED.read_text(encoding='utf-8'))
    return {**published, 'releases': [*published['releases'], *releases]}


def content(feed):
    return (json.dumps(feed, indent=2) + '\n').encode()


def test_the_published_history_is_what_the_old_apps_list():
    assert FEED.check(PUBLISHED.read_bytes()) == OLD_VERSIONS


def test_one_yy_n_release_makes_the_old_apps_drop_the_whole_feed():
    with pytest.raises(FEED.RejectedError, match=r"'26\.17' is not YYYY\.MM\.N"):
        FEED.check(content(history(release('26.17', 'a', 181, 185))))


def test_the_legacy_feed_offers_26_17_as_2026_11_32():
    first = release('26.17', 'a', 181, 185)
    old = FEED.legacy(history(first))
    assert FEED.check(content(old)) == ['2026.11.32', *OLD_VERSIONS]
    published = json.loads(PUBLISHED.read_text(encoding='utf-8'))
    assert old['releases'][:-1] == published['releases']
    assert {key: old[key] for key in ('schema', 'baseline_commit')} == {
        'schema': 'edi.releases/1',
        'baseline_commit': published['baseline_commit'],
    }
    alias = old['releases'][-1]
    assert alias['version'] == '2026.11.32'
    assert (alias['date'], alias['commit']) == (first['date'], first['commit'])
    assert alias['notes'] == {
        'Added': [
            {'title': BRIDGE.format('26.17'), 'pull_request': 181},
            *first['notes']['Added'],
        ],
        'Fixed': first['notes']['Fixed'],
        'Changed': [],
    }


def test_only_the_newest_yy_n_release_reaches_the_old_apps():
    feed = history(
        release('26.17', 'a', 181), release('26.18', 'b', 190, 191), release('27.1', 'c', 200)
    )
    old = FEED.legacy(feed)
    assert FEED.check(content(old)) == ['2026.11.34', *OLD_VERSIONS]
    assert [item['version'] for item in old['releases']][-1] == '2026.11.34'
    assert old['releases'][-1]['notes']['Added'][0] == {
        'title': BRIDGE.format('27.1'),
        'pull_request': 200,
    }
    assert not any(FEED.is_new(item['version']) for item in old['releases'])


@pytest.mark.parametrize(('count', 'version'), [(1, '2026.11.32'), (2, '2026.11.33')])
def test_the_alias_counts_the_yy_n_releases(count, version):
    assert FEED.alias_version(count) == version


def test_the_tools_write_the_full_feed_and_the_checked_legacy_feed(tmp_path):
    source = tmp_path / 'release-history.json'
    source.write_text(json.dumps(history(release('26.17', 'a', 181)), indent=2))
    FEED.write_feeds(source, tmp_path / 'releases')
    assert (tmp_path / 'releases/stable-v2.json').read_bytes() == source.read_bytes()
    legacy = (tmp_path / 'releases/stable.json').read_bytes()
    assert FEED.check(legacy)[0] == '2026.11.32'
    assert legacy == content(FEED.legacy(history(release('26.17', 'a', 181))))


def test_a_legacy_feed_the_old_apps_would_drop_is_not_written(tmp_path):
    # 300 characters, 600 UTF-16 code units: QString counts the latter against its 512.
    long = release('26.17', 'a', 181)
    long['notes']['Fixed'] = [{'title': '\U0001f9ea' * 300, 'pull_request': 182}]
    source = tmp_path / 'release-history.json'
    source.write_text(json.dumps(history(long)))
    with pytest.raises(FEED.RejectedError, match='not one short line'):
        FEED.write_feeds(source, tmp_path / 'releases')
    assert not (tmp_path / 'releases').exists()


def test_a_preview_feed_keeps_its_schema_and_needs_no_pull_requests():
    old_preview = release('2026.11.30', 'd', 1, preview=True)
    feed = {
        'schema': 'edi.preview-releases/1',
        'sequence': 'calendar',
        'releases': [release('26.18', 'e', 1, preview=True), old_preview],
    }
    old = FEED.legacy(feed)
    assert old['schema'] == 'edi.preview-releases/1'
    assert old['sequence'] == 'calendar'
    assert old['releases'][1] == old_preview
    assert old['releases'][0]['notes']['Added'][0] == {'title': BRIDGE.format('26.18')}
    assert FEED.check(content(old), testing=True) == ['2026.11.32', '2026.11.30']
    with pytest.raises(FEED.RejectedError, match='schema'):
        FEED.check(content(old))
    assert FEED.publishable(feed, testing=True) == content(old)


def valid():
    return {'schema': 'edi.releases/1', 'releases': [release('2026.11.31', 'a', 5)]}


def changed(path, value):
    """The valid feed with one field changed; path is a list of keys and indices."""
    feed = copy.deepcopy(valid())
    target = feed
    for key in path[:-1]:
        target = target[key]
    target[path[-1]] = value
    return feed


TITLE = ['releases', 0, 'notes', 'Added', 0, 'title']
NUMBER = ['releases', 0, 'notes', 'Added', 0, 'pull_request']


@pytest.mark.parametrize(
    ('feed', 'rule'),
    [
        ([], 'not a JSON object'),
        (changed(['schema'], 'edi.preview-releases/1'), 'schema'),
        (changed(['releases'], {}), 'not an array'),
        (changed(['releases', 0], 'release'), 'not YYYY.MM.N'),
        (changed(['releases', 0, 'version'], '26.17'), 'not YYYY.MM.N'),
        (changed(['releases', 0, 'version'], '2026.13.0'), 'not YYYY.MM.N'),
        (changed(['releases', 0, 'version'], '2026.11.01'), 'not YYYY.MM.N'),
        (changed(['releases', 0, 'version'], '1999.12.0'), 'not YYYY.MM.N'),
        (changed(['releases', 0, 'version'], f'2026.11.{2**64}'), 'not YYYY.MM.N'),
        (changed(['releases', 0, 'date'], '2026-02-30'), 'ISO date'),
        (changed(['releases', 0, 'date'], '2026-11-27T00:00'), 'ISO date'),
        (changed(['releases', 0, 'date'], '0000-01-01'), 'ISO date'),
        (changed(['releases', 0, 'commit'], 'A' * 40), 'full commit'),
        (changed(['releases', 0, 'notes'], {}), 'no notes'),
        (changed(['releases', 0, 'notes', 'Changed'], None), 'no Changed list'),
        (changed(['releases', 0, 'notes', 'Added'], []), 'no note'),
        (changed(['releases', 0, 'notes', 'Added', 0], 'note'), 'one short line'),
        (changed(TITLE, ' \t　'), 'one short line'),
        (changed(TITLE, 'two\nlines'), 'one short line'),
        (changed(TITLE, 'a\r'), 'one short line'),
        (changed(TITLE, 'x' * 513), 'one short line'),
        (changed(NUMBER, 0), 'pull request'),
        (changed(NUMBER, '5'), 'pull request'),
        (changed(NUMBER, True), 'pull request'),
        (changed(NUMBER, 5.5), 'pull request'),
        (changed(NUMBER, 2**63), 'pull request'),
    ],
)
def test_the_checker_refuses_what_the_old_parser_refuses(feed, rule):
    with pytest.raises(FEED.RejectedError, match=rule):
        FEED.check(content(feed))


@pytest.mark.parametrize(
    'feed',
    [
        valid(),
        changed(TITLE, 'x' * 512),
        changed(TITLE, 'é' * 512),
        changed(NUMBER, 5.0),
        changed(NUMBER, 2**63 - 1),
        changed(['releases', 0, 'extra'], 'ignored'),
        changed(['releases', 0, 'notes', 'Other'], 'ignored'),
    ],
)
def test_the_checker_takes_what_the_old_parser_takes(feed):
    assert FEED.check(content(feed)) == ['2026.11.31']


def test_the_checker_follows_the_feed_limits():
    assert FEED.check(content({'schema': 'edi.releases/1', 'releases': []})) == []
    twice = valid()
    twice['releases'] *= 2
    with pytest.raises(FEED.RejectedError, match='listed twice'):
        FEED.check(content(twice))
    padded = content(valid())[:-1] + b' ' * (FEED.SIZE_LIMIT - len(content(valid())) + 1)
    assert len(padded) == FEED.SIZE_LIMIT
    assert FEED.check(padded) == ['2026.11.31']
    with pytest.raises(FEED.RejectedError, match='over'):
        FEED.check(padded + b' ')
    with pytest.raises(FEED.RejectedError, match='not one JSON document'):
        FEED.check(b'{"schema": "edi.releases/1", "releases": [], "releases": []}')
    with pytest.raises(FEED.RejectedError, match='not one JSON document'):
        FEED.check(b'\xff')


def test_a_preview_needs_the_testing_feed_and_no_pull_request():
    preview = changed(['schema'], 'edi.preview-releases/1')
    del preview['releases'][0]['notes']['Added'][0]['pull_request']
    assert FEED.check(content(preview), testing=True) == ['2026.11.31']
    stable = changed(['schema'], 'edi.releases/1')
    stable['releases'][0]['notes']['Added'][0]['pull_request'] = 0
    with pytest.raises(FEED.RejectedError, match='pull request'):
        FEED.check(content(stable), testing=True)
