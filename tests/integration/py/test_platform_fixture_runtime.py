"""Host-independent controls for native tool selection and exact source manifest transport."""

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
def test_windows_manifest_keys_retain_the_entire_reviewed_pin_and_reject_byte_changes(shape):
    records = json.loads(
        (ROOT / 'tests/fixtures/example_catalogue/retention-adaptations.json').read_text()
    )['files']
    name = 'docs/user/cli/pd-neut-tof_ncaf-wish-2bank_start-3/expected.json'
    row = records[name]
    windows = PureWindowsPath(name)
    key = windows if shape == 'path' else str(windows)
    raw = (ROOT / name).read_bytes()
    assert retained_bytes(key, raw) == row['before'].encode('utf-8'), (
        'Windows path transport must reach the same whole-file reviewed '
        'source adaptation as POSIX keys'
    )
    with pytest.raises(
        AssertionError,
        match=r'exact committed|entire independently archived|every committed source byte',
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
    consumer.os.environ['EDI_MAGNETIC_INTEGRATION_TEST_EXE'] = str(tmp_path / 'missing.exe')
    with pytest.raises(AssertionError, match='missing downstream consumer is a failure'):
        consumer.native_consumers.__wrapped__()


def test_authored_python_spy_reaches_declared_and_refused_argv_without_an_ambient_tool(tmp_path):
    program = tmp_path / 'fixture-read'
    native_process.python_program(
        program,
        'import sys\nprint("FIXTURE_ARGV", repr(sys.argv[1:]))\n'
        'sys.exit(0 if sys.argv[1:] == ["--declared", "value with spaces"] else 64)\n',
    )
    for arguments, expected in [(['--declared', 'value with spaces'], 0), (['--unknown'], 64)]:
        result = subprocess.run(
            [native_process.environment_bash(), str(program), *arguments],
            env=os.environ.copy(),
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
