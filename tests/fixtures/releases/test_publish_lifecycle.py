# SPDX-License-Identifier: BSD-3-Clause
"""Release publication against a model of GitHub's documented draft behaviour, offline.

GitHub's ``releases/tags/{tag}`` route answers only for published releases; a draft is visible
in the release list and by its ID, and its tag exists only once it is published
(docs.github.com/en/rest/releases/releases, "Get a release by tag name" and "List releases").
``gh release upload`` finds a draft by tag the same way, by listing.
"""

import hashlib
import importlib.util
import json
import subprocess
import sys
from pathlib import Path
from unittest import mock

import pytest

ROOT = Path(__file__).resolve().parents[3]
REPO = 'enhantica/edi'


def module(name):
    spec = importlib.util.spec_from_file_location(name, ROOT / 'tools/release' / (name + '.py'))
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


PLAN = module('plan')
with mock.patch.dict(sys.modules, {'plan': PLAN}):
    PROMOTE = module('promote')
    PREPARE = module('prepare')
    with mock.patch.dict(sys.modules, {'prepare': PREPARE}):
        PUBLISH = module('publish_assets')
    with mock.patch.dict(sys.modules, {'publish_assets': PUBLISH, 'promote': PROMOTE}):
        PREVIEW = module('preview_draft')

RELEASE = {
    'version': '2026.11.0',
    'commit': 'a' * 40,
    'date': '2026-11-05',
    'notes': {
        'Added': [],
        'Fixed': [{'title': 'Fix plot zoom', 'pull_request': 1}],
        'Changed': [],
    },
}
HISTORY = {'schema': 'edi.releases/1', 'baseline_commit': 'b' * 40, 'releases': [RELEASE]}


class GitHub:
    """The release endpoints publication uses, with drafts hidden from the tag route."""

    def __init__(self):
        self.releases, self.tags, self.next_id, self.fail_after_create = {}, set(), 1, False

    def run(self, command, *, check=False, input=None, **_):
        code, out = self.answer(command[1:], input)
        if check and code:
            raise subprocess.CalledProcessError(code, command)
        stderr = b'HTTP 404' if code == 404 else b''
        return subprocess.CompletedProcess(command, 1 if code else 0, out, stderr)

    def check_output(self, command, *, input=None, **_):
        return self.run(command, check=True, input=input).stdout

    def by_tag_with_drafts(self, tag):
        return next((r for r in self.releases.values() if r['tag_name'] == tag), None)

    def answer(self, args, data):  # noqa: PLR0911 - one return per modelled endpoint
        if args[0] == 'release' and args[1] == 'upload':
            release = self.by_tag_with_drafts(args[2])
            path = Path(args[3])
            digest = 'sha256:' + hashlib.sha256(path.read_bytes()).hexdigest()
            release['assets'] = [a for a in release['assets'] if a['name'] != path.name]
            release['assets'].append({'name': path.name, 'digest': digest})
            return 0, b''
        assert args[0] == 'api', args
        method = args[args.index('--method') + 1] if '--method' in args else 'GET'
        path = next(a for a in args[1:] if a.startswith('repos/'))[len(f'repos/{REPO}/') :]
        if method == 'POST' and path == 'releases':
            payload = json.loads(data)
            release = {**payload, 'id': self.next_id, 'assets': [], 'html_url': 'u'}
            self.releases[self.next_id] = release
            self.next_id += 1
            if self.fail_after_create:
                return 1, b''
            return 0, json.dumps(release).encode()
        if method == 'PATCH':
            release = self.releases[int(path.rsplit('/', 1)[1])]
            release['draft'] = False
            release['make_latest'] = 'true' if 'make_latest=true' in args else 'false'
            self.tags.add(release['tag_name'])
            return 0, b'{}'
        if path.startswith('releases?'):
            return 0, json.dumps([list(self.releases.values())]).encode()
        if path.startswith('releases/tags/'):
            found = self.by_tag_with_drafts(path.rsplit('/', 1)[1])
            return (0, json.dumps(found).encode()) if found and not found['draft'] else (404, b'')
        if path.startswith('git/ref/tags/'):
            return (0, b'{}') if path.rsplit('/', 1)[1] in self.tags else (404, b'')
        if path.startswith('releases/'):
            found = self.releases.get(int(path.rsplit('/', 1)[1]))
            return (0, json.dumps(found).encode()) if found else (404, b'')
        raise AssertionError(args)


@pytest.fixture
def github():
    model = GitHub()
    fake = mock.Mock(
        run=model.run,
        check_output=model.check_output,
        CalledProcessError=subprocess.CalledProcessError,
    )
    with (
        mock.patch.object(PUBLISH, 'subprocess', fake),
        mock.patch.object(PREVIEW, 'subprocess', fake),
        mock.patch.object(PUBLISH, 'published_history', return_value={**HISTORY, 'releases': []}),
    ):
        yield model


@pytest.fixture
def folder(tmp_path):
    (tmp_path / 'assets').mkdir()
    (tmp_path / 'release.json').write_text(json.dumps(RELEASE))
    (tmp_path / 'assets/release-history.json').write_text(json.dumps(HISTORY))
    (tmp_path / 'assets/installer.zip').write_bytes(b'qualified installer')
    (tmp_path / 'notes.md').write_text(PLAN.markdown_notes(RELEASE))
    return tmp_path


def test_first_stable_publication_creates_uploads_and_finalizes_its_own_draft(github, folder):
    PUBLISH.publish(REPO, folder)
    (release,) = github.releases.values()
    assert release['draft'] and [a['name'] for a in release['assets']] == [
        'installer.zip',
        'release-history.json',
    ]
    PUBLISH.publish(REPO, folder, finalize=True)
    assert (
        not release['draft'] and release['make_latest'] == 'true' and 'v2026.11.0' in github.tags
    )
    assert len(github.releases) == 1


def test_a_retry_after_creation_resumes_the_same_draft(github, folder):
    github.fail_after_create = True
    with pytest.raises(subprocess.CalledProcessError):
        PUBLISH.publish(REPO, folder)
    github.fail_after_create = False
    PUBLISH.publish(REPO, folder)
    PUBLISH.publish(REPO, folder)
    (release,) = github.releases.values()
    assert len(release['assets']) == 2 and release['draft']


def test_finalizing_without_a_draft_refuses(github, folder):
    with pytest.raises(ValueError, match='Create and verify the draft'):
        PUBLISH.publish(REPO, folder, finalize=True)
    assert github.releases == {}


def test_a_tag_without_its_release_and_duplicate_drafts_refuse(github, folder):
    github.tags.add('v2026.11.0')
    with pytest.raises(ValueError, match='tag already exists'):
        PUBLISH.publish(REPO, folder)
    github.tags.clear()
    for _ in range(2):
        github.run(
            ['gh', 'api', '--method', 'POST', f'repos/{REPO}/releases'],
            input=json.dumps({'tag_name': 'v2026.11.0', 'draft': True}).encode(),
        )
    with pytest.raises(ValueError, match='Multiple releases'):
        PUBLISH.publish(REPO, folder)


def test_preview_drafts_are_found_through_the_same_lookup(github, tmp_path):
    archive = tmp_path / 'installer.zip'
    archive.write_bytes(b'preview installer')
    archives = [(archive, hashlib.sha256(archive.read_bytes()).hexdigest())]
    PREVIEW.publish(REPO, RELEASE, 'Notes\n', archives)
    PREVIEW.publish(REPO, RELEASE, 'Notes\n', archives)
    (release,) = github.releases.values()
    assert release['draft'] and release['prerelease'] and len(release['assets']) == 1
