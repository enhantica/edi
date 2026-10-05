"""Check public metadata and files using local commits and event payloads."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[3]
CONTRACT = json.loads(
    (ROOT / 'tests/fixtures/e04_t12_public_release/content-contract.json').read_text()
)


def git(root, *args):
    env = {k: v for k, v in os.environ.items() if not k.startswith('GIT_')}
    completed = subprocess.run(
        ['git', '-C', str(root), *args],
        env=env,
        capture_output=True,
        text=True,
        check=False,
        timeout=5,
    )
    assert completed.returncode == 0, 'local content controls require valid Git operations'
    return completed.stdout.strip()


def commit(root, message):
    git(root, 'add', '.')
    git(
        root,
        '-c',
        'user.name=Contributor',
        '-c',
        'user.email=person@example.invalid',
        'commit',
        '--allow-empty',
        '-qm',
        message,
    )
    return git(root, 'rev-parse', 'HEAD')


def specimen(tmp_path):
    root = tmp_path / 'source'
    root.mkdir()
    git(root, 'init', '-q', '-b', 'main')
    (root / 'README.md').write_text('A diffraction library.\n')
    base = commit(root, 'Start the project')
    return root, base


def check(root, base, head, event, tmp_path):
    script = ROOT / CONTRACT['script']
    assert script.is_file(), 'public CI needs an executable file and metadata content checker'
    body_file = tmp_path / 'body.txt'
    pr = event.get('pull_request')
    body_file.write_text(pr['body'] if pr else '')
    values = {
        'base': base or 'root',
        'head': head,
        'title': pr['title'] if pr else '',
        'body_file': body_file,
    }
    arguments = [value.format(**values) for value in CONTRACT['arguments']]
    if pr is not None:
        arguments.extend(value.format(**values) for value in CONTRACT['pr_arguments'])
    env = {k: v for k, v in os.environ.items() if not k.startswith('GIT_')}
    result = subprocess.run(
        [sys.executable, str(script), *arguments],
        cwd=root,
        env=env,
        capture_output=True,
        text=True,
        check=False,
        timeout=8,
    )
    assert 'Traceback' not in result.stderr and 'unrecognized arguments' not in result.stderr, (
        'content refusals must be policy diagnostics, not crashes or CLI mismatches'
    )
    return result


def event(title='Improve the loader', body='Read the saved format. Keep existing values.'):
    return {'pull_request': {'title': title, 'body': body}}


def forbidden(kind):
    return {
        'long-subject': 'x' * (CONTRACT['subject_limit'] + 1),
        'long-body': 'Improve the loader\n\n' + 'Describe another unrelated detail.\n' * 140,
        'process-suffix': 'Improve the loader (' + 're' + 'lay ' + 'E' + '05-' + 'T1)',
        'personal-path': 'Open /h' + 'ome/contributor/work/project.txt',
        'mac-path': 'Open /U' + 'sers/contributor/work/project.txt',
        'issue-id': 'Fix ' + 'I-' + '0300',
        'lane-id': 'Resume ' + 're' + 'lay-rc-edi-' + 'E' + '05-' + 'T1-implement',
        'private-citation': 'Follow crysta ' + 'A' + 'DR-0012',
        'private-url': 'Read https://github.com/enhantica/c' + 'rysta/blob/main/docs/design.md',
    }[kind]


@pytest.mark.parametrize(
    'kind',
    [
        'long-subject',
        'long-body',
        'process-suffix',
        'personal-path',
        'mac-path',
        'issue-id',
        'lane-id',
        'private-citation',
        'private-url',
    ],
)
def test_e04_t12_commit_metadata_escapes_are_refused(tmp_path, kind):
    root, base = specimen(tmp_path)
    clean = commit(root, 'Improve the loader\n\nRead the saved format. Keep existing values.')
    good = check(root, base, clean, event(), tmp_path)
    assert good.returncode == 0, 'ordinary public commit and PR text must be accepted'
    bad = commit(root, forbidden(kind))
    rejected = check(root, clean, bad, event(), tmp_path)
    assert rejected.returncode != 0, (
        'public content checks must reject forbidden commit metadata: ' + kind
    )


@pytest.mark.parametrize(
    ('field', 'kind'),
    [
        ('body', 'issue-id'),
        ('body', 'process-suffix'),
        ('body', 'personal-path'),
        ('body', 'long-body'),
        ('title', 'private-citation'),
        ('title', 'private-url'),
        ('title', 'long-subject'),
    ],
)
def test_e04_t12_pr_metadata_escapes_are_refused(tmp_path, field, kind):
    root, base = specimen(tmp_path)
    head = commit(root, 'Improve the loader')
    payload = event()
    good = check(root, base, head, payload, tmp_path)
    assert good.returncode == 0, 'valid PR metadata must pass before an escape is attempted'
    payload['pull_request'][field] = forbidden(kind)
    rejected = check(root, base, head, payload, tmp_path)
    assert rejected.returncode != 0, (
        'public content checks must inspect the actual PR title and body: ' + field + '/' + kind
    )


def test_e04_t12_all_commits_in_the_range_are_checked(tmp_path):
    root, base = specimen(tmp_path)
    commit(root, forbidden('process-suffix'))
    head = commit(root, 'Improve the loader')
    result = check(root, base, head, event(), tmp_path)
    assert result.returncode != 0, (
        'a clean tip must not hide forbidden metadata in an earlier PR commit'
    )


def test_e04_t12_test_name_allowance_does_not_hide_metadata(tmp_path):
    root, base = specimen(tmp_path)
    message = 'Repair test_' + 'e05_t1_parser (' + 're' + 'lay ' + 'E' + '05-' + 'T1)'
    head = commit(root, message)
    result = check(root, base, head, event(), tmp_path)
    assert result.returncode != 0, (
        'the file test-name allowance must never exempt commit or PR metadata'
    )


@pytest.mark.parametrize('channel', ['text', 'zip-member', 'test-private', 'test-process'])
def test_e04_t12_file_residue_is_checked_with_metadata(tmp_path, channel):
    root, base = specimen(tmp_path)
    clean = commit(root, 'Improve the loader')
    assert check(root, base, clean, event(), tmp_path).returncode == 0, (
        'public-safe files and metadata must pass before residue is introduced'
    )
    if channel == 'text':
        (root / 'note.txt').write_text(forbidden('personal-path'))
    elif channel == 'zip-member':
        with zipfile.ZipFile(root / 'input.zip', 'w', zipfile.ZIP_DEFLATED) as archive:
            archive.writestr('notes.txt', forbidden('private-citation'))
    else:
        path = root / 'tests/unit/py/test_saved.py'
        path.parent.mkdir(parents=True)
        residue = forbidden('private-citation' if channel == 'test-private' else 'process-suffix')
        path.write_text('# ' + residue + '\ndef test_saved():\n    pass\n')
    head = commit(root, 'Add saved data')
    result = check(root, clean, head, event(), tmp_path)
    assert result.returncode != 0, (
        'metadata validation must also reject publication residue in files and decoded members'
    )


def test_e04_t12_initial_one_commit_tree_is_checked(tmp_path):
    root, head = specimen(tmp_path)
    good = check(root, None, head, {}, tmp_path)
    assert good.returncode == 0, 'the first public-safe snapshot must pass without a parent commit'
    head = commit(root, forbidden('personal-path'))
    result = check(root, None, head, {}, tmp_path)
    assert result.returncode != 0, (
        'the initial-push root base must check history rather than bypass commit metadata'
    )


def test_e04_t12_content_ci_checks_pushes_and_pr_text(tmp_path):
    observe_content_workflows(ROOT)
    prepared = tmp_path / 'tools/public-release/github/workflows'
    installed = tmp_path / '.github/workflows'
    for folder in (prepared, installed):
        folder.mkdir(parents=True)
        (folder / 'content.yml').write_bytes((ROOT / '.github/workflows/content.yml').read_bytes())
    observe_content_workflows(tmp_path)
    path = installed / 'content.yml'
    original = path.read_text()
    for damage in ('trigger', 'checker', 'head', 'title', 'body', 'base'):
        document = yaml.safe_load(original)
        if damage == 'trigger':
            document.get('on', document.get(True)).pop('pull_request')
        else:
            before = {
                'checker': CONTRACT['script'],
                'head': 'pull_request.head.sha',
                'title': '--title',
                'body': '--body-file',
                'base': '--base',
            }[damage]
            document = yaml.safe_load(original.replace(before, 'missing-input'))
        path.write_text(yaml.safe_dump(document))
        with pytest.raises(AssertionError):
            observe_content_workflows(tmp_path)
        path.write_text(original)
    path.unlink()
    with pytest.raises(AssertionError):
        observe_content_workflows(tmp_path)


def observe_content_workflows(root):
    prepared = root / 'tools/public-release/github/workflows'
    installed = root / '.github/workflows'
    folders = [folder for folder in (prepared, installed) if folder.is_dir()]
    assert folders, 'content CI must exist in the prepared or installed workflow tree'
    for folder in folders:
        workflows = [yaml.safe_load(path.read_text()) for path in folder.glob('*.yml')]
        matches = [
            (data, job)
            for data in workflows
            for job in data['jobs'].values()
            if any(CONTRACT['script'] in str(step.get('run', '')) for step in job.get('steps', []))
        ]
        assert matches, 'the cut snapshot CI must enforce public file and metadata content'
        for data, job in matches:
            triggers = data.get('on', data.get(True))
            assert 'push' in triggers and 'pull_request' in triggers, (
                'content CI must run on pushes and PR metadata changes'
            )
            text = json.dumps(job)
            assert 'pull_request' in text and '--title' in text and '--body-file' in text, (
                'CI content checks must receive PR text, not only checkout files'
            )
            assert (
                '--base' in text and 'pull_request.head.sha' in text and 'fetch-depth' in text
            ), 'CI content checks must use the actual PR head with its complete commit range'


@pytest.mark.parametrize('mode', ['root', 'push', 'pr'])
@pytest.mark.parametrize(
    'channel',
    [
        'added-removed',
        'private-clean',
        'archive-removed',
        'archive-clean',
        'tracked-build',
        'broken-link',
        'test-collateral',
        'member-collateral',
    ],
)
def test_e04_t12_every_published_blob_is_checked(tmp_path, mode, channel):
    root, base = specimen(tmp_path)
    if channel == 'archive-clean':
        with zipfile.ZipFile(root / 'saved.zip', 'w', zipfile.ZIP_DEFLATED) as archive:
            archive.writestr('test_saved.py', 'A saved diffraction pattern.\n')
        base = commit(root, 'Add saved data')
    payload = event() if mode == 'pr' else {}
    start = None if mode == 'root' else base
    assert check(root, start, base, payload, tmp_path).returncode == 0, (
        'each publication range must accept a clean history before its blob escape'
    )
    bad = forbidden('private-citation')
    if channel in {'added-removed', 'private-clean'}:
        path = root / ('README.md' if channel == 'private-clean' else 'note.txt')
        path.write_text(bad)
    elif channel in {'archive-removed', 'archive-clean', 'member-collateral'}:
        path = root / 'saved.zip'
        member = bad if channel != 'member-collateral' else collateral()
        with zipfile.ZipFile(path, 'w', zipfile.ZIP_DEFLATED) as archive:
            archive.writestr('test_saved.py', member)
    elif channel == 'tracked-build':
        (root / '.gitignore').write_text('build/\n')
        path = root / 'build/note.txt'
        path.parent.mkdir()
        path.write_text(forbidden('personal-path'))
        git(root, 'add', '-f', 'build/note.txt')
    elif channel == 'broken-link':
        path = root / 'saved-link'
        path.symlink_to('/h' + 'ome/contributor/missing/data')
    else:
        path = root / 'tests/integration/py/test_saved.py'
        path.parent.mkdir(parents=True)
        path.write_text(collateral())
    head = commit(root, 'Add saved data')
    if channel.endswith('removed'):
        path.unlink()
        head = commit(root, 'Remove saved data')
    elif channel.endswith('clean'):
        if channel.startswith('archive'):
            with zipfile.ZipFile(path, 'w', zipfile.ZIP_DEFLATED) as archive:
                archive.writestr('test_saved.py', 'A saved diffraction pattern.\n')
        else:
            path.write_text('A saved diffraction pattern.\n')
        head = commit(root, 'Update saved data')
    result = check(root, start, head, payload, tmp_path)
    assert result.returncode != 0, (
        'root, push and PR ranges must reject every introduced Git blob, including ' + channel
    )


def collateral():
    return (
        'def test_' + 'e05_t1_saved(): pass  # ' + 're' + 'lay ' + 'E' + '05-' + 'T1 I-' + '0300\n'
    )


@pytest.mark.parametrize('mode', ['root', 'push', 'pr'])
@pytest.mark.parametrize('channel', ['test-name', 'decoded-member'])
def test_e04_t12_ordinary_test_names_and_members_remain_compatible(tmp_path, mode, channel):
    root, base = specimen(tmp_path)
    text = 'def test_' + 'e05_t1_saved():\n    pass\n'
    if channel == 'test-name':
        path = root / 'tests/integration/py/test_saved.py'
        path.parent.mkdir(parents=True)
        path.write_text(text)
    else:
        with zipfile.ZipFile(root / 'saved.zip', 'w', zipfile.ZIP_DEFLATED) as archive:
            archive.writestr('test_saved.py', text)
    head = commit(root, 'Add saved data')
    result = check(
        root, None if mode == 'root' else base, head, event() if mode == 'pr' else {}, tmp_path
    )
    assert result.returncode == 0, (
        'retaining ordinary test names and decoded members must work in every publication range'
    )


def synthetic_credential(kind):
    return {
        'aws-id': 'AK' + 'IA' + 'A1' * 8,
        'github': 'gh' + 'p_' + 'Ab7' * 12,
        'github-fine': 'github' + '_pat_' + 'Ab7_' * 15,
        'slack': 'xo' + 'xb-' + 'Ab7-' * 4,
        'google': 'AI' + 'za' + 'Ab7x_' * 7,
        'private-key': '-----BEGIN ' + 'PRIVATE KEY-----',
        'aws-secret': 'aws_secret_access_key=' + 'Ab7x' * 10,
    }[kind]


@pytest.mark.parametrize(
    'kind', ['aws-id', 'github', 'github-fine', 'slack', 'google', 'private-key', 'aws-secret']
)
@pytest.mark.parametrize('channel', ['commit-root', 'commit-push', 'commit-pr', 'title', 'body'])
def test_e04_t12_credentials_are_refused_and_redacted_in_metadata(tmp_path, kind, channel):
    root, base = specimen(tmp_path)
    payload = event()
    start = None if channel == 'commit-root' else base
    assert check(root, start, base, payload, tmp_path).returncode == 0, (
        'safe metadata must pass before independently constructed credentials are introduced'
    )
    token = synthetic_credential(kind)
    if channel.startswith('commit'):
        head = commit(root, token)
        payload = event() if channel == 'commit-pr' else {}
    else:
        head = base
        payload['pull_request'][channel] = token
    result = check(root, start, head, payload, tmp_path)
    assert result.returncode != 0, (
        'every metadata channel must refuse recognised credential shapes'
    )
    output = result.stdout + result.stderr
    assert token not in output, (
        'credential refusals must redact the credential rather than repeat it'
    )
    assert any(word in output.lower() for word in ('credential', 'secret', 'token', 'key')), (
        'metadata credentials need an explicit policy diagnostic'
    )


def test_e04_t12_transformed_snapshot_keeps_the_content_workflow_observer(tmp_path):
    root, _base = specimen(tmp_path)
    prepared = root / 'tools/public-release/github/workflows'
    source = ROOT / 'tools/public-release/github/workflows'
    if not source.is_dir():
        source = ROOT / '.github/workflows'
    shutil.copytree(source, prepared)
    head = commit(root, 'Prepare public checks')
    output = tmp_path / 'published'
    result = subprocess.run(
        [
            sys.executable,
            str(ROOT / 'tools/public-release/snapshot.py'),
            '--source',
            str(root),
            '--ref',
            head,
            '--output',
            str(output),
            '--skip-hidden',
        ],
        capture_output=True,
        text=True,
        check=False,
        timeout=8,
    )
    assert result.returncode == 0, (
        'the workflow observer control must use the actual snapshot transformation'
    )
    assert git(output, 'rev-list', '--count', 'HEAD') == '1', (
        'the published workflow control must have one fresh commit'
    )
    assert not (output / 'tools/public-release/github').exists(), (
        'the observer must run after the preparation directory has been removed'
    )
    observe_content_workflows(output)

    folder = output / '.github/workflows'
    for workflow in folder.glob('*.yml'):
        original = workflow.read_text()
        document = yaml.safe_load(original)
        jobs = [
            job
            for job in document['jobs'].values()
            if any(CONTRACT['script'] in str(step.get('run', '')) for step in job.get('steps', []))
        ]
        if not jobs:
            continue
        for trigger in ('push', 'pull_request'):
            damaged = yaml.safe_load(original)
            damaged.get('on', damaged.get(True)).pop(trigger)
            workflow.write_text(yaml.safe_dump(damaged))
            with pytest.raises(AssertionError, match='pushes and PR'):
                observe_content_workflows(output)
            workflow.write_text(original)
        for argument, diagnostic in (
            ('--title', 'PR text'),
            ('--body-file', 'PR text'),
            ('--base', 'actual PR head'),
            ('pull_request.head.sha', 'actual PR head'),
            ('fetch-depth', 'actual PR head'),
        ):
            workflow.write_text(original.replace(argument, 'missing-input'))
            with pytest.raises(AssertionError, match=diagnostic):
                observe_content_workflows(output)
            workflow.write_text(original)
