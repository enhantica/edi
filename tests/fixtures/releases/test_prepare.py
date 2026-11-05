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
        'labels': ['[scope] bug'],
    }
    with (
        mock.patch.object(PREPARE, 'ROOT', root),
        mock.patch.object(PREPARE, 'published_history', return_value=history),
        mock.patch.object(PREPARE, 'merged_requests', return_value=[request]),
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
    assert (root / 'downloaded/notes.md').read_bytes() == (root / 'first/notes.md').read_bytes()
    recorded = json.loads((root / 'first/release-history.json').read_text())
    PLAN.validate_history(recorded)
    assert first['release']['version'] == '2026.11.0'
    assert first['release']['commit'] == head
    assert first['release']['notes']['Fixed'][0]['title'] == request['title']
    with (
        mock.patch.object(PREPARE, 'ROOT', root),
        mock.patch.object(PREPARE, 'published_history', return_value=recorded),
        mock.patch.object(PREPARE, 'merged_requests', return_value=[]),
    ):
        retry = PREPARE.prepare('enhantica/edi', head, root / 'retry', datetime.date(2026, 12, 1))
    assert retry['reused']
    assert retry['release'] == first['release']
    assert json.loads((root / 'retry/release-history.json').read_text()) == recorded


def test_preparation_refuses_a_candidate_behind_the_published_baseline(repository):
    root, base, head = repository
    history = {'schema': 'edi.releases/1', 'baseline_commit': head, 'releases': []}
    with (
        mock.patch.object(PREPARE, 'ROOT', root),
        mock.patch.object(PREPARE, 'published_history', return_value=history),
        pytest.raises(subprocess.CalledProcessError),
    ):
        PREPARE.prepare('enhantica/edi', base, root / 'rejected', datetime.date(2026, 11, 5))
    assert not (root / 'rejected').exists()


def test_api_failure_is_not_treated_as_a_first_release():
    response = subprocess.CompletedProcess([], 1, b'', b'HTTP 403')
    with (
        mock.patch.object(PREPARE.subprocess, 'run', return_value=response),
        pytest.raises(RuntimeError, match='could not be read'),
    ):
        PREPARE.published_history('enhantica/edi')
