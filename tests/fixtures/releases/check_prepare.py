# SPDX-License-Identifier: BSD-3-Clause
"""Use real local git ancestry and recorded GitHub responses for release preparation."""

import datetime
import importlib.util
import io
import json
import subprocess
import sys
import zipfile
from pathlib import Path
from unittest import mock

import pytest

ROOT = Path(__file__).resolve().parents[3]
PLAN_SPEC = importlib.util.spec_from_file_location('plan', ROOT / 'tools/release/plan.py')
PLAN = importlib.util.module_from_spec(PLAN_SPEC)
PLAN_SPEC.loader.exec_module(PLAN)
SPEC = importlib.util.spec_from_file_location('prepare_release', ROOT / 'tools/release/prepare.py')
PREPARE = importlib.util.module_from_spec(SPEC)
with mock.patch.dict(sys.modules, {'plan': PLAN}):
    SPEC.loader.exec_module(PREPARE)


@pytest.fixture
def repository(tmp_path):
    def git(*arguments):
        return subprocess.check_output(
            [
                'git',
                '-C',
                str(tmp_path),
                '-c',
                'user.name=Release Fixture',
                '-c',
                'user.email=fixture@example.invalid',
                '-c',
                'commit.gpgsign=false',
                *arguments,
            ],
            text=True,
        ).strip()

    git('init', '-q')
    file = tmp_path / 'feature.txt'
    file.write_text('first')
    git('add', 'feature.txt')
    git('commit', '-qm', 'Initial version')
    base = git('rev-parse', 'HEAD')
    file.write_text('second')
    git('add', 'feature.txt')
    git('commit', '-qm', 'Improve powder fitting')
    return tmp_path, base, git('rev-parse', 'HEAD')


def test_preparation_uses_actual_ancestry_and_retry_identity(repository):
    root, base, head = repository
    history = {'schema': 'edi.releases/1', 'baseline_commit': base, 'releases': []}
    request = {
        'number': 1,
        'title': 'Refine backgrounds in full powder fits',
        'merged_at': '2026-11-05',
        'merge_commit_sha': head,
        'labels': ['[scope] bug', '[interface] desktop'],
    }
    with (
        mock.patch.object(PREPARE, 'ROOT', root),
        mock.patch.object(PREPARE, 'published_history', return_value=history),
        mock.patch.object(PREPARE, 'merged_requests', return_value=[request]),
        mock.patch.object(PREPARE, 'calendar_tags', return_value=['2026.11.0']),
        mock.patch.object(
            PREPARE, 'reserve_identity', return_value=('2026.11.1', datetime.date(2026, 11, 5))
        ) as reserve,
    ):
        first = PREPARE.prepare('enhantica/edi', head, root / 'first', datetime.date(2026, 11, 5))
    download_spec = importlib.util.spec_from_file_location(
        'download_release_inputs', ROOT / 'tools/release/download_plan.py'
    )
    download = importlib.util.module_from_spec(download_spec)
    download_spec.loader.exec_module(download)
    archive = io.BytesIO()
    with zipfile.ZipFile(archive, 'w') as stream:
        for path in (root / 'first').iterdir():
            stream.write(path, path.name)
    download.unpack_plan(archive.getvalue(), root / 'downloaded')
    assert (root / 'downloaded/notes.md').read_bytes() == (root / 'first/notes.md').read_bytes(), (
        'Preparation uses actual ancestry and retry identity.'
    )
    recorded = json.loads((root / 'first/release-history.json').read_text())
    PLAN.validate_history(recorded)
    reserve.assert_called_once_with(
        'enhantica/edi', head, datetime.date(2026, 11, 5), prerelease=False
    )
    assert first['release']['version'] == '2026.11.1', (
        'Preparation uses actual ancestry and retry identity.'
    )
    assert first['release']['commit'] == head, (
        'Preparation uses actual ancestry and retry identity.'
    )
    assert first['release']['notes']['Fixed'][0]['title'] == request['title'], (
        'Preparation uses actual ancestry and retry identity.'
    )
    with (
        mock.patch.object(PREPARE, 'ROOT', root),
        mock.patch.object(PREPARE, 'published_history', return_value=recorded),
        mock.patch.object(PREPARE, 'merged_requests', return_value=[]),
        mock.patch.object(PREPARE, 'calendar_tags', return_value=['2026.11.0', '2026.11.1']),
    ):
        retry = PREPARE.prepare('enhantica/edi', head, root / 'retry', datetime.date(2026, 12, 1))
    assert retry['reused'], 'Preparation uses actual ancestry and retry identity.'
    assert retry['release'] == first['release'], (
        'Preparation uses actual ancestry and retry identity.'
    )
    assert json.loads((root / 'retry/release-history.json').read_text()) == recorded, (
        'Preparation uses actual ancestry and retry identity.'
    )


def test_preparation_refuses_a_candidate_behind_the_published_baseline(repository):
    root, base, head = repository
    history = {'schema': 'edi.releases/1', 'baseline_commit': head, 'releases': []}
    with (
        mock.patch.object(PREPARE, 'ROOT', root),
        mock.patch.object(PREPARE, 'published_history', return_value=history),
        pytest.raises(subprocess.CalledProcessError),
    ):
        PREPARE.prepare('enhantica/edi', base, root / 'rejected', datetime.date(2026, 11, 5))
    assert not (root / 'rejected').exists(), (
        'Preparation refuses a candidate behind the published baseline.'
    )


def test_api_failure_is_not_treated_as_a_first_release():
    response = subprocess.CompletedProcess([], 1, b'', b'HTTP 403')
    with (
        mock.patch.object(PREPARE.subprocess, 'run', return_value=response),
        pytest.raises(RuntimeError, match='could not be read'),
    ):
        PREPARE.published_history('enhantica/edi')


def draft_release(identifier, tag, commit, *, draft=True, prerelease=True, body=None, assets=()):
    return {
        'id': identifier,
        'tag_name': tag,
        'target_commitish': commit,
        'draft': draft,
        'prerelease': prerelease,
        'body': PLAN.release_body('', '2026-11-17') if body is None else body,
        'assets': list(assets),
    }


@pytest.mark.parametrize(
    ('mode', 'deleted'),
    [
        ({'prerelease': True}, [1, 2]),
        ({'prerelease': False, 'reservations_only': True}, [5]),
    ],
)
def test_a_failed_run_withdraws_only_its_own_drafts(mode, deleted):
    commit, other = 'a' * 40, 'b' * 40
    releases = [
        draft_release(1, 'v2026.11.21', commit),
        draft_release(2, 'v2026.11.22', commit, body='Notes', assets=[{'name': 'x.dmg'}]),
        draft_release(3, 'v2026.11.20', commit, draft=False),
        draft_release(4, 'v2026.11.23', other),
        draft_release(5, 'v2026.11.6', commit, prerelease=False),
        draft_release(6, 'v2026.11.7', commit, prerelease=False, assets=[{'name': 'x.exe'}]),
        draft_release(7, 'not-a-calendar-tag', commit),
    ]
    calls = []

    def fake_run(command, **_):
        calls.append(command)
        return subprocess.CompletedProcess(command, 0)

    with (
        mock.patch.object(PREPARE, 'list_releases', return_value=releases),
        mock.patch.object(PREPARE.subprocess, 'run', side_effect=fake_run),
    ):
        tags = PREPARE.withdraw_drafts('enhantica/edi', commit, **mode)
    assert [command[-1] for command in calls] == [
        f'repos/enhantica/edi/releases/{identifier}' for identifier in deleted
    ], 'Only this source and channel lose their drafts; published releases are never touched.'
    assert len(tags) == len(deleted)
