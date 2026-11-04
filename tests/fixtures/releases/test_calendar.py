# SPDX-License-Identifier: BSD-3-Clause
"""Recorded release inputs, with no GitHub or installer network access."""

import datetime
import importlib.util
from pathlib import Path

import pytest

SPEC = importlib.util.spec_from_file_location(
    'release_plan', Path(__file__).resolve().parents[3] / 'tools/release/plan.py'
)
PLAN = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(PLAN)
HEAD = 'a' * 40


def request(**changes):
    return {
        'number': 3,
        'title': 'Refine backgrounds in full powder fits',
        'merged_at': '2026-11-04T12:00:00Z',
        'merge_commit_sha': HEAD,
        'labels': [{'name': '[scope] bug'}],
        **changes,
    }


def make_plan(releases=(), today=datetime.date(2026, 11, 5), requests=None):
    return PLAN.release_plan(
        [request()] if requests is None else requests, list(releases), HEAD, {HEAD}, today
    )


@pytest.mark.parametrize(
    ('versions', 'date', 'expected'),
    [
        ([], '2026-11-05', '2026.11.0'),
        (['2026.11.0', '2026.11.9'], '2026-11-05', '2026.11.10'),
        (['2026.11.10'], '2026-12-01', '2026.12.0'),
        (['2026.12.2'], '2027-01-01', '2027.01.0'),
    ],
)
def test_release_calendar(versions, date, expected):
    releases = [{'version': version, 'commit': 'b' * 40} for version in versions]
    assert make_plan(releases, datetime.date.fromisoformat(date))['version'] == expected


def test_retry_on_another_day_reuses_the_published_identity_and_notes():
    original = make_plan()
    assert make_plan([original], datetime.date(2026, 12, 1)) == original


def test_labels_group_notes_without_changing_the_version_rule():
    for label, group in PLAN.GROUPS.items():
        result = make_plan(requests=[request(labels=[label])])
        assert result['version'] == '2026.11.0'
        assert result['notes'][group][0]['title'] == request()['title']


@pytest.mark.parametrize(
    'changes',
    [{'merged_at': None}, {'merge_commit_sha': 'c' * 40}, {'labels': ['[bot] backmerge']}],
)
def test_unmerged_unincluded_and_bot_requests_are_not_release_changes(changes):
    with pytest.raises(ValueError, match='No user-facing merged changes'):
        make_plan(requests=[request(**changes)])


@pytest.mark.parametrize(
    'title', ['E11-T8 fixes', 'Fix I-0347', 'fix: better fitting', '', 'First\nSecond']
)
def test_internal_or_unusable_titles_must_be_rewritten_before_release(title):
    with pytest.raises(ValueError, match=r'title|line|outcome'):
        make_plan(requests=[request(title=title)])


def test_skipped_versions_are_all_included_in_whats_new():
    releases = [
        {'version': version}
        for version in ['2026.11.0', '2026.11.2', '2026.11.9', '2026.11.10', '2026.12.0']
    ]
    assert [
        release['version'] for release in PLAN.notes_since(releases, '2026.11.0', '2026.11.10')
    ] == ['2026.11.10', '2026.11.9', '2026.11.2']


def test_calendar_regression_and_duplicate_published_identity_fail_closed():
    with pytest.raises(ValueError, match='backwards'):
        make_plan([{'version': '2027.01.0', 'commit': 'b' * 40}])
    original = make_plan()
    with pytest.raises(ValueError, match='unique'):
        make_plan([original, original])
