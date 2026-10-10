"""Desktop authentication and configure recovery from authored subprocess results."""

import importlib.util
import os
import shutil
import subprocess
from pathlib import Path
from types import SimpleNamespace

import pytest

ROOT = Path(__file__).resolve().parents[3]


def sdk_module():
    spec = importlib.util.spec_from_file_location('desk_sdk', ROOT / 'tools/ci/crysta_sdk.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.mark.parametrize('exported', [None, 'GITHUB_TOKEN', 'GH_TOKEN'])
def test_sdk_uses_cli_login_when_no_token_was_exported(monkeypatch, exported):
    module = sdk_module()
    calls = []
    for name in ('GITHUB_TOKEN', 'GH_TOKEN'):
        monkeypatch.delenv(name, raising=False)
    if exported:
        monkeypatch.setenv(exported, 'authored-environment-token')
    monkeypatch.setattr(
        module.shutil, 'which', lambda name: '/authored/gh' if name == 'gh' else None
    )

    def run(argv, **kwargs):
        calls.append((argv, kwargs))
        return SimpleNamespace(returncode=0, stdout='authored-login-token\n')

    monkeypatch.setattr(module.subprocess, 'run', run)
    assert module.token() == (
        'authored-environment-token' if exported else 'authored-login-token'
    ), 'SDK authentication must use an explicit token or the desktop CLI login without an export'
    assert bool(calls) == (exported is None), (
        'An explicit token must avoid an unnecessary CLI subprocess'
    )
    if calls:
        assert calls[0][0] == ['gh', 'auth', 'token'] and 0 < calls[0][1]['timeout'] <= 30, (
            'The desktop login fallback must invoke the CLI token command with a bounded wait'
        )


@pytest.mark.parametrize('failure', ['missing', 'failed', 'empty', 'timeout'])
def test_missing_desktop_login_refuses_without_disclosing_output(monkeypatch, failure):
    module = sdk_module()
    for name in ('GITHUB_TOKEN', 'GH_TOKEN'):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setattr(
        module.shutil, 'which', lambda _name: None if failure == 'missing' else '/authored/gh'
    )

    def run(_argv, **_kwargs):
        if failure == 'timeout':
            raise subprocess.TimeoutExpired('gh', 30, output='private-login-output')
        return SimpleNamespace(
            returncode=1 if failure == 'failed' else 0,
            stdout='' if failure == 'empty' else 'private-login-output',
        )

    monkeypatch.setattr(module.subprocess, 'run', run)
    with pytest.raises(module.RefusedError) as error:
        module.token()
    assert 'private-login-output' not in str(error.value), (
        'SDK authentication refusals must preserve CLI output privacy'
    )


def executable(path, text):
    path.write_text('#!/bin/bash\n' + text)
    path.chmod(0o755)


def test_failed_configure_preserves_attempt_for_next_no_export_build(tmp_path):
    root = tmp_path / 'desk'
    (root / 'tools/ci').mkdir(parents=True)
    shutil.copy2(ROOT / 'tools/ci/app-build.sh', root / 'tools/ci/app-build.sh')
    executable(root / 'tools/ci/build-crysta.sh', 'exit 0\n')
    bin_dir = root / 'bin'
    bin_dir.mkdir()
    executable(
        bin_dir / 'cmake',
        """
if [[ "$1" == --version ]]; then echo 'cmake version authored'; exit 0; fi
if [[ "$1" == --build ]]; then exit 0; fi
printf '%s\\n' "$@" >> configure-arguments.txt
mkdir -p build/app
if [[ ! -f build/app/attempt-proof ]]; then
  echo retained > build/app/attempt-proof
  exit 9
fi
exit 0
""",
    )
    executable(bin_dir / 'c++', 'echo authored-compiler >&2\n')
    prefix = root / 'env'
    (prefix / 'conda-meta').mkdir(parents=True)
    env = os.environ.copy()
    for name in ('EDI_GUI_COMPONENTS_SRC', 'GH_TOKEN', 'GITHUB_TOKEN', 'EDI_CRYSTA_PREFIX', 'CI'):
        env.pop(name, None)
    env.update(PATH=f'{bin_dir}:/usr/bin:/bin', CONDA_PREFIX=str(prefix), CXX=str(bin_dir / 'c++'))
    command = ['bash', 'tools/ci/app-build.sh']
    failed = subprocess.run(
        command, cwd=root, env=env, capture_output=True, text=True, timeout=10, check=False
    )
    assert failed.returncode == 9, (
        'The configure recovery witness must reach its authored first-attempt refusal'
    )
    proof = root / 'build/app/attempt-proof'
    before = proof.stat().st_ino
    retried = subprocess.run(
        command, cwd=root, env=env, capture_output=True, text=True, timeout=10, check=False
    )
    assert retried.returncode == 0 and proof.stat().st_ino == before, (
        'A desktop build must retry a failed configure without '
        'deleting the same-identity attempted tree'
    )
    assert (
        'FETCHCONTENT_SOURCE_DIR_GUI_COMPONENTS'
        not in (root / 'configure-arguments.txt').read_text()
    ), (
        'A normal desktop build must use the default pinned archive '
        'without a source-directory export'
    )


def test_default_gui_fetch_uses_pinned_archive_with_digest_and_deadline(tmp_path):
    modules = tmp_path / 'modules'
    modules.mkdir()
    (modules / 'FetchContent.cmake').write_text("""
function(FetchContent_Declare)
  file(WRITE "${CMAKE_BINARY_DIR}/observed-declaration.txt" "${ARGV}")
endfunction()
function(FetchContent_MakeAvailable)
  message(FATAL_ERROR "observed default archive acquisition")
endfunction()
""")
    program = tmp_path / 'observe.cmake'
    program.write_text(
        f'set(CMAKE_MODULE_PATH "{modules}")\ninclude("{ROOT / "cmake/EdiGuiBase.cmake"}")\n'
    )
    result = subprocess.run(
        ['cmake', '-P', str(program)],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        timeout=10,
        check=False,
    )
    assert result.returncode != 0 and 'observed default archive acquisition' in result.stderr, (
        'The default GUI source observer must reach the real acquisition declaration'
    )
    fields = (tmp_path / 'observed-declaration.txt').read_text().split(';')
    assert fields[fields.index('URL') + 1] == (
        'https://github.com/easyscience/gui-components/archive/'
        'a573a9695e53a0807de197785e12f9facd06da05.tar.gz'
    ), 'Desktop builds must fetch the immutable upstream GUI commit from ADR-0015'
    assert fields[fields.index('URL_HASH') + 1] == (
        'SHA256=df502bdc41f2730531533c9ef81d371ec7db39b04666d54016e65e4a93bb1dba'
    ), 'Desktop GUI acquisition must verify the frozen upstream archive digest'
    assert (
        int(fields[fields.index('INACTIVITY_TIMEOUT') + 1]) > 0
        and int(fields[fields.index('TIMEOUT') + 1]) > 0
    ), 'The default archive acquisition must bound both stalled and total download time'
