"""Windows SDK reader protocols retain identity, qualification, runtime and ABI boundaries."""

import importlib.util
import os
import sys
import tarfile
from pathlib import Path
from types import SimpleNamespace

import pytest

from tests.fixtures.untested_sdk.generate import make as make_posix
from tests.fixtures.untested_sdk.generate import write_manifest as write_posix_manifest
from tests.fixtures.windows_native_sdk import make, write_manifest

ROOT = Path(__file__).resolve().parents[3]


@pytest.fixture
def reader():
    spec = importlib.util.spec_from_file_location(
        'windows_sdk_reader', ROOT / 'tools/ci/crysta_sdk.py'
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def check(reader, prefix, repo):
    return reader.check(
        prefix, 'win-64', lockfile=repo / 'installer.lock', environment='installer'
    )


def test_windows_reader_uses_explicit_installer_lock_and_exact_qualified_layout(
    reader, tmp_path, monkeypatch
):
    prefix, repo, manifest = make(tmp_path)
    monkeypatch.setattr(reader, 'ROOT', repo)
    monkeypatch.delenv('MACOSX_DEPLOYMENT_TARGET', raising=False)
    assert check(reader, prefix, repo) == manifest, (
        'The explicit installer lock admits every true .lib/.exe and mixed-case DLL payload'
    )
    with pytest.raises(reader.RefusedError):
        reader.check(prefix, 'win-64', lockfile=repo / 'installer.lock', environment='default')
    with pytest.raises(reader.RefusedError):
        reader.check(prefix, 'win-64', environment='installer')


@pytest.mark.parametrize(
    'defect',
    [
        'missing-library',
        'missing-cli',
        'changed-library',
        'changed-dll',
        'unhashed-dll',
        'missing-dll',
        'unsafe-dll-path',
        'case-alias-hash',
        'missing-package',
        'duplicate-package',
        'wrong-build',
        'wrong-compiler',
        'wrong-architecture',
        'wrong-crt',
        'bad-compiler-version',
        'incomplete-cpp',
        'incomplete-corpus',
        'boolean-cpp-counts',
        'floating-passed-count',
    ],
)
def test_windows_reader_refuses_unproved_runtime_abi_and_qualification(  # noqa: PLR0912
    reader, tmp_path, monkeypatch, defect
):
    prefix, repo, manifest = make(tmp_path)
    monkeypatch.delenv('EDI_ALLOW_UNTESTED_SDK', raising=False)
    if defect == 'missing-library':
        (prefix / 'lib/crysta_core.lib').unlink()
    elif defect == 'missing-cli':
        (prefix / 'bin/crysta.exe').unlink()
    elif defect == 'changed-library':
        (prefix / 'lib/crysta_core.lib').write_bytes(b'not qualified')
    elif defect == 'changed-dll':
        (prefix / 'bin/VCOMP140.DLL').write_bytes(b'not qualified')
    elif defect == 'unhashed-dll':
        (prefix / 'bin/hidden.DLL').write_bytes(b'unrecorded runtime')
    elif defect == 'missing-dll':
        (prefix / 'bin/MSVCP140.dll').unlink()
    elif defect == 'unsafe-dll-path':
        manifest['tested']['sha256']['bin/../escape.dll'] = '0' * 64
    elif defect == 'case-alias-hash':
        manifest['tested']['sha256']['bin/vcomp140.dll'] = manifest['tested']['sha256'].pop(
            'bin/VCOMP140.DLL'
        )
    elif defect == 'missing-package':
        manifest['fingerprint']['packages'].pop()
    elif defect == 'duplicate-package':
        manifest['fingerprint']['packages'].append(dict(manifest['fingerprint']['packages'][0]))
    elif defect == 'wrong-build':
        manifest['fingerprint']['packages'][0]['build'] = 'other_build'
    elif defect.startswith('wrong-') or defect == 'bad-compiler-version':
        key, value = {
            'wrong-compiler': ('id', 'Clang'),
            'wrong-architecture': ('architecture', 'ARM64'),
            'wrong-crt': ('runtime', 'MultiThreaded'),
            'bad-compiler-version': ('version', 'unknown'),
        }[defect]
        manifest['fingerprint']['compiler'][key] = value
    elif defect == 'incomplete-cpp':
        manifest['tested']['cpp_tier']['passed'] = 6
    elif defect == 'incomplete-corpus':
        manifest['tested']['corpus']['passed'] = 2
    elif defect == 'boolean-cpp-counts':
        manifest['tested']['cpp_tier'] = {'passed': True, 'total': True}
    else:
        manifest['tested']['cpp_tier'] = {'passed': 7.0, 'total': 7}
    write_manifest(prefix, manifest)
    with pytest.raises(reader.RefusedError):
        check(reader, prefix, repo)


def test_windows_pinned_fetch_refuses_foreign_archive_but_keeps_diagnostic_candidate(
    reader, tmp_path, monkeypatch
):
    prefix, repo, manifest = make(tmp_path)
    monkeypatch.setattr(reader, 'ROOT', repo)
    manifest['source_sha'] = 'b8' * 20
    manifest['identity'] = 'git:' + manifest['source_sha']
    write_manifest(prefix, manifest)
    assert check(reader, prefix, repo) == manifest, (
        'An explicitly requested diagnostic candidate retains its admitted unpinned behavior'
    )
    archives = tmp_path / 'archives'
    archives.mkdir()
    archive = archives / ('crysta-sdk-' + 'a7' * 20 + '-win-64.tar.gz')
    with tarfile.open(archive, 'w:gz') as output:
        for path in prefix.rglob('*'):
            if path.is_file():
                output.add(path, arcname=path.relative_to(prefix))
    monkeypatch.setenv('CRYSTA_SDK_ARCHIVES', str(archives))
    with pytest.raises(reader.RefusedError, match='differs from requested'):
        reader.fetch('win-64')
    assert not (repo / 'build/crysta-sdk' / ('a7' * 20 + '-win-64') / '.sdk-sha256').exists(), (
        'A foreign Windows archive never receives a successful pinned acquisition marker'
    )


def test_windows_acquisition_lock_owns_and_unlocks_the_same_byte_even_on_refusal(
    reader, tmp_path, monkeypatch
):
    calls = []
    module = SimpleNamespace(
        LK_LOCK=7, LK_UNLCK=9, locking=lambda fd, mode, count: calls.append((fd, mode, count))
    )
    monkeypatch.setitem(sys.modules, 'msvcrt', module)
    monkeypatch.setattr(reader, 'os', SimpleNamespace(name='nt', SEEK_END=os.SEEK_END))
    with (
        pytest.raises(RuntimeError, match='independent failed acquisition'),
        reader.acquisition_lock(tmp_path / 'native.lock'),
    ):
        raise RuntimeError('independent failed acquisition')
    assert [row[1:] for row in calls] == [(7, 1), (9, 1)] and calls[0][0] == calls[1][0], (
        'Windows acquires and releases the same byte/descriptor in a finally boundary'
    )
    assert (tmp_path / 'native.lock').read_bytes() == b'0', (
        'The portable acquisition lock supplies its required byte before native locking'
    )


@pytest.mark.parametrize(
    ('sdk_target', 'consumer_target', 'accepted'),
    [
        ('11.0', '14.0', True),
        ('14.0', '11.0', False),
        ('11.0.0', '11.0', True),
        ('11.0', '11.0.0', True),
        ('invalid', '14.0', False),
        ('invalid', 'invalid', False),
        (None, '14.0', False),
        ('11.0', None, False),
        (None, None, False),
    ],
)
def test_macos_target_compatibility_requires_valid_numeric_order(
    reader, tmp_path, monkeypatch, sdk_target, consumer_target, accepted
):
    prefix, repo, _environment, _tree, manifest = make_posix(tmp_path, 'osx-arm64')
    monkeypatch.setattr(reader, 'ROOT', repo)
    monkeypatch.setenv('PIXI_ENVIRONMENT_NAME', 'default')
    if consumer_target is None:
        monkeypatch.delenv('MACOSX_DEPLOYMENT_TARGET', raising=False)
    else:
        monkeypatch.setenv('MACOSX_DEPLOYMENT_TARGET', consumer_target)
    manifest['fingerprint']['macos_deployment_target'] = sdk_target
    write_posix_manifest(prefix, manifest)
    if accepted:
        assert reader.check(prefix, 'osx-arm64') == manifest, (
            'A valid older or semantically equal SDK target remains compatible with its consumer'
        )
    else:
        with pytest.raises(reader.RefusedError):
            reader.check(prefix, 'osx-arm64')
