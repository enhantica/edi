# SPDX-License-Identifier: BSD-3-Clause
"""Run the sanitizer source and diagnostic contract without compiling the engine."""

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
SOURCE_LINE = 'constexpr auto internalSourceSentinel = 819;'
LOCATION = 'CMake Error at CMakeLists.txt:2 (message):'
COMPILE_LOCATION = 'probe.cpp:2:3: error: fixture diagnostic'


def git(root, *args):
    return subprocess.check_output(
        ['git', '-C', str(root), '-c', 'core.hooksPath=/dev/null', *args],
        text=True,
        timeout=10,
    ).strip()


def commit(root):
    git(root, 'add', '-A')
    git(
        root,
        '-c',
        'user.name=Fixture',
        '-c',
        'user.email=fixture@example.invalid',
        'commit',
        '-qm',
        'Fixture',
    )
    return git(root, 'rev-parse', 'HEAD')


def manifest(sdk, source, sha):
    (sdk / 'share/crysta-sdk/manifest.json').write_text(
        json.dumps({
            'source_sha': sha,
            'source_tree': git(source, 'rev-parse', f'{sha}^{{tree}}'),
        }),
        encoding='utf-8',
    )


@pytest.fixture
def tsan_checkout(tmp_path):
    edi = tmp_path / 'edi'
    scripts = edi / 'tools/ci'
    shutil.copytree(ROOT / 'tools/ci', scripts)
    git(edi, 'init', '-q')
    git(
        edi,
        '-c',
        'user.name=Fixture',
        '-c',
        'user.email=fixture@example.invalid',
        'commit',
        '--allow-empty',
        '-qm',
        'Parent checkout',
    )
    probe = edi / 'tests/unit/cpp/e04_t9_tsan_probe.cpp'
    probe.parent.mkdir(parents=True)
    probe.touch()

    source = tmp_path / 'crysta'
    source.mkdir()
    git(source, 'init', '-q')
    (source / 'CMakeLists.txt').write_text('# Older source\n', encoding='utf-8')
    old = commit(source)
    (source / 'CMakeLists.txt').write_text('# SDK source\n', encoding='utf-8')
    (source / 'code.cpp').write_text(SOURCE_LINE + '\n', encoding='utf-8')
    (source / 'run.sh').write_text('#!/bin/sh\n', encoding='utf-8')
    (source / 'run.sh').chmod(0o755)
    (source / 'link.cpp').symlink_to('code.cpp')
    for mode, constant in [('parallel', 'SOURCE_PATHS'), ('simd', 'PATHS')]:
        builder = source / 'tests/fixtures' / f'web_{mode}' / 'build.py'
        builder.parent.mkdir(parents=True)
        builder.write_text(f'{constant} = ("code.cpp",)\n', encoding='utf-8')
    sha = commit(source)
    sdk = tmp_path / 'sdk'
    (sdk / 'share/crysta-sdk').mkdir(parents=True)
    manifest(sdk, source, sha)

    (scripts / 'crysta_sdk.py').write_text(
        'import os\nprint(os.environ["TEST_SDK"])\n', encoding='utf-8'
    )
    commands = tmp_path / 'bin'
    commands.mkdir()
    (commands / 'python').symlink_to(sys.executable)
    cmake = commands / 'cmake'
    cmake.write_text(
        f'#!{sys.executable}\n'
        'import json, os, sys\n'
        'from pathlib import Path\n'
        'trace = Path(os.environ["TEST_CONFIGURE"])\n'
        'if sys.argv[1] == "-S":\n'
        '    source = Path(sys.argv[2])\n'
        '    paths = {str(file.relative_to(source)): [str(file.readlink()) if file.is_symlink() '
        'else file.read_text(), bool(file.stat().st_mode & 0o100)] '
        "for file in source.rglob('*') if file.is_file() and '.git' not in file.parts}\n"
        '    trace.write_text(json.dumps({"paths": paths, "argv": sys.argv[1:]}))\n'
        '    if os.environ["TEST_FAILURE"] == "configure":\n'
        f'        print({LOCATION!r}, file=sys.stderr)\n'
        f'        print({SOURCE_LINE!r}, file=sys.stderr)\n'
        '        sys.exit(28)\n'
        'else:\n'
        f'    print({COMPILE_LOCATION!r}, file=sys.stderr)\n'
        '    args = json.loads(trace.read_text())["argv"]\n'
        '    if not any("-fno-diagnostics-show-caret" in arg for arg in args):\n'
        f'        print({SOURCE_LINE!r}, file=sys.stderr)\n'
        '    sys.exit(29)\n',
        encoding='utf-8',
    )
    cmake.chmod(0o755)
    env = {
        key: value
        for key, value in os.environ.items()
        if not key.startswith(('GIT_', 'CRYSTA_', 'EDI_PRODUCER_'))
        and key not in {'RUNNER_TEMP', 'PYTEST_XDIST_WORKER', 'BASH_ENV', 'ENV'}
    }
    env.update(
        PATH=f'{commands}{os.pathsep}{os.environ["PATH"]}',
        CRYSTA_SRC=str(source),
        TEST_SDK=str(sdk),
        TEST_CONFIGURE=str(tmp_path / 'configured.json'),
        GIT_CONFIG_NOSYSTEM='1',
        GIT_CONFIG_GLOBAL=os.devnull,
        GITHUB_ACTIONS='true',
        PIXI_ENVIRONMENT_NAME='default',
        RUNNER_OS='Linux',
        RUNNER_ARCH='X64',
    )
    return edi, source, sdk, old, sha, env


def run_tsan(edi, env, failure):
    return subprocess.run(
        ['bash', 'tools/ci/tsan-worker.sh'],
        cwd=edi,
        env={**env, 'TEST_FAILURE': failure},
        capture_output=True,
        text=True,
        timeout=15,
        check=False,
    )


@pytest.mark.skipif(sys.platform != 'linux', reason='ThreadSanitizer worker is Linux-only')
@pytest.mark.parametrize(
    ('route', 'failure'),
    [
        ('pinned', 'configure'),
        ('candidate-behind', 'configure'),
        ('candidate-exact', 'configure'),
        ('candidate-exact', 'compile'),
    ],
)
def test_worker_compiles_the_sdk_export_and_retains_only_safe_diagnostics(
    tsan_checkout, route, failure
):
    edi, source, sdk, old, sha, env = tsan_checkout
    if route.startswith('candidate'):
        env.update(CRYSTA_SDK_DIR=str(sdk), CRYSTA_CONSUMER_SRC=str(source))
        if route == 'candidate-behind':
            git(source, 'checkout', '-q', old)
            (source / 'untracked.cpp').touch()
    else:
        export = edi / 'build/crysta-src'
        export.mkdir(parents=True)
        (export / 'CRYSTA_SOURCE_SHA').write_text(sha + '\n', encoding='utf-8')
        (export / 'CMakeLists.txt').write_text('# Edited export\n', encoding='utf-8')
        (export / 'foreign.cpp').touch()

    result = run_tsan(edi, env, failure)
    trace = Path(env['TEST_CONFIGURE'])
    assert trace.is_file(), 'The manifest source tree must reach the instrumented configure'
    observed = json.loads(trace.read_text(encoding='utf-8'))
    files = observed['paths']
    assert files['CMakeLists.txt'][0] == git(source, 'show', f'{sha}:CMakeLists.txt') + '\n', (
        'The configured file bytes must come from the SDK commit'
    )
    assert files['code.cpp'][0] == SOURCE_LINE + '\n', (
        'The configure sees the pinned source payload'
    )
    assert files['run.sh'][1], 'The SDK export preserves the executable mode'
    assert files['link.cpp'][0] == 'code.cpp', 'The SDK export preserves the symbolic link target'
    assert set(files) - {'CRYSTA_SOURCE_SHA', 'runner-source-objects.json'} == {
        'CMakeLists.txt',
        'code.cpp',
        'run.sh',
        'link.cpp',
        'tests/fixtures/web_parallel/build.py',
        'tests/fixtures/web_simd/build.py',
    }, 'Only the entries in the SDK tree reach configure'
    output = result.stdout + result.stderr
    location = LOCATION if failure == 'configure' else COMPILE_LOCATION
    assert result.returncode != 0 and location in output, (
        'The failed sanitizer stage keeps the diagnostic location and reports failure'
    )
    assert SOURCE_LINE not in output, 'The sanitizer stage must not print a quoted source line'


@pytest.mark.skipif(sys.platform != 'linux', reason='ThreadSanitizer worker is Linux-only')
@pytest.mark.parametrize('route', ['candidate', 'pinned'])
def test_sdk_tree_mismatch_refuses_even_with_an_intact_export(tsan_checkout, route):
    edi, source, sdk, old, sha, env = tsan_checkout
    path = sdk / 'share/crysta-sdk/manifest.json'
    path.write_text(
        json.dumps({
            'source_sha': sha,
            'source_tree': git(source, 'rev-parse', f'{old}^{{tree}}'),
        }),
        encoding='utf-8',
    )
    if route == 'candidate':
        env.update(CRYSTA_SDK_DIR=str(sdk), CRYSTA_CONSUMER_SRC=str(source))
    result = run_tsan(edi, env, 'configure')
    assert result.returncode and not Path(env['TEST_CONFIGURE']).exists(), (
        'A mismatched manifest tree must refuse before the first configure'
    )
    assert 'tree' in result.stderr.lower().replace(str(edi.parent).lower(), ''), (
        'The refusal identifies a source tree mismatch'
    )
