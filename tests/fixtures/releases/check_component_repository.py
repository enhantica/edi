# SPDX-License-Identifier: BSD-3-Clause
"""Release, preview and Pages consumers of the per-platform component repositories."""

import hashlib
import importlib.util
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'tools/release'))


def module(path):
    spec = importlib.util.spec_from_file_location(path.stem, ROOT / path)
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


PROMOTE = module(Path('tools/release/promote.py'))
PAGES = module(Path('tools/ci/pages_update.py'))
APP = 'org.easydiffraction.app'
ASSISTANT = 'org.easydiffraction.app.assistant'
MAINTENANCE = 'org.easydiffraction.app.maintenancetool'


def sha1(path):
    return hashlib.sha1(path.read_bytes()).hexdigest()  # noqa: S324 - the framework's own checksum


def repository(folder, versions):
    """Write a repository in repogen's layout: one data archive and one metadata archive each."""
    updates = []
    for name, version in versions.items():
        component = folder / name
        component.mkdir(parents=True)
        data = component / f'{version}content.7z'
        data.write_bytes(f'{name} data'.encode())
        (component / f'{version}content.7z.sha1').write_text(sha1(data) + '\n')
        meta = component / f'{version}meta.7z'
        meta.write_bytes(f'{name} metadata'.encode())
        updates.append(
            f'<PackageUpdate><Name>{name}</Name><Version>{version}</Version>'
            f'<DownloadableArchives>content.7z</DownloadableArchives>'
            f'<SHA1>{sha1(meta)}</SHA1></PackageUpdate>'
        )
    (folder / 'Updates.xml').write_text('<Updates>' + ''.join(updates) + '</Updates>')
    return folder


@pytest.mark.parametrize(
    ('platform', 'names'),
    [
        ('macos-arm64', {APP, ASSISTANT, MAINTENANCE}),
        ('linux-x86_64', {APP, ASSISTANT}),
        ('windows-x86_64', {APP, ASSISTANT, MAINTENANCE}),
    ],
)
def test_release_admits_exactly_each_platform_component_set(tmp_path, platform, names):
    folder = repository(tmp_path / 'repository', dict.fromkeys(names, '2026.11.3'))
    PROMOTE.validate_repository(folder, '2026.11.3', expected=PROMOTE.component_names(platform))


def test_release_refuses_the_maintenance_component_on_linux(tmp_path):
    folder = repository(tmp_path / 'r', dict.fromkeys([APP, ASSISTANT, MAINTENANCE], '2026.11.3'))
    with pytest.raises(ValueError, match='does not match'):
        PROMOTE.validate_repository(
            folder, '2026.11.3', expected=PROMOTE.component_names('linux-x86_64')
        )


@pytest.mark.parametrize('platform', ['macos-arm64', 'windows-x86_64'])
def test_release_refuses_a_platform_without_its_maintenance_component(tmp_path, platform):
    folder = repository(tmp_path / 'r', dict.fromkeys([APP, ASSISTANT], '2026.11.3'))
    with pytest.raises(ValueError, match='does not match'):
        PROMOTE.validate_repository(
            folder, '2026.11.3', expected=PROMOTE.component_names(platform)
        )


def test_release_refuses_a_maintenance_component_of_another_version(tmp_path):
    versions = {APP: '2026.11.3', ASSISTANT: '2026.11.3', MAINTENANCE: '4.11.0'}
    folder = repository(tmp_path / 'r', versions)
    with pytest.raises(ValueError, match='does not match'):
        PROMOTE.validate_repository(
            folder, '2026.11.3', expected=PROMOTE.component_names('macos-arm64')
        )


@pytest.mark.parametrize('archive', ['2026.11.3content.7z', '2026.11.3meta.7z'])
def test_release_refuses_a_corrupt_maintenance_archive(tmp_path, archive):
    folder = repository(tmp_path / 'r', dict.fromkeys([APP, ASSISTANT, MAINTENANCE], '2026.11.3'))
    (folder / MAINTENANCE / archive).write_bytes(b'changed after repogen')
    with pytest.raises(ValueError, match='checksum differs'):
        PROMOTE.validate_repository(
            folder, '2026.11.3', expected=PROMOTE.component_names('macos-arm64')
        )


def preview_delivery(tmp_path, platform, names):
    """A qualified preview delivery for copy_preview, with the policy's own repository URL."""
    preview = module(Path('tools/release/preview.py'))
    policy = json.loads((ROOT / 'data/distribution.json').read_text())
    version, commit = '2026.11.3', 'a' * 40
    delivery = tmp_path / 'delivery'
    delivery.mkdir()
    name = PROMOTE.installer_name(version, platform, 'online')
    (delivery / name).write_bytes(b'installer')
    url = policy['primary_base'] + policy['repository_paths']['testing'].format(platform=platform)
    metadata = {
        'download': name,
        'download_sha256': hashlib.sha256(b'installer').hexdigest(),
        'version': version,
        'platform': platform,
        'kind': 'online',
        'edi_commit': commit,
        'repository_url': url,
    }
    (delivery / 'installer.json').write_text(json.dumps(metadata))
    (delivery / 'build-inputs.json').write_text(json.dumps({'edi_commit': commit}))
    (delivery / 'qualification.json').write_text(
        json.dumps({'passed': True, 'smoke': {'passed': True}})
    )
    components = tmp_path / 'components'
    repository(components / 'testing' / platform, dict.fromkeys(names, version))
    return preview, delivery, components, version, commit


@pytest.mark.parametrize(
    ('platform', 'names', 'accepted'),
    [
        ('macos-arm64', {APP, MAINTENANCE}, True),
        ('macos-arm64', {APP, ASSISTANT, MAINTENANCE}, True),
        ('linux-x86_64', {APP, ASSISTANT}, True),
        ('linux-x86_64', {APP, MAINTENANCE}, False),
        ('windows-x86_64', {APP, ASSISTANT, MAINTENANCE}, True),
        ('windows-x86_64', {APP, ASSISTANT}, False),
    ],
)
def test_preview_recovery_admits_the_maintenance_component_on_macos_and_windows(
    tmp_path, platform, names, accepted
):
    preview, delivery, components, version, commit = preview_delivery(tmp_path, platform, names)
    output = tmp_path / 'output'
    output.mkdir()
    if accepted:
        preview.copy_preview(delivery, components, output, platform, version, commit)
        assert {
            item.name for item in (output / 'components/testing' / platform).iterdir()
        } >= names
    else:
        with pytest.raises(ValueError, match='Unknown preview component set'):
            preview.copy_preview(delivery, components, output, platform, version, commit)


def test_pages_trims_old_maintenance_archives_with_the_app(tmp_path):
    folder = tmp_path / 'macos-arm64'
    for version in ['2026.11.1', '2026.11.3']:
        for name in [APP, MAINTENANCE]:
            (folder / name).mkdir(parents=True, exist_ok=True)
            (folder / name / f'{version}content.7z').write_bytes(b'data')
    PAGES.trim_testing_archives(folder, {'2026.11.3'})
    for name in [APP, MAINTENANCE]:
        assert [path.name for path in (folder / name).iterdir()] == ['2026.11.3content.7z']
