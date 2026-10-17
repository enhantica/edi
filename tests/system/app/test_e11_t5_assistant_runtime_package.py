"""Actual pinned package CMake boundary; no vendor executable is ever launched.

Owner53138596a/public consultation98 define layout, digest and executable roles.
The tiny owned project calls the actual committed function/check/install scripts.
"""

from __future__ import annotations

import hashlib
import json
import os
import platform
import shutil
import subprocess
from contextlib import contextmanager
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
VERSION = '0.162.1'
TARGET = 'x86_64-unknown-linux-musl'
DIGEST = '8748f9f8b708b3bc5a52b3f0a1ccddb22e6985f0efb4f45dafa1677e324abe0e'
MEMBERS = [
    'bin/codex-app-server',
    'bin/codex-code-mode-host',
    'codex-path/rg',
    'codex-resources/zsh/bin/zsh',
    'codex-resources/bwrap',
]


def digest(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def cmake(command, log):
    result = subprocess.run(
        ['cmake', *map(str, command)], capture_output=True, text=True, check=False, timeout=25
    )
    log.write_text(result.stdout + result.stderr)
    return result


@pytest.fixture(scope='module')
def package(tmp_path_factory):
    if platform.system() != 'Linux' or platform.machine() not in {'x86_64', 'AMD64'}:
        pytest.skip('PACKAGE qualification: this finite genuine archive witness is Linux x86_64')
    archive = Path(os.environ['EDI_CODEX_TEST_PACKAGE_ARCHIVE'])
    original_stat = archive.stat()
    original_hash = digest(archive)
    assert original_hash == DIGEST, (
        'PACKAGE SETUP: actual archive matches independent release digest'
    )
    owned = tmp_path_factory.mktemp('actual-runtime-package')
    source, build = owned / 'source', owned / 'build'
    source.mkdir()
    (source / 'cmake').mkdir()
    for name in ['assistant_runtime.cmake', 'assistant_runtime_config.hpp.in']:
        shutil.copy2(ROOT / 'cmake' / name, source / 'cmake' / name)
    shutil.copytree(ROOT / 'data/assistant/runtime', source / 'data/assistant/runtime')
    (source / 'CMakeLists.txt').write_text(
        'cmake_minimum_required(VERSION 3.25)\n'
        'project(OwnedPackageBoundary NONE)\n'
        'include(GNUInstallDirs)\n'
        'set(CMAKE_SYSTEM_PROCESSOR x86_64)\n'
        'add_library(edi_app_module INTERFACE)\n'
        'include(${PROJECT_SOURCE_DIR}/cmake/assistant_runtime.cmake)\n'
        'edi_bundle_assistant_runtime()\n'
    )
    cache = source / 'build/deps/codex' / VERSION / TARGET
    cache.mkdir(parents=True)
    cached = cache / 'package.tar.gz'
    # Each mutable boundary owns a real archive copy; upstream remains read-only.
    shutil.copy2(archive, cached)
    configured = cmake(['-S', source, '-B', build], owned / 'configure.log')
    assert configured.returncode == 0, (
        'PACKAGE SETUP: real function configures verified owned package'
    )
    # Existing generated public C++ config identifies the actual owning root;
    # no alternate resolver or product getter is introduced by this consumer.
    config = (build / 'assistant_runtime_config.hpp').read_text()
    line = next(value for value in config.splitlines() if 'EDI_CODEX_RUNTIME_BUILD_DIR ' in value)
    published = Path(line.split('R"(', 1)[1].rsplit(')"', 1)[0])
    assert published.is_relative_to(source), 'PACKAGE SETUP: all mutable runtime members are owned'
    fixture = {
        'owned': owned,
        'source': source,
        'build': build,
        'cache': cache,
        'cached': cached,
        'published': published,
    }
    (owned / 'subject.json').write_text(
        json.dumps(
            {
                'function_sha256': digest(source / 'cmake/assistant_runtime.cmake'),
                'template_sha256': digest(source / 'cmake/assistant_runtime_config.hpp.in'),
                'archive_sha256': original_hash,
                'published': str(published),
            },
            indent=2,
        )
    )
    yield fixture
    after_stat = archive.stat()
    assert digest(archive) == original_hash and (
        after_stat.st_mode,
        after_stat.st_ino,
        after_stat.st_size,
    ) == (original_stat.st_mode, original_stat.st_ino, original_stat.st_size), (
        'PACKAGE: original upstream archive bytes, mode and identity survive every owned mutation'
    )


def check(package, phase, label):
    owned = package['owned']
    if phase == 'build':
        return cmake(
            ['--build', package['build'], '--target', 'edi_assistant_runtime_check'],
            owned / (label + '-build.log'),
        )
    installed = owned / ('installed-' + label)
    result = cmake(
        ['--install', package['build'], '--prefix', installed], owned / (label + '-install.log')
    )
    shutil.rmtree(installed, ignore_errors=True)
    return result


@pytest.mark.parametrize('phase', ['build', 'install'])
def test_healthy_genuine_package_passes_actual_generated_boundaries(package, phase):
    assert check(package, phase, 'healthy').returncode == 0, (
        'PACKAGE: complete verified executable closure passes real normal build/install checks'
    )
    manifest = json.loads((package['published'] / 'codex-package.json').read_text())
    assert manifest == {
        'layoutVersion': 1,
        'version': VERSION,
        'target': TARGET,
        'variant': 'codex-app-server',
        'entrypoint': 'bin/codex-app-server',
        'resourcesDir': 'codex-resources',
        'pathDir': 'codex-path',
    }, 'PACKAGE: genuine canonical manifest retains actual version/target/layout relationships'


@contextmanager
def changed_member(path, mutation):
    before_mode = path.stat().st_mode
    backup = path.with_name(path.name + '.original-owned-member')
    if mutation == 'mode':
        path.chmod(0o644)
    else:
        path.rename(backup)
        if mutation == 'symlink':
            path.symlink_to(backup.name)
        else:
            path.mkdir()
    try:
        yield
    finally:
        if mutation == 'mode':
            path.chmod(before_mode)
        else:
            if path.is_symlink():
                path.unlink()
            else:
                path.rmdir()
            backup.rename(path)


@pytest.mark.parametrize('member', MEMBERS)
@pytest.mark.parametrize('mutation', ['mode', 'symlink', 'directory'])
@pytest.mark.parametrize('phase', ['build', 'install'])
def test_bnd1_after_configure_required_helper_predicates_remain_binding(
    package, member, mutation, phase
):
    path = package['published'] / member
    assert path.is_file() and not path.is_symlink() and os.access(path, os.X_OK), (
        'BND1 SETUP: genuine required original is executable before its owned staging mutation'
    )
    with changed_member(path, mutation):
        result = check(package, phase, member.replace('/', '-') + '-' + mutation)
    assert result.returncode != 0, (
        'BND1: post-configure helper execute/type loss must fail actual build and install proof'
    )


def reader_has_members(descriptor):
    # An already-open normal filesystem reader, not a producer marker/test hook.
    try:
        for member in MEMBERS:
            with os.fdopen(os.open(member, os.O_RDONLY, dir_fd=descriptor), 'rb') as stream:
                if not stream.read(1):
                    return False
    except FileNotFoundError:
        return False
    return True


def test_bnd2_unchanged_reconfigure_preserves_already_published_reader(package):
    descriptor = os.open(package['published'], os.O_RDONLY | os.O_DIRECTORY)
    try:
        assert reader_has_members(descriptor), (
            'BND2 SETUP: original reader sees complete valid closure'
        )
        result = cmake(
            ['-S', package['source'], '-B', package['build']],
            package['owned'] / 'unchanged-reconfigure.log',
        )
        assert result.returncode == 0, 'BND2: unchanged verified reconfigure remains successful'
        assert reader_has_members(descriptor), (
            'BND2: unchanged configure preserves the existing dependency for readers'
        )
    finally:
        os.close(descriptor)


def test_bnd2_failed_archive_preparation_retains_prior_valid_publication(package):
    cached = package['cached']
    # This digest mutation uses its own COPY, never the upstream archive.
    backup = cached.with_name('untouched-original-archive.tar.gz')
    cached.rename(backup)
    shutil.copy2(backup, cached)
    with cached.open('r+b') as stream:
        first = stream.read(1)
        stream.seek(0)
        stream.write(bytes([first[0] ^ 1]))
    descriptor = os.open(package['published'], os.O_RDONLY | os.O_DIRECTORY)
    try:
        result = cmake(
            ['-S', package['source'], '-B', package['build']],
            package['owned'] / 'failed-archive-reconfigure.log',
        )
        assert result.returncode != 0, 'BND2 SETUP: real pinned digest rejects owned corrupt copy'
        assert reader_has_members(descriptor), (
            'BND2: failure preparing replacement leaves previously valid published readers intact'
        )
    finally:
        os.close(descriptor)
        cached.unlink()
        backup.rename(cached)
