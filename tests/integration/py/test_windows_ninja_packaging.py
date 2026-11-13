"""Explicit packaging Ninja configuration retains its real environment-default semantics."""

import importlib
import importlib.util
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
VARIABLES = ('CMAKE_GENERATOR_PLATFORM', 'CMAKE_GENERATOR_TOOLSET', 'CMAKE_GENERATOR_INSTANCE')


class ConfigurationObservedError(Exception):
    """Stop before any application or scientific compilation starts."""


@pytest.fixture
def builder(monkeypatch):
    monkeypatch.syspath_prepend(str(ROOT / 'tools/installer'))
    spec = importlib.util.spec_from_file_location(
        'ninja_packaging_builder', ROOT / 'tools/installer/build.py'
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def observe_configuration(builder, root, monkeypatch, boundary, system='windows'):
    source, work, qt = root / 'source', root / 'work', root / 'qt'
    (source / 'include/crysta').mkdir(parents=True)
    (source / 'include/crysta/model.hpp').write_text('source identity protocol only')
    (source / 'compiler-checks').mkdir()
    (source / 'compiler-checks/CMakeLists.txt').write_text('source identity protocol only')
    work.mkdir()
    qt.mkdir()
    monkeypatch.setattr(builder, 'SYSTEM', system)
    monkeypatch.setattr(builder, 'resolve_qt_prefix', lambda _qt: qt)
    monkeypatch.setattr(builder, 'acquire_sdk', lambda _source: root / 'qualified-sdk')
    monkeypatch.setattr(
        builder,
        'release_identity',
        lambda *_args: {
            'version': '2026.1.1',
            'plan': None,
            'commit': 'a7' * 20,
        },
    )
    monkeypatch.setattr(builder, 'write_preview_history', lambda *_args: work / 'history.json')
    cli = importlib.import_module('standalone_cli')
    common = []
    monkeypatch.setattr(
        cli, 'build_cli', lambda _sdk, _work, options, *_args: common.extend(options)
    )
    observed = []

    def run(args, **kwargs):
        observed.append(([str(value) for value in args], kwargs.get('env')))
        raise ConfigurationObservedError

    monkeypatch.setattr(builder, 'run', run)
    action = (
        (lambda: builder.check_compiler(source, work))
        if boundary == 'preflight'
        else (lambda: builder.build(source, work, qt, None, '2026.1.1'))
    )
    with pytest.raises(ConfigurationObservedError):
        action()
    assert len(observed) == 1, (
        'Each public packaging entry reaches exactly its first configure boundary'
    )
    if boundary == 'desktop':
        assert common, (
            'Versioned packaging forwards actual shared configure arguments to CLI and wheel'
        )
        assert all(value in observed[0][0] for value in common), (
            'Desktop CLI and wheel receive the identical generator and compiler settings'
        )
    return observed[0]


def real_configure(root, command, selected_environment, contaminated):
    source, tree = root / 'tiny', root / 'configured'
    source.mkdir(parents=True)
    (source / 'CMakeLists.txt').write_text(
        'cmake_minimum_required(VERSION 3.20)\nproject(generator_contract C)\n'
        'file(WRITE "$ENV{PROTOCOL_OUTPUT}" "$ENV{CXX}|$ENV{VSCMD_ARG_TGT_ARCH}")\n'
    )
    command = list(command)
    command[0] = shutil.which(
        'cmake', path=str(Path(sys.executable).parent) + os.pathsep + os.environ['PATH']
    )
    command[command.index('-S') + 1] = str(source)
    command[command.index('-B') + 1] = str(tree)
    environment = {
        **(os.environ if selected_environment is None else selected_environment),
        'PATH': str(Path(sys.executable).parent) + os.pathsep + os.environ['PATH'],
        'CMAKE_GENERATOR': 'Ninja',
        'CXX': 'independent-compiler.exe',
        'VSCMD_ARG_TGT_ARCH': 'x64',
        'PROTOCOL_OUTPUT': str(root / 'observed.txt'),
    }
    for name in VARIABLES:
        environment.pop(name, None)
    environment.update(dict.fromkeys(contaminated, 'unsupported-independent-value'))
    return subprocess.run(
        command, env=environment, capture_output=True, text=True, check=False, timeout=10
    )


@pytest.mark.parametrize('boundary', ['preflight', 'desktop'])
@pytest.mark.parametrize('contaminated', [(name,) for name in VARIABLES] + [VARIABLES])
def test_every_installer_explicit_ninja_boundary_ignores_inherited_vs_defaults(
    builder,
    tmp_path,
    monkeypatch,
    boundary,
    contaminated,
):
    command, environment = observe_configuration(
        builder, tmp_path / 'entry', monkeypatch, boundary
    )
    assert command[command.index('-G') + 1] == 'Ninja', (
        'All native packaging entries explicitly select their existing Ninja generator'
    )
    result = real_configure(tmp_path / 'good', command, environment, contaminated)
    assert result.returncode == 0, (
        'The actual installer configure arguments reach valid real Ninja configuration'
    )
    assert (tmp_path / 'good/observed.txt').read_text() == 'independent-compiler.exe|x64', (
        'Generator cleanup retains the selected compiler and architecture environment'
    )
    if boundary == 'desktop':
        cache = (tmp_path / 'good/configured/CMakeCache.txt').read_text()
        assert 'CMAKE_MSVC_RUNTIME_LIBRARY:UNINITIALIZED=MultiThreadedDLL' in cache, (
            'Installer generator cleanup preserves the shared dynamic release CRT selection'
        )
    position = command.index('-G')
    escaped = command[:position] + command[position + 2 :]
    result = real_configure(tmp_path / 'escape', escaped, environment, contaminated)
    assert result.returncode != 0, (
        'Removing explicit generator selection exposes actual inherited VS-only conflicts'
    )


@pytest.mark.parametrize('system', ['linux', 'macos'])
@pytest.mark.parametrize('boundary', ['preflight', 'desktop'])
def test_windows_generator_cleanup_does_not_change_other_platform_settings(
    builder,
    tmp_path,
    monkeypatch,
    system,
    boundary,
):
    command, _environment = observe_configuration(builder, tmp_path, monkeypatch, boundary, system)
    assert all('-D' + name + '=' not in command for name in VARIABLES), (
        'Existing Linux and macOS configure policies retain their own platform settings'
    )
