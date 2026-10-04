# SPDX-License-Identifier: BSD-3-Clause
"""Consumer configure must use locked packages and the SDK's real versions.

Accident paths: installed fleet Eigen masks a hosted-runner failure; a different
find_package silently selects a system copy; the SDK claims a version that its
consumer's configured headers do not implement.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import pytest

from tests.fixtures.locked_configure import (
    configure,
    eigen_version,
    escapes,
    fingerprint_mismatches,
    packages,
)

ROOT = Path(__file__).resolve().parents[3]


@pytest.fixture(params=['system-present', 'system-absent'])
def configured(request, tmp_path_factory):
    return configure(
        ROOT, tmp_path_factory.mktemp('locked-configure'), request.param == 'system-present'
    )


def test_every_resolved_third_party_input_is_inside_locked_prefix(configured):
    result = configured['result']
    assert result.returncode == 0, (
        'Locked dependencies must configure with and without fleet packages: '
        f'{result.stdout}{result.stderr}'
    )
    assert not escapes(configured), (
        'Every third-party C++ package must come from the locked pixi prefix: '
        f'{escapes(configured)}'
    )
    assert eigen_version(configured) == '3.4.0', (
        'The committed Eigen pin must build the owner-selected 3.4.0 headers'
    )
    includes = [p for _, p in configured['paths'] if (p / 'Eigen/Core').is_file()]
    assert all(p.resolve().is_relative_to(configured['prefix']) for p in includes), (
        'A fallback or an apparent prefix symlink must not replace the locked Eigen package'
    )


def test_sdk_fingerprint_equals_configured_dependencies(configured):
    result = configured['result']
    assert result.returncode == 0, (
        f'SDK accuracy needs a real completed consumer configure: {result.stdout}{result.stderr}'
    )
    manifest = json.loads((configured['sdk'] / 'share/crysta-sdk/manifest.json').read_text())
    assert not fingerprint_mismatches(configured, manifest), (
        'SDK versions must equal actual configured inputs: '
        f'{fingerprint_mismatches(configured, manifest)}'
    )


def test_dependency_escape_observer_closes_paths_and_symlink_redirects(tmp_path):
    prefix, outside = tmp_path / 'prefix', tmp_path / 'system'
    prefix.mkdir()
    outside.mkdir()
    (prefix / 'redirect').symlink_to(outside, target_is_directory=True)
    observed = {
        'prefix': prefix,
        'root': tmp_path / 'source',
        'scratch': tmp_path / 'build',
        'sdk': None,
        'paths': [('OtherPackage_DIR', outside), ('OtherPackage:include', prefix / 'redirect')],
    }
    assert len(escapes(observed)) == 2, (
        'Dependency escape detection must reject another package and a symlink into the system'
    )
    observed['paths'] = [('CMAKE_CXX_COMPILER', observed['root'] / 'copied-compiler')]
    observed['cache'] = {'CMAKE_CXX_COMPILER': ('FILEPATH', 'copied-compiler')}
    assert escapes(observed), (
        'A compiler copied into the source checkout must not impersonate the locked toolchain'
    )
    observed['paths'] = [('OtherPackage_DIR', prefix)]
    assert not escapes(observed), (
        'The dependency observer must admit an actual locked-prefix package'
    )


@pytest.mark.parametrize('form', ['package-path', 'symlink-path', 'typed-cache'])
def test_real_configure_observer_catches_an_added_external_package(tmp_path, form):
    external = tmp_path / 'external package'
    external.mkdir()
    (external / 'GateDependencyConfig.cmake').write_text(
        'add_library(GateDependency::headers INTERFACE IMPORTED)\nset(GateDependency_FOUND TRUE)\n'
    )
    selected = external
    if form == 'symlink-path':
        selected = tmp_path / 'redirect'
        selected.symlink_to(external, target_is_directory=True)
    hook = tmp_path / 'observe-added-package.cmake'
    hook.write_text(
        'find_package(GateDependency CONFIG REQUIRED PATHS "'
        + selected.as_posix()
        + '" NO_DEFAULT_PATH)\n'
    )
    extra = ['-DCMAKE_PROJECT_INCLUDE=' + hook.as_posix()]
    if form == 'typed-cache':
        extra += ['-DGateDependency_DIR:STRING=' + selected.as_posix()]
    observed = configure(ROOT, tmp_path / 'configure', system=False, extra=extra)
    assert any(name == 'GateDependency_DIR' for name, _ in escapes(observed)), (
        'The CMake observer must catch an external package, '
        'symlink redirect, or typed cache override'
    )


def test_fingerprint_observer_rejects_header_version_substitution(tmp_path):
    prefix = Path(os.environ.get('CONDA_PREFIX', sys.prefix)).resolve()
    actual = packages(prefix)['eigen']
    include = tmp_path / 'alien-headers'
    macros = include / 'Eigen/src/Core/util/Macros.h'
    macros.parent.mkdir(parents=True)
    macros.write_text(
        '#define EIGEN_WORLD_VERSION 9\n#define EIGEN_MAJOR_VERSION 7\n'
        '#define EIGEN_MINOR_VERSION 3\n'
    )
    observed = {'prefix': prefix, 'paths': [('Eigen3:include', include)], 'cache': {}}
    manifest = {'fingerprint': {'packages': [actual]}}
    assert 'eigen: manifest differs from configured header macros' in fingerprint_mismatches(
        observed, manifest
    ), (
        'SDK fingerprint comparison must reject substituted headers '
        'beneath matching package metadata'
    )


@pytest.mark.parametrize('system', [True, False], ids=['system-present', 'system-absent'])
def test_app_configure_uses_locked_packages_and_truthful_sdk(tmp_path, monkeypatch, system):
    prefix = ROOT / '.pixi/envs/app'
    if not (prefix / 'bin/cmake').is_file():
        pytest.skip('The app configuration is absent from this native-only environment')
    monkeypatch.setenv('CONDA_PREFIX', str(prefix))
    monkeypatch.setenv('PATH', str(prefix / 'bin') + os.pathsep + os.environ['PATH'])
    # The native gate runs in default; the app configure must not inherit that
    # environment's flags or prefix search list when it selects the app compiler.
    for name in (
        'CMAKE_PREFIX_PATH',
        'LIBRARY_PATH',
        'CPATH',
        'CPLUS_INCLUDE_PATH',
        'C_INCLUDE_PATH',
        'CPPFLAGS',
        'CFLAGS',
        'CXXFLAGS',
        'LDFLAGS',
        'CMAKE_ARGS',
        'CMAKE_TOOLCHAIN_FILE',
        'CONDA_BUILD_SYSROOT',
    ):
        monkeypatch.delenv(name, raising=False)
    for name, fallback in (('CXX', 'c++'), ('CC', 'cc')):
        compiler = prefix / 'bin' / Path(os.environ.get(name, fallback)).name
        if compiler.is_file():
            monkeypatch.setenv(name, str(compiler))
    extra = ['-DEDI_BUILD_APP=ON', '-DEDI_BUILD_BINDINGS=OFF']
    gui = ROOT / 'build/app/_deps/gui_components-src'
    if gui.is_dir():
        extra += ['-DFETCHCONTENT_SOURCE_DIR_GUI_COMPONENTS=' + str(gui)]
    observed = configure(ROOT, tmp_path / 'app-configure', system, extra=extra)
    result = observed['result']
    assert result.returncode == 0, (
        'The actual Qt app configure must work without system packages: '
        f'{result.stdout}{result.stderr}'
    )
    assert not escapes(observed), (
        'Every app and transitive Qt package must be inside its locked prefix: '
        f'{escapes(observed)}'
    )
    manifest = json.loads((observed['sdk'] / 'share/crysta-sdk/manifest.json').read_text())
    assert not fingerprint_mismatches(observed, manifest), (
        'The Qt app must consume the dependency versions the SDK actually records: '
        f'{fingerprint_mismatches(observed, manifest)}'
    )
