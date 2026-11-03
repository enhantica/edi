"""Real metadata-producing CMake targets in an isolated, SDK-free git fixture."""

import os
import re
import shutil
import subprocess
from pathlib import Path

import pytest

from tests.fixtures.fast_ci.processes import process_guard

ROOT = Path(__file__).resolve().parents[3]
SOURCE = Path(os.environ.get('EDI_ONBOARDING_SOURCE_ROOT', ROOT))


def run(*args, cwd):
    result = subprocess.run(args, cwd=cwd, capture_output=True, text=True, check=False, timeout=20)
    assert result.returncode == 0, (
        'The isolated metadata build executes its real git/CMake operation: '
        + ' '.join(map(str, args))
        + '\n'
        + result.stdout
        + result.stderr
    )
    return result.stdout.strip()


@pytest.fixture(scope='module')
def rebuilt_metadata(tmp_path_factory):
    temporary = tmp_path_factory.mktemp('app-version')
    source, build = temporary / 'source', temporary / 'build'
    source.mkdir()
    shutil.copytree(SOURCE / 'cmake', source / 'cmake')
    for relative in (
        'app/CMakeLists.txt',
        'app/src/app_build_info.hpp.in',
        'app/src/app_info.cpp',
    ):
        destination = source / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(SOURCE / relative, destination)
    shutil.copyfile(ROOT / 'tests/fixtures/app_metadata/CMakeLists.txt', source / 'CMakeLists.txt')
    # Unrelated resource inventories have no role in build identity.
    (source / 'docs/user/cli').mkdir(parents=True)
    (source / 'docs/user/cli/projects.yml').write_text('schema: 1\nprojects: []\n')
    (source / 'app/examples').mkdir()
    (source / 'app/examples/metadata.json').write_text('{"schema":1,"examples":{}}\n')
    for relative in (
        'COPYING',
        'LICENSE',
        'THIRD-PARTY-NOTICES',
        'DEPENDENCIES.md',
        'app/DISTRIBUTION-LICENSE.md',
    ):
        (source / relative).write_text('Resource placeholder; not built or installed.\n')
    run('git', 'init', '-q', cwd=source)
    run('git', 'add', '.', cwd=source)
    identity = [
        '-c',
        'user.name=Fixture',
        '-c',
        'user.email=fixture@example.invalid',
        '-c',
        'commit.gpgsign=false',
    ]
    run('git', *identity, 'commit', '-qm', 'Initial metadata fixture', cwd=source)
    run('git', 'tag', 'v2031.1', cwd=source)
    cmake = str(ROOT / '.pixi/envs/app/bin/cmake')
    ninja = str(ROOT / '.pixi/envs/app/bin/ninja')
    configure = [
        cmake,
        '-S',
        str(source),
        '-B',
        str(build),
        '-G',
        'Ninja',
        '-DCMAKE_MAKE_PROGRAM=' + ninja,
    ]
    run(*configure, cwd=source)

    def version():
        # Observe the generated value the actual ApplicationInfo consumer uses.
        # Both its former macro and a build-time producer are valid mechanisms;
        # the expected value remains the independently tagged git history.
        consumer = (source / 'app/src/app_info.cpp').read_text()
        if 'QStringLiteral(EDI_APP_VERSION)' in consumer:
            header = build / 'app/app_build_info.hpp'
            assert header.is_file(), 'The app produces its consumed version header'
            values = re.findall(
                r'^#define EDI_APP_VERSION "([^"\n]*)"$', header.read_text(), re.MULTILINE
            )
        else:
            assert 'edi_app::app_version()' in consumer, (
                'The metadata witness observes the actual ApplicationInfo version consumer'
            )
            values = []
            for generated in build.rglob('*.cpp'):
                values.extend(
                    re.findall(
                        r'app_version\(\)\s*(?:noexcept)?\s*\{\s*return\s+"([^"\n]*)"',
                        generated.read_text(),
                    )
                )
        assert len(values) == 1, 'Exactly one generated value feeds the app version'
        return values[0]

    with process_guard(ROOT):
        run(cmake, '--build', str(build), '--target', 'edi_app', cwd=source)
    first = version()
    expected_first = run('git', 'describe', '--tags', '--always', '--dirty', cwd=source)
    # Only git history changes. No CMake input is touched and no sleep is used.
    run('git', *identity, 'commit', '--allow-empty', '-qm', 'Next metadata fixture', cwd=source)
    run('git', 'tag', 'v2031.2', cwd=source)
    expected_second = run('git', 'describe', '--tags', '--always', '--dirty', cwd=source)
    revision = run('git', 'rev-parse', 'HEAD', cwd=source)
    with process_guard(ROOT):
        run(cmake, '--build', str(build), '--target', 'edi_app', cwd=source)
    incremental = version()
    marker = (build / 'edi_app_build_commit.cpp').read_text()
    assert revision in marker, (
        'The real build-time commit producer proves the second build ran at the new commit'
    )
    run(*configure, cwd=source)
    with process_guard(ROOT):
        run(cmake, '--build', str(build), '--target', 'edi_app', cwd=source)
    return (
        first,
        expected_first,
        expected_second,
        {'incremental': incremental, 'reconfigured': version()},
    )


@pytest.mark.parametrize('reuse', ['incremental', 'reconfigured'])
def test_user_visible_version_follows_a_new_commit_in_a_reused_build(rebuilt_metadata, reuse):
    first, expected_first, expected_second, rebuilt = rebuilt_metadata
    assert first == expected_first, 'The first configure/build reports the independent git version'
    assert expected_second != expected_first, (
        'The fixture changes git version without changing a CMake input'
    )
    assert rebuilt[reuse] == expected_second, (
        'A rebuild after a new commit refreshes the user-visible version, '
        'including with a reused CMake cache'
    )
