# SPDX-License-Identifier: BSD-3-Clause
"""Recorded release inputs, with no GitHub or installer network access."""

import datetime
import importlib.util
import subprocess
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
        'labels': [{'name': '[scope] bug'}, {'name': '[interface] desktop'}],
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
        result = make_plan(requests=[request(labels=[label, '[interface] desktop'])])
        assert result['version'] == '2026.11.0'
        assert result['notes'][group][0]['title'] == request()['title']


@pytest.mark.parametrize(
    'changes',
    [{'merged_at': None}, {'merge_commit_sha': 'c' * 40}, {'labels': ['[bot] backmerge']}],
)
def test_unmerged_unincluded_and_bot_requests_are_not_release_changes(changes):
    with pytest.raises(ValueError, match='No user-facing merged changes'):
        make_plan(requests=[request(**changes)])


@pytest.mark.parametrize('title', ['fix: refine backgrounds', '', 'First\nSecond'])
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


@pytest.mark.parametrize('version', ['2026.11.0', '2026.11.10', '2027.01.0'])
def test_cmake_embeds_the_selected_calendar_identity(tmp_path, version):
    output = tmp_path / 'version.cpp'
    subprocess.run(
        [
            'cmake',
            f'-DSOURCE_DIR={tmp_path}',
            f'-DOUT={output}',
            f'-DRELEASE_VERSION={version}',
            '-P',
            str(Path(__file__).resolve().parents[3] / 'cmake/build_version.cmake'),
        ],
        check=True,
    )
    assert 'return "' + version + '";' in output.read_text()


@pytest.mark.parametrize(
    'version', ['2026.13.0', '2026.1.0', '2026.11.01', '0000.11.0', 'bad"version']
)
def test_invalid_release_identity_cannot_generate_cpp(tmp_path, version):
    output = tmp_path / 'version.cpp'
    result = subprocess.run(
        [
            'cmake',
            f'-DSOURCE_DIR={tmp_path}',
            f'-DOUT={output}',
            f'-DRELEASE_VERSION={version}',
            '-P',
            str(Path(__file__).resolve().parents[3] / 'cmake/build_version.cmake'),
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode != 0
    assert not output.exists()


def test_persisted_history_validates_note_groups_dates_and_identities():
    release = make_plan()
    history = {'schema': 'edi.releases/1', 'baseline_commit': 'b' * 40, 'releases': [release]}
    PLAN.validate_history(history)
    for changed in [
        {**release, 'date': '2026-02-31'},
        {**release, 'commit': 'unknown'},
        {**release, 'notes': {'Fixed': []}},
    ]:
        with pytest.raises(ValueError, match=r'date|format|identities|groups'):
            PLAN.validate_history({**history, 'releases': [changed]})
