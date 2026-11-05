# SPDX-License-Identifier: BSD-3-Clause
"""Offline boundary checks for the native installer tool."""

import importlib.util
import io
import json
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
    app = tomllib.loads((root / 'pixi.toml').read_text(encoding='utf-8'))['feature']['app']
    installer = tomllib.loads((root / 'tools/installer/pixi.toml').read_text(encoding='utf-8'))
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
    root = tmp_path / 'libexec/edi/codex'
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
@pytest.mark.parametrize('member_kind', ['info', 'pkg'])
def test_pinned_license_acquisition_is_independent_of_the_package_cache(
    tmp_path, fault, member_kind
):
    archive = tmp_path / 'recorded.conda'
    info = io.BytesIO()
    with tarfile.open(fileobj=info, mode='w:zst') as tar:
        member = tarfile.TarInfo(
            'info/licenses/../../escape' if fault == 'escape' else 'info/licenses/LICENSE'
        )
        member.size = len(b'licence text')
        tar.addfile(member, io.BytesIO(b'licence text'))
    with zipfile.ZipFile(archive, 'w') as zipped:
        zipped.writestr(member_kind + '-example.tar.zst', info.getvalue())
        empty = io.BytesIO()
        with tarfile.open(fileobj=empty, mode='w:zst'):
            pass
        zipped.writestr(
            ('pkg' if member_kind == 'info' else 'info') + '-example.tar.zst', empty.getvalue()
        )
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
        assert (notices / 'portable/LICENSE').read_text(encoding='utf-8') == 'portable licence'
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


def test_windows_clean_environment_accepts_uppercase_systemroot(tmp_path):
    with (
        mock.patch.object(PACKAGE, 'SYSTEM', 'windows'),
        mock.patch.dict(os.environ, {'SYSTEMROOT': str(tmp_path)}, clear=True),
    ):
        env = PACKAGE.clean_environment(tmp_path / 'home')
    assert env['PATH'] == str(tmp_path / 'System32') + os.pathsep + str(tmp_path)


@pytest.mark.parametrize('name', ['libgcc', 'libstdcxx', 'libgomp', 'libfreetype6'])
def test_split_runtime_packages_retain_the_exact_upstream_licenses(tmp_path, name):
    policy = PACKAGE.json.loads(
        (PACKAGE.ROOT / 'tools/installer/licenses/manifest.json').read_text(encoding='utf-8')
    )
    package = policy['packages'][name]
    metadata = {'name': name, 'version': package['version'], 'license': package['license']}
    assert PACKAGE.bundled_runtime_licenses(metadata, tmp_path / 'notices')
    for filename in package['files']:
        assert (
            PACKAGE.sha256(tmp_path / 'notices' / filename) == policy['files'][filename]['sha256']
        )
    metadata['version'] = '999.0.0'
    assert not PACKAGE.bundled_runtime_licenses(metadata, tmp_path / 'wrong-version')
    assert not (tmp_path / 'wrong-version').exists()


def test_installation_lifecycles_have_distinct_real_temp_directories(tmp_path):
    offline = PACKAGE.clean_environment(tmp_path / 'offline')
    online = PACKAGE.clean_environment(tmp_path / 'online')
    assert offline['TEMP'] != online['TEMP']
    for env in [offline, online]:
        assert env['TEMP'] == env['TMP'] == env['TMPDIR']
        assert Path(env['TEMP']).is_dir()


@pytest.mark.parametrize('damage', ['none', 'source', 'history', 'version', 'reused'])
def test_prepared_release_inputs_share_one_identity(tmp_path, damage):
    release = {
        'version': '2026.11.0',
        'commit': 'a' * 40,
        'date': '2026-11-05',
        'notes': {
            'Added': [],
            'Fixed': [{'title': 'Improve fitting', 'pull_request': 1}],
            'Changed': [],
        },
    }
    plan = {
        'version': release['version'],
        'commit': release['commit'],
        'reused': damage == 'reused',
    }
    if damage == 'version':
        plan['version'] = '2026.11.1'
    history = {
        'schema': 'edi.releases/1',
        'baseline_commit': 'b' * 40,
        'releases': [] if damage == 'history' else [release],
    }
    for name, value in [
        ('plan.json', plan),
        ('release.json', release),
        ('release-history.json', history),
    ]:
        (tmp_path / name).write_text(PACKAGE.json.dumps(value))
    if damage == 'none':
        assert PACKAGE.read_release_plan(tmp_path, 'a' * 40) == release
    else:
        with pytest.raises(RuntimeError, match=r'match|uniquely|disagree|already exists'):
            PACKAGE.read_release_plan(tmp_path, 'c' * 40 if damage == 'source' else 'a' * 40)


def test_deployed_licenses_follow_runtime_paths_instead_of_compiler_copies():
    spec = importlib.util.spec_from_file_location(
        'installer_build', PACKAGE.ROOT / 'tools/installer/build.py'
    )
    build = importlib.util.module_from_spec(spec)
    with mock.patch.dict(sys.modules, {'package': PACKAGE, 'audit': AUDIT}):
        spec.loader.exec_module(build)
    records = [
        {'name': 'runtime', 'files': ['lib/libgcc_s.so.1']},
        {'name': 'compiler', 'files': ['lib/gcc/target/14/libgcc_s.so.1']},
        {'name': 'windows', 'files': ['Library/bin/Qt6Core.dll']},
    ]
    assert build.deployed_package_names(
        [Path('lib/libgcc_s.so.1'), Path('bin/Qt6Core.dll')], records
    ) == {'runtime', 'windows'}
    records.append({'name': 'conflict', 'files': ['lib/libgcc_s.so.1']})
    with pytest.raises(RuntimeError, match='Ambiguous'):
        build.deployed_package_names([Path('lib/libgcc_s.so.1')], records)


@pytest.mark.parametrize('damage', ['none', 'package', 'empty', 'missing', 'escape'])
def test_windows_runtime_uses_locked_dlls_and_refuses_invalid_inventory(tmp_path, damage):
    spec = importlib.util.spec_from_file_location(
        'installer_build', PACKAGE.ROOT / 'tools/installer/build.py'
    )
    build = importlib.util.module_from_spec(spec)
    with mock.patch.dict(sys.modules, {'package': PACKAGE, 'audit': AUDIT}):
        spec.loader.exec_module(build)
    prefix = tmp_path / 'prefix'
    metadata = prefix / 'conda-meta'
    metadata.mkdir(parents=True)
    stage = tmp_path / 'stage'
    (stage / 'bin').mkdir(parents=True)
    assistant = stage / 'libexec/edi/codex/helper.dll'
    assistant.parent.mkdir(parents=True)
    assistant.write_bytes(b'official helper')
    for package, dll in [('vc14_runtime', 'msvcp140.dll'), ('vcomp14', 'vcomp140.dll')]:
        member = 'Library/bin/' + dll
        source = prefix / member
        source.parent.mkdir(parents=True, exist_ok=True)
        source.write_bytes(package.encode())
        (stage / 'bin' / dll).write_bytes(b'older runtime')
        inventory = [member, 'Library/include/header.h']
        if package == 'vcomp14':
            if damage == 'package':
                continue
            if damage == 'empty':
                inventory = []
            elif damage == 'missing':
                source.unlink()
            elif damage == 'escape':
                inventory = ['../escape.dll']
        (metadata / (package + '.json')).write_text(
            json.dumps({'name': package, 'files': inventory}), encoding='utf-8'
        )
    if damage == 'none':
        build.copy_windows_compiler_runtime(prefix, stage)
        assert (stage / 'bin/msvcp140.dll').read_bytes() == b'vc14_runtime'
        assert (stage / 'bin/vcomp140.dll').read_bytes() == b'vcomp14'
        assert sorted(path.name for path in (stage / 'bin').iterdir()) == [
            'msvcp140.dll',
            'vcomp140.dll',
        ]
    else:
        with pytest.raises(RuntimeError, match='runtime'):
            build.copy_windows_compiler_runtime(prefix, stage)
    assert assistant.read_bytes() == b'official helper'


@pytest.mark.parametrize('different', [False, True])
def test_windows_runtime_only_coalesces_identical_copies(tmp_path, different):
    stage = tmp_path / 'stage with spaces'
    stage.mkdir()
    shipped = stage / 'msvcp140.dll'
    shipped.write_bytes(b'locked runtime')
    original = tmp_path / 'msvcp140.dll'
    original.write_bytes(b'other runtime' if different else shipped.read_bytes())
    script = tmp_path / 'check.cmake'
    resolver = PACKAGE.ROOT / 'tools/installer/windows-runtime.cmake'
    script.write_text(
        f'include("{resolver.as_posix()}")\n'
        f'set(STAGE "{stage.as_posix()}")\n'
        f'edi_choose_runtime_copy(msvcp140.dll selected "{original.as_posix()}" '
        f'"{shipped.as_posix()}")\n'
        f'if(NOT selected STREQUAL "{shipped.as_posix()}")\n'
        '    message(FATAL_ERROR "Expected the staged path")\n'
        'endif()\n',
        encoding='utf-8',
    )
    result = subprocess.run(['cmake', '-P', script], capture_output=True, text=True, check=False)
    assert (result.returncode != 0) is different, result.stderr
    if different:
        assert 'Different Windows runtime copies found' in result.stderr
