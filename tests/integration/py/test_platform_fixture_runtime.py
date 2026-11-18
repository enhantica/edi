"""Host-independent controls for native tool selection and exact source manifest transport."""

import hashlib
import json
import os
import subprocess
from pathlib import Path, PureWindowsPath
from types import SimpleNamespace

import pytest

from tests.fixtures import native_process, node_runtime
from tests.fixtures.example_catalogue.retained_bytes import retained_bytes

ROOT = Path(__file__).resolve().parents[3]


def test_windows_node_uses_the_interpreter_environment_root(tmp_path, monkeypatch):
    monkeypatch.setattr(node_runtime, 'os', SimpleNamespace(name='nt'))
    monkeypatch.setattr(node_runtime, 'sys', SimpleNamespace(prefix=str(tmp_path)))
    assert node_runtime.environment_node() == tmp_path / 'node.exe', (
        'Windows Node belongs to the active interpreter prefix '
        'rather than its POSIX bin subdirectory'
    )


def test_windows_shell_selects_git_bash_and_never_the_wsl_launcher(tmp_path, monkeypatch):
    git = tmp_path / 'Git with spaces/cmd/git.exe'
    bash = git.parent.parent / 'bin/bash.exe'
    wsl = tmp_path / 'Windows/System32/bash.exe'
    for path in [git, bash, wsl]:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(b'authored executable-path control')
    monkeypatch.setattr(
        native_process, 'os', SimpleNamespace(name='nt', environ={'BASH': str(wsl)})
    )
    monkeypatch.setattr(native_process, 'shutil', SimpleNamespace(which=lambda _name: str(git)))
    native_process.environment_bash.cache_clear()
    try:
        assert native_process.environment_bash() == str(bash.resolve()), (
            'Windows fixtures select the actual Git installation shell '
            'despite a visible WSL launcher'
        )
        bash.unlink()
        native_process.environment_bash.cache_clear()
        with pytest.raises(RuntimeError, match='WSL is not a Git Bash fallback'):
            native_process.environment_bash()
    finally:
        native_process.environment_bash.cache_clear()


@pytest.mark.parametrize('shape', ['path', 'string'])
def test_windows_manifest_keys_retain_the_entire_reviewed_pin_and_reject_byte_changes(
    shape, monkeypatch
):
    records = json.loads(
        (ROOT / 'tests/fixtures/example_catalogue/retention-adaptations.json').read_text()
    )['files']
    name = 'docs/user/cli/pd-neut-tof_ncaf-wish-2bank_start-3/expected.json'
    row = records[name]
    windows = PureWindowsPath(name)
    key = windows if shape == 'path' else str(windows)
    raw = (ROOT / name).read_bytes()
    from tools.checks import case_records  # noqa: PLC0415 - exercise path serialization separately

    with monkeypatch.context() as patch:
        patch.setattr(case_records, 'CLI_DIR', PureWindowsPath('docs/user/cli'))
        assert (
            case_records.tutorials('authored-case')['cli_docs']
            == 'docs/user/cli/authored-case/index.md'
        ), 'Windows interface records use portable repository paths instead of native separators'
    assert retained_bytes(key, raw) == row['before'].encode('utf-8'), (
        'Windows path transport must reach the same whole-file reviewed '
        'source adaptation as POSIX keys'
    )
    with pytest.raises(
        AssertionError,
        match=r'^A seed update first authenticates every current scientific and metadata byte$',
    ):
        retained_bytes(key, raw + b' ')


def test_windows_native_consumer_uses_release_executable_and_honours_exact_override(
    tmp_path, monkeypatch
):
    from tests.integration.py import test_magnetic_native_consumers as consumer  # noqa: PLC0415

    binary = tmp_path / 'build/ci-consumer/core/Release/edi_integration_tests.exe'
    binary.parent.mkdir(parents=True)
    binary.write_bytes(b'authored binary-path control, not a consumer execution')
    monkeypatch.setattr(consumer, 'ROOT', tmp_path)
    monkeypatch.setattr(consumer, 'os', SimpleNamespace(name='nt', environ={}))
    assert consumer.native_consumers.__wrapped__() == binary, (
        'The Windows multi-config consumer uses its native executable suffix and Release directory'
    )
    prefix = tmp_path / 'old environment'
    needed = tmp_path / 'compiler tools'
    environment = {
        'PATH': os.pathsep.join([str(prefix), str(prefix / 'Scripts'), str(needed), str(needed)]),
        'KEEP': 'unchanged',
    }
    monkeypatch.setattr(
        native_process,
        'os',
        SimpleNamespace(name='nt', environ=environment, pathsep=os.pathsep, path=os.path),
    )
    monkeypatch.setattr(native_process, 'sys', SimpleNamespace(prefix=str(prefix)))
    cleaned = native_process.fresh_pixi_environment()
    assert cleaned == {'PATH': str(needed), 'KEEP': 'unchanged'}, (
        'Fresh Pixi activation removes old prefix and duplicate paths but keeps compiler tools'
    )
    assert environment['PATH'].count(str(needed)) == 2, (
        'Preparing the child activation must leave the original parent environment untouched'
    )
    library = binary.parent / 'edi_core.lib'
    library.write_bytes(b'authored archive-path control, not compiled content')
    assert (
        native_process.native_static_library(library.parent.parent / 'libedi_core.a') == library
    ), 'The Windows native archive uses its .lib name in the actual Release configuration'
    assert native_process.native_static_library(library) == library, (
        'Selecting an already native library path preserves its exact filename'
    )
    consumer.os.environ['EDI_MAGNETIC_INTEGRATION_TEST_EXE'] = str(tmp_path / 'missing.exe')
    with pytest.raises(AssertionError, match='missing downstream consumer is a failure'):
        consumer.native_consumers.__wrapped__()
    reflection_observer_controls(tmp_path, monkeypatch)


def reflection_observer_controls(tmp_path, monkeypatch):
    from tests.integration.py import (  # noqa: PLC0415 - exercise the actual fixture callers
        test_reflection_admission as admission,
    )
    from tests.integration.py import (  # noqa: PLC0415 - prior-art observer fixture
        test_single_crystal_empty as empty,
    )
    from tests.system.py import test_single_crystal_edges as edges  # noqa: PLC0415

    for module in (admission, empty, edges):
        directory = tmp_path / module.__name__.split('.')[-1]
        binding = SimpleNamespace(_edi=SimpleNamespace(__file__=directory / 'python/edi/_edi.pyd'))
        digest = hashlib.sha256(
            (ROOT / 'tests/fixtures/single_crystal_edges/probe.cpp').read_bytes()
        ).hexdigest()
        for configuration in ('single', 'multi'):
            folder = directory / 'single_crystal_edges'
            if configuration == 'multi':
                folder /= 'Release'
            binary = folder / 'single_crystal_edge_probe.exe'
            binary.parent.mkdir(parents=True, exist_ok=True)
            binary.write_bytes(b'authored native-path control; not an executed model')
            calls = []

            def identity(command, *, binary=binary, digest=digest, calls=calls, **_kwargs):
                assert command == [str(binary), '--identity'], (
                    'Each reflection fixture must authenticate '
                    'the exact selected native executable'
                )
                calls.append(command)
                return digest + '\n'

            with monkeypatch.context() as patch:
                patch.setattr(native_process, 'os', SimpleNamespace(name='nt'))
                patch.setattr(module, 'subprocess', SimpleNamespace(check_output=identity))
                if module is admission:
                    patch.setattr(
                        module,
                        'importlib',
                        SimpleNamespace(import_module=lambda _name, binding=binding: binding),
                    )
                else:
                    patch.setattr(module, 'engine', lambda binding=binding: binding)
                if module is not edges:
                    patch.setattr(module, 'os', SimpleNamespace(environ={}))
                assert module.native.__wrapped__() == binary, (
                    'All reflection observers must resolve Windows exe and Release layouts '
                    'through their actual fixture entry points'
                )
                assert len(calls) == 1, (
                    'Native path admission must reach the complete-source identity check once'
                )
                patch.setattr(
                    module, 'subprocess', SimpleNamespace(check_output=lambda *_a, **_k: 'stale')
                )
                with pytest.raises(AssertionError, match=r'prepared.*match'):
                    module.native.__wrapped__()
                patch.setattr(module, 'subprocess', SimpleNamespace(check_output=identity))
                if module is not edges:
                    module.os.environ['SINGLE_CRYSTAL_EMPTY_OBSERVER'] = str(binary)
                    assert module.native.__wrapped__() == binary, (
                        'An explicit observer path is used exactly and retains identity validation'
                    )
                    module.os.environ['SINGLE_CRYSTAL_EMPTY_OBSERVER'] = str(
                        directory / 'missing-override.exe'
                    )
                    with pytest.raises(AssertionError, match=r'require.*prepared'):
                        module.native.__wrapped__()
                    module.os.environ.clear()
                binary.unlink()
                with pytest.raises(AssertionError, match=r'require.*prepared|must be prepared'):
                    module.native.__wrapped__()


def test_authored_python_spy_reaches_declared_and_refused_argv_without_an_ambient_tool(tmp_path):
    directory = tmp_path / 'fixture commands'
    directory.mkdir()
    program = directory / 'fixture-read'
    ambient = tmp_path / 'ambient'
    ambient.mkdir()
    foreign = ambient / 'fixture-read'
    foreign.write_text('#!/bin/sh\nexit 91\n', newline='\n')
    foreign.chmod(0o755)
    native_process.python_program(
        program,
        'import sys\nprint("FIXTURE_ARGV", repr(sys.argv[1:]))\n'
        'sys.exit(0 if sys.argv[1:] == ["--declared", "value with spaces"] else 64)\n',
    )
    for arguments, expected in [(['--declared', 'value with spaces'], 0), (['--unknown'], 64)]:
        result = subprocess.run(
            native_process.fixture_shell(
                directory,
                'test "$(command -v fixture-read)" = "$fixture_bin/fixture-read" || exit 92; '
                'fixture-read "$@"',
            )
            + arguments,
            env={**os.environ, 'PATH': str(ambient) + os.pathsep + os.environ['PATH']},
            capture_output=True,
            text=True,
            check=False,
            timeout=3,
        )
        assert result.returncode == expected and 'FIXTURE_ARGV' in result.stdout, (
            'The authored Python transport must receive exact argv on both admission and refusal'
        )
        assert repr(arguments) in result.stdout, (
            'Interpreter selection must preserve spaces, options and the complete addressed argv'
        )
