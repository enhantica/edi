"""Desktop authentication and configure recovery from authored subprocess results."""

import importlib.util
import os
import shutil
import subprocess
from pathlib import Path

import pytest

from tests.integration.py.test_e04_t1_app_contract import GUI_ARCHIVE_SHA256, GUI_PIN

ROOT = Path(__file__).resolve().parents[3]


def sdk_module():
    spec = importlib.util.spec_from_file_location('desk_sdk', ROOT / 'tools/ci/crysta_sdk.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.mark.parametrize('exported', [None, 'GITHUB_TOKEN', 'GH_TOKEN'])
def test_qualified_desk_sdk_needs_no_exported_or_cli_login(tmp_path, exported):
    from tests.integration.py.test_e09_t75_sdk_consumer import consumer  # noqa: PLC0415

    env, root, _ = consumer(tmp_path, prepare_only=True)
    if exported:
        env[exported] = 'private-synthetic-token'
    result = subprocess.run(
        ['bash', str(root / 'tools/ci/build-crysta.sh')],
        cwd=root,
        env=env,
        capture_output=True,
        text=True,
        check=False,
        timeout=10,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert not (tmp_path / 'commands').exists(), (
        'ADR-0083: a qualified local SDK never calls gh, curl, Git or a compiler'
    )
    assert 'private-synthetic-token' not in result.stdout + result.stderr


@pytest.mark.parametrize('login', ['missing', 'failed', 'empty', 'timeout'])
def test_unusable_login_is_irrelevant_to_a_qualified_local_sdk(tmp_path, login):
    from tests.integration.py.test_e09_t75_sdk_consumer import consumer  # noqa: PLC0415

    env, root, _ = consumer(tmp_path, prepare_only=True)
    gh = tmp_path / 'bin/gh'
    if login == 'missing':
        gh.unlink()
    else:
        # Any invocation is forbidden, irrespective of what the obsolete login
        # path would return; no artificial timeout or sleep is needed.
        gh.write_text('#!/bin/sh\necho forbidden > "$SDK_COMMANDS"\nexit 91\n')
    result = subprocess.run(
        ['bash', str(root / 'tools/ci/build-crysta.sh')],
        cwd=root,
        env=env,
        capture_output=True,
        text=True,
        check=False,
        timeout=10,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert not (tmp_path / 'commands').exists(), 'SDK-only consumption must not try authentication'


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


def assert_default_gui_fetch(fields):
    for name in ('URL', 'URL_HASH', 'INACTIVITY_TIMEOUT', 'TIMEOUT'):
        assert fields.count(name) == 1 and fields.index(name) + 1 < len(fields), (
            'GUI archive acquisition must declare each URL, digest and deadline exactly once'
        )
    assert fields[fields.index('URL') + 1] == (
        'https://github.com/easyscience/gui-components/archive/' + GUI_PIN + '.tar.gz'
    ), 'Desktop builds must fetch the immutable upstream GUI commit from ADR-0015'
    assert fields[fields.index('URL_HASH') + 1] == 'SHA256=' + GUI_ARCHIVE_SHA256, (
        'Desktop GUI acquisition must verify the independently frozen upstream archive digest'
    )
    for name, bound in [('INACTIVITY_TIMEOUT', 60), ('TIMEOUT', 600)]:
        value = fields[fields.index(name) + 1]
        assert value.isdecimal() and 0 < int(value) <= bound, (
            'The default archive acquisition must retain bounded stalled and total download time'
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
    assert_default_gui_fetch(fields)


@pytest.mark.parametrize(
    'damage',
    [
        'url',
        'digest',
        'missing-stall',
        'missing-total',
        'zero-stall',
        'zero-total',
        'unbounded-stall',
        'unbounded-total',
        'nonnumeric',
        'missing-value',
        'duplicate',
    ],
)
def test_gui_archive_observer_refuses_url_digest_and_deadline_escapes(damage):
    fields = [
        'gui_components',
        'URL',
        'https://github.com/easyscience/gui-components/archive/' + GUI_PIN + '.tar.gz',
        'URL_HASH',
        'SHA256=' + GUI_ARCHIVE_SHA256,
        'INACTIVITY_TIMEOUT',
        '60',
        'TIMEOUT',
        '600',
    ]
    assert_default_gui_fetch(fields)
    if damage == 'url':
        fields[2] = fields[2].replace(GUI_PIN, 'master')
    elif damage == 'digest':
        fields[4] = 'SHA256=' + '0' * 64
    elif damage.startswith('missing-'):
        index = fields.index('INACTIVITY_TIMEOUT' if damage == 'missing-stall' else 'TIMEOUT')
        del fields[index : index + 2]
    elif damage == 'zero-stall':
        fields[6] = '0'
    elif damage == 'unbounded-total':
        fields[8] = '601'
    elif damage == 'zero-total':
        fields[8] = '0'
    elif damage == 'unbounded-stall':
        fields[6] = '61'
    elif damage == 'nonnumeric':
        fields[8] = 'unbounded'
    elif damage == 'missing-value':
        fields.pop()
    else:
        fields += ['URL', fields[2]]
    with pytest.raises(AssertionError):
        assert_default_gui_fetch(fields)
