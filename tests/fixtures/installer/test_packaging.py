# SPDX-License-Identifier: BSD-3-Clause
"""Offline boundary checks for the native installer tool."""

import importlib.util
import io
import os
import subprocess
import sys
import tarfile
import tomllib
import zipfile
from pathlib import Path
from unittest import mock

import pytest
from defusedxml import ElementTree

SPEC = importlib.util.spec_from_file_location(
    'installer_package', Path(__file__).resolve().parents[3] / 'tools/installer/package.py'
)
PACKAGE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(PACKAGE)

AUDIT_SPEC = importlib.util.spec_from_file_location(
    'installer_audit', PACKAGE.ROOT / 'tools/installer/audit.py'
)
AUDIT = importlib.util.module_from_spec(AUDIT_SPEC)
AUDIT_SPEC.loader.exec_module(AUDIT)


def test_manifest_preserves_relative_links(tmp_path):
    (tmp_path / 'real').write_bytes(b'library')
    (tmp_path / 'link').symlink_to('real')
    manifest = PACKAGE.payload_manifest(tmp_path)
    assert manifest['link'] == {'link': 'real'}
    assert manifest['real']['sha256'] == PACKAGE.sha256(tmp_path / 'real')


@pytest.mark.parametrize('target', ['../elsewhere', '/etc/passwd', 'missing'])
def test_manifest_refuses_escaping_or_broken_links(tmp_path, target):
    (tmp_path / 'link').symlink_to(target)
    with pytest.raises(RuntimeError, match='link'):
        PACKAGE.payload_manifest(tmp_path)


def test_manifest_refuses_empty_stage(tmp_path):
    with pytest.raises(RuntimeError, match='empty'):
        PACKAGE.payload_manifest(tmp_path)


def test_clean_environment_removes_developer_paths(tmp_path):
    with mock.patch.dict(
        os.environ,
        {
            'LD_LIBRARY_PATH': '/developer/lib',
            'DYLD_LIBRARY_PATH': '/developer/lib',
            'QML_IMPORT_PATH': '/developer/qml',
            'QT_PLUGIN_PATH': '/developer/plugins',
            'EDI_CODEX_DEVELOPMENT_EXECUTABLE': '/developer/codex',
            'PYTHONPATH': '/developer/python',
            'CONDA_PREFIX': '/developer/env',
            'PIXI_PROJECT_ROOT': '/developer/project',
        },
    ):
        env = PACKAGE.clean_environment(tmp_path)
    assert not any('/developer' in value for value in env.values())
    assert env['CODEX_HOME'] == str(tmp_path / 'codex')
    assert env['HOME'] == str(tmp_path)


@pytest.mark.parametrize(
    'output',
    [
        'libQt6Core.so.6 => /developer/env/lib/libQt6Core.so.6 (0x123)',
        'libQt6Core.so.6 => not found',
    ],
)
def test_dependency_check_refuses_missing_or_external_library(tmp_path, output):
    (tmp_path / 'app').write_bytes(b'\x7fELFpayload')
    result = subprocess.CompletedProcess([], 0, output, '')
    with (
        mock.patch.object(PACKAGE.subprocess, 'run', return_value=result),
        pytest.raises(RuntimeError, match='dependency'),
    ):
        PACKAGE.check_linux_dependencies(tmp_path, {})


def test_dependency_check_allows_packaged_and_system_libraries(tmp_path):
    (tmp_path / 'app').write_bytes(b'\x7fELFpayload')
    result = subprocess.CompletedProcess(
        [],
        0,
        f'libQt6Core.so.6 => {tmp_path}/libQt6Core.so.6 (0x123)\n'
        'libc.so.6 => /usr/lib/libc.so.6 (0x456)',
        '',
    )
    with mock.patch.object(PACKAGE.subprocess, 'run', return_value=result):
        assert 'app' in PACKAGE.check_linux_dependencies(tmp_path, {})


def test_installer_workspace_preserves_the_app_toolchain_pins():
    root = Path(__file__).resolve().parents[3]
    app = tomllib.loads((root / 'pixi.toml').read_text())['feature']['app']
    installer = tomllib.loads((root / 'tools/installer/pixi.toml').read_text())
    for module in ['qt6-main', 'qt6-graphs', 'qt6-quick3d', 'libvulkan-headers']:
        assert installer['dependencies'][module] == app['dependencies'][module]
    for platform in ['linux-64', 'osx-arm64']:
        for name, specification in app['target'][platform]['dependencies'].items():
            assert installer['target'][platform]['dependencies'][name] == specification


@pytest.mark.parametrize('version', ['../escape', '2026.11.0\n', '1;command', ''])
def test_invalid_version_cannot_escape_installer_output(tmp_path, version):
    with pytest.raises(RuntimeError, match='numeric components'):
        PACKAGE.package_app(tmp_path, tmp_path, tmp_path / 'output', version)
    assert not (tmp_path / 'output').exists()


def test_future_mirror_is_configured_without_enabling_an_empty_repository(tmp_path):
    config, meta = tmp_path / 'config', tmp_path / 'meta'
    config.mkdir()
    meta.mkdir()
    urls = PACKAGE.repository_urls('testing')
    PACKAGE.write_metadata(config, meta, '2026.11.0', urls[0], urls[1:])
    xml = ElementTree.parse(config / 'config.xml')
    repositories = xml.findall('RemoteRepositories/Repository')
    assert repositories[0].findtext('Enabled') == '1'
    assert repositories[1].findtext('Url').startswith('https://download.easydiffraction.org/')
    assert repositories[1].findtext('Enabled') == '0'


def test_download_archive_keeps_bootstrap_libraries_and_permissions(tmp_path):
    if PACKAGE.SYSTEM != 'linux':
        pytest.skip('Linux bootstrap layout')
    installer = tmp_path / 'EasyDiffraction.run'
    installer.write_bytes(b'installer')
    installer.chmod(0o755)
    runtime = tmp_path / 'installer-runtime'
    (runtime / 'lib').mkdir(parents=True)
    (runtime / 'lib/library.so').write_bytes(b'portable dependency')
    archive = PACKAGE.archive_installer(installer, runtime)
    unpacked = PACKAGE.unpack_installer(archive, tmp_path / 'download')
    assert unpacked.read_bytes() == b'installer'
    assert unpacked.stat().st_mode & 0o111 == 0o111
    assert (
        unpacked.parent / 'installer-runtime/lib/library.so'
    ).read_bytes() == b'portable dependency'


def test_installer_runtime_refuses_an_unavailable_dependency(tmp_path):
    result = subprocess.CompletedProcess([], 0, 'libmissing.so.1 => not found\n', '')
    with (
        mock.patch.object(PACKAGE.subprocess, 'run', return_value=result),
        pytest.raises(RuntimeError, match='Unresolved installer dependency'),
    ):
        PACKAGE.collect_linux_installer_libraries(
            tmp_path / 'base', tmp_path, None, 'patchelf', {}
        )


def test_installer_runtime_leaves_the_system_c_library_on_the_host(tmp_path):
    result = subprocess.CompletedProcess([], 0, 'libc.so.6 => /lib/libc.so.6 (0x123)\n', '')
    with mock.patch.object(PACKAGE.subprocess, 'run', return_value=result):
        assert (
            PACKAGE.collect_linux_installer_libraries(
                tmp_path / 'base', tmp_path, None, 'patchelf', {}
            )
            == {}
        )
    assert not list(tmp_path.iterdir())


@pytest.mark.parametrize('damage', ['replace', 'add', 'remove', 'link'])
def test_deployment_gate_rejects_runtime_byte_or_membership_changes(tmp_path, damage):
    spec = importlib.util.spec_from_file_location(
        'installer_build', PACKAGE.ROOT / 'tools/installer/build.py'
    )
    build = importlib.util.module_from_spec(spec)
    with mock.patch.dict(sys.modules, {'package': PACKAGE, 'audit': AUDIT}):
        spec.loader.exec_module(build)
    root = tmp_path / (
        'EasyDiffraction.app/Contents/libexec/edi/codex'
        if PACKAGE.SYSTEM == 'macos'
        else 'libexec/edi/codex'
    )
    root.mkdir(parents=True)
    member = root / 'helper'
    member.write_bytes(b'upstream bytes')
    expected = tmp_path / 'expected.json'
    expected.write_text('{"helper": "' + PACKAGE.sha256(member) + '"}')
    build.verify_assistant_payload(tmp_path, expected)
    if damage == 'replace':
        member.write_bytes(b'resigned bytes')
    elif damage == 'add':
        (root / 'unverified-helper').write_bytes(b'extra')
    elif damage == 'remove':
        member.unlink()
    else:
        (root / 'alias').symlink_to('helper')
    with pytest.raises(RuntimeError, match=r'runtime|empty'):
        build.verify_assistant_payload(tmp_path, expected)


@pytest.mark.parametrize('fault', ['none', 'checksum', 'escape'])
def test_pinned_license_acquisition_is_independent_of_the_package_cache(tmp_path, fault):
    archive = tmp_path / 'recorded.conda'
    info = io.BytesIO()
    with tarfile.open(fileobj=info, mode='w:zst') as tar:
        member = tarfile.TarInfo(
            'info/licenses/../../escape' if fault == 'escape' else 'info/licenses/LICENSE'
        )
        member.size = len(b'licence text')
        tar.addfile(member, io.BytesIO(b'licence text'))
    with zipfile.ZipFile(archive, 'w') as zipped:
        zipped.writestr('info-example.tar.zst', info.getvalue())
    metadata = {
        'name': 'example',
        'url': 'https://conda.anaconda.org/conda-forge/linux-64/example.conda',
        'sha256': '0' * 64 if fault == 'checksum' else PACKAGE.sha256(archive),
    }
    target = tmp_path / 'licenses'
    with mock.patch.object(
        PACKAGE.urllib.request, 'urlopen', side_effect=lambda *_args, **_kwargs: archive.open('rb')
    ):
        if fault == 'none':
            PACKAGE.acquire_package_licenses(metadata, tmp_path, target)
            assert (target / 'LICENSE').read_bytes() == b'licence text'
        else:
            with pytest.raises(RuntimeError, match=r'checksum|unsafe'):
                PACKAGE.acquire_package_licenses(metadata, tmp_path, target)
    assert not (tmp_path / 'escape').exists()


@pytest.mark.parametrize('recovered', [False, True])
def test_packaging_uses_acquired_licenses_when_the_original_cache_is_absent(tmp_path, recovered):
    prefix = tmp_path / 'prefix'
    (prefix / 'conda-meta').mkdir(parents=True)
    source = prefix / 'lib/portable.so'
    source.parent.mkdir()
    source.write_bytes(b'portable library')
    (prefix / 'conda-meta/portable.json').write_text(
        '{"name":"portable","files":["lib/portable.so"],"link":{"source":"missing-cache"}}'
    )
    acquired, notices = tmp_path / 'acquired', tmp_path / 'notices'
    notices.mkdir()
    if recovered:
        (acquired / 'portable').mkdir(parents=True)
        (acquired / 'portable/LICENSE').write_text('portable licence')
        PACKAGE.installer_runtime_notices({'portable.so': str(source)}, prefix, notices, acquired)
        assert (notices / 'portable/LICENSE').read_text() == 'portable licence'
    else:
        with pytest.raises(RuntimeError, match='No dependency licence'):
            PACKAGE.installer_runtime_notices(
                {'portable.so': str(source)}, prefix, notices, acquired
            )


@pytest.mark.parametrize(
    'name', ['libQt6WebEngineCore.so.6', 'Qt6Multimedia.dll', 'QtWebEngineCore']
)
def test_bundle_audit_rejects_unrelated_native_qt_components(tmp_path, name):
    (tmp_path / name).write_bytes(b'\x7fELFunneeded module')
    with pytest.raises(RuntimeError, match='Unused Qt component'):
        AUDIT.audit_bundle(tmp_path)


def test_bundle_audit_counts_one_library_and_keeps_required_widgets(tmp_path):
    library = tmp_path / 'libQt6Widgets.so.6'
    library.write_bytes(b'\x7fELFmath text dependency')
    (tmp_path / 'alias').symlink_to(library.name)
    result = AUDIT.audit_bundle(tmp_path)
    assert result['regular_file_bytes'] == library.stat().st_size
    assert result['qt_modules'] == [library.name]
