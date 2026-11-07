# SPDX-License-Identifier: BSD-3-Clause
"""Recorded qualification evidence and immutable release retry boundaries."""

import importlib.util
import json
import sys
from pathlib import Path
from unittest import mock

import pytest

ROOT = Path(__file__).resolve().parents[3]


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


def test_cli_delivery_requires_the_executed_identity_and_unchanged_zip(tmp_path):
    version, commit, platform = '2026.11.4', 'a' * 40, 'linux-x86_64'
    assert PROMOTE.validate_cli(tmp_path, version, commit, platform) is None, (
        'CLI delivery requires the executed identity and unchanged ZIP.'
    )
    archive = tmp_path / f'EasyDiffraction-{version}-{platform}-cli.zip'
    archive.write_bytes(b'qualified zip')
    evidence = {
        'passed': True,
        'version': version,
        'commit': commit,
        'platform': platform,
        'zip': archive.name,
        'sha256': PROMOTE.digest(archive),
    }
    (tmp_path / 'cli-qualification.json').write_text(json.dumps(evidence), encoding='utf-8')
    assert PROMOTE.validate_cli(tmp_path, version, commit, platform) == archive, (
        'CLI delivery requires the executed identity and unchanged ZIP.'
    )
    archive.write_bytes(b'different zip')
    with pytest.raises(ValueError, match='CLI identity or ZIP bytes differ'):
        PROMOTE.validate_cli(tmp_path, version, commit, platform)


def test_preview_notes_use_canonical_interfaces_and_recover_early_cli_drafts():
    notes = json.loads((ROOT / 'data/installer-preview-notes.json').read_text(encoding='utf-8'))
    assert all(PLAN.note_interfaces(entry) for entries in notes.values() for entry in entries), (
        'Preview notes use canonical interfaces and recover early CLI drafts.'
    )
    expected = PREVIEW._preview_notes({'notes': notes})
    cli = next(entry for entry in notes['Added'] if entry['interfaces'] == ['cli-standalone'])
    cli['interfaces'] = ['cli']
    assert PREVIEW._preview_notes({'notes': notes}) == expected, (
        'Preview notes use canonical interfaces and recover early CLI drafts.'
    )
    assert cli['interfaces'] == ['cli'], (
        'Preview notes use canonical interfaces and recover early CLI drafts.'
    )


@pytest.mark.parametrize('damage', ['none', 'branch', 'workflow', 'job', 'attempt', 'expired'])
def test_promotion_requires_every_platform_from_one_successful_main_attempt(damage):
    run = {
        'path': '.github/workflows/installers.yml',
        'head_branch': 'main',
        'status': 'completed',
        'conclusion': 'success',
        'event': 'workflow_dispatch',
        'run_attempt': 2,
    }
    jobs = [
        {'name': name, 'run_attempt': 2, 'conclusion': 'success'}
        for name in [
            *[f'installer · {name}' for name in PROMOTE.PLATFORMS],
            'record qualified release inputs',
        ]
    ]
    names = ['qualified-release-plan-2']
    for name in PROMOTE.PLATFORMS:
        names += [f'installer-{name}-2', f'installer-components-{name}-2']
    artifacts = [
        {'name': name, 'id': index + 1, 'expired': False} for index, name in enumerate(names)
    ]
    if damage == 'branch':
        run['head_branch'] = 'development'
    elif damage == 'workflow':
        run['path'] = '.github/workflows/other.yml'
    elif damage == 'job':
        jobs[0]['conclusion'] = 'failure'
    elif damage == 'attempt':
        jobs[0]['run_attempt'] = 1
    elif damage == 'expired':
        artifacts[0]['expired'] = True
    if damage == 'none':
        assert set(PROMOTE.qualified_artifacts(run, artifacts, jobs)) == set(names), (
            'Promotion requires every platform from one successful main attempt.'
        )
    else:
        with pytest.raises(ValueError, match=r'qualification|platform|artifacts'):
            PROMOTE.qualified_artifacts(run, artifacts, jobs)


@pytest.mark.parametrize(
    'damage', ['none', 'bytes', 'source', 'history', 'not-executed', 'channel']
)
def test_delivery_compares_zip_and_executed_app_to_prepared_identity(tmp_path, damage):
    release = {'version': '2026.11.0', 'commit': 'a' * 40}
    policy = json.loads((ROOT / 'data/distribution.json').read_text())
    platform = 'linux-x86_64'
    url = (
        policy['primary_base'].rstrip('/')
        + '/'
        + policy['repository_paths']['stable'].format(platform=platform)
    )
    name = 'EasyDiffraction-2026.11.0-linux-x86_64-online.zip'
    (tmp_path / name).write_bytes(b'qualified installer')
    metadata = {
        **release,
        'edi_commit': release['commit'],
        'release_history_sha256': 'b' * 64,
        'platform': platform,
        'kind': 'online',
        'repository_url': url,
        'zip': name,
        'zip_sha256': PROMOTE.digest(tmp_path / name),
    }
    build = {
        'edi_commit': release['commit'],
        'release_version': release['version'],
        'release_history_sha256': 'b' * 64,
    }
    receipt = {
        'passed': True,
        'smoke': {
            'passed': True,
            'app_version': release['version'],
            'release_history_sha256': 'b' * 64,
        },
    }
    if damage == 'source':
        build['edi_commit'] = 'c' * 40
    elif damage == 'history':
        receipt['smoke']['release_history_sha256'] = 'c' * 64
    elif damage == 'not-executed':
        receipt['passed'] = False
    elif damage == 'channel':
        metadata['repository_url'] = url.replace('/repository/', '/repository/testing/')
    elif damage == 'bytes':
        (tmp_path / name).write_bytes(b'rebuilt installer')
    for filename, value in [
        ('installer.json', metadata),
        ('build-inputs.json', build),
        ('qualification.json', receipt),
    ]:
        (tmp_path / filename).write_text(json.dumps(value))
    if damage == 'none':
        assert PROMOTE.validate_delivery(tmp_path, release, 'b' * 64, platform).name == name, (
            'Delivery compares ZIP and executed app to prepared identity.'
        )
    else:
        with pytest.raises(ValueError, match=r'identity|bytes'):
            PROMOTE.validate_delivery(tmp_path, release, 'b' * 64, platform)


@pytest.mark.parametrize('damage', ['none', 'source', 'notes', 'asset', 'published-missing'])
def test_release_retry_never_overwrites_an_existing_identity(damage):
    release = {'commit': 'a' * 40}
    existing = {
        'target_commitish': 'a' * 40,
        'body': 'User notes',
        'draft': True,
        'assets': [{'name': 'installer.zip', 'digest': 'sha256:' + 'b' * 64}],
    }
    if damage == 'source':
        existing['target_commitish'] = 'c' * 40
    elif damage == 'notes':
        existing['body'] = 'Different notes'
    elif damage == 'asset':
        existing['assets'][0]['digest'] = 'sha256:' + 'c' * 64
    elif damage == 'published-missing':
        existing.update(draft=False, assets=[])
    if damage == 'none':
        assert PUBLISH.check_existing(
            existing, release, 'User notes', {'installer.zip': 'b' * 64}
        ) == {'installer.zip'}, 'Release retry never overwrites an existing identity.'
    else:
        with pytest.raises(ValueError, match=r'different|cannot'):
            PUBLISH.check_existing(existing, release, 'User notes', {'installer.zip': 'b' * 64})


def test_draft_cli_passes_the_commit_and_deliveries_to_qualification():
    args = ['preview_draft.py', '--repo', 'enhantica/edi', '--commit', 'a' * 40, 'delivery']
    qualified = ({'version': '2026.11.0'}, 'Release notes', [])
    with (
        mock.patch.object(sys, 'argv', args),
        mock.patch.object(PREVIEW, 'prepare', autospec=True, return_value=qualified) as prepare,
        mock.patch.object(PREVIEW, 'publish') as publish,
    ):
        PREVIEW.main()
    prepare.assert_called_once_with('a' * 40, [Path('delivery')], mac_linux_only=False)
    publish.assert_called_once_with('enhantica/edi', *qualified)


def test_only_preview_drafts_can_replace_a_known_installer():
    release = {'commit': 'a' * 40}
    existing = {
        'target_commitish': release['commit'],
        'body': 'User notes',
        'draft': True,
        'assets': [{'name': 'installer.zip', 'digest': 'sha256:' + 'b' * 64}],
    }
    replacement = {'installer.zip': 'c' * 64}
    assert (
        PUBLISH.check_existing(
            existing,
            release,
            'User notes',
            replacement,
            replace_draft_assets=True,
        )
        == set()
    ), 'Only preview drafts can replace a known installer.'
    for change in ({'draft': False}, {'target_commitish': 'd' * 40}, {'body': 'Edited notes'}):
        with pytest.raises(ValueError, match='different'):
            PUBLISH.check_existing(
                {**existing, **change},
                release,
                'User notes',
                replacement,
                replace_draft_assets=True,
            )


@pytest.mark.parametrize('damage', ['none', 'stale', 'missing'])
def test_release_history_progression_refuses_stale_candidates(damage):
    release = {
        'version': '2026.11.0',
        'commit': 'a' * 40,
        'date': '2026-11-05',
        'notes': {
            'Added': [],
            'Fixed': [{'title': 'Improve refinement', 'pull_request': 1}],
            'Changed': [],
        },
    }
    previous = {'schema': 'edi.releases/1', 'baseline_commit': 'b' * 40, 'releases': []}
    history = {**previous, 'releases': [release]}
    if damage == 'stale':
        previous['baseline_commit'] = 'c' * 40
    elif damage == 'missing':
        history['releases'] = []
    if damage == 'none':
        PUBLISH.check_progression(history, previous, release)
        PUBLISH.check_progression(history, history, release)
    else:
        with pytest.raises(ValueError, match=r'moved|missing'):
            PUBLISH.check_progression(history, previous, release)


@pytest.mark.parametrize(
    'damage', ['none', 'archive', 'assistant_archive', 'version', 'missing', 'declaration']
)
def test_component_identity_and_original_checksums_are_verified(tmp_path, damage):
    content = '<Updates>'
    for name in ['org.easyscience.edi', 'org.easyscience.edi.assistant']:
        optional = name.endswith('.assistant')
        if optional and damage == 'missing':
            continue
        component = tmp_path / name
        component.mkdir()
        archive = component / '2026.11.0content.7z'
        archive.write_bytes(b'qualified component bytes')
        metadata = component / '2026.11.0meta.7z'
        metadata.write_bytes(b'qualified component metadata')
        for path in [archive, metadata]:
            with path.open('rb') as stream:
                checksum = PROMOTE.hashlib.file_digest(stream, 'sha1').hexdigest()
            path.with_suffix(path.suffix + '.sha1').write_text(checksum)
        version = '2026.11.1' if optional and damage == 'version' else '2026.11.0'
        content += (
            f'<PackageUpdate><Name>{name}</Name>'
            f'<Version>{version}</Version><DownloadableArchives>content.7z</DownloadableArchives>'
            f'<SHA1>{metadata.with_suffix(".7z.sha1").read_text()}</SHA1></PackageUpdate>'
        )
        if damage == ('assistant_archive' if optional else 'archive'):
            archive.write_bytes(b'rebuilt component')
    content += '</Updates>'
    if damage == 'declaration':
        content = '<!DOCTYPE Updates>' + content
    (tmp_path / 'Updates.xml').write_text(content)
    if damage == 'none':
        PROMOTE.validate_repository(tmp_path, '2026.11.0')
    else:
        with pytest.raises(ValueError, match=r'checksum|match|declarations'):
            PROMOTE.validate_repository(tmp_path, '2026.11.0')
