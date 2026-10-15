"""Build-helper regression: a stable SDK prefix must not retain old inline ABI code."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]


def run(args, cwd, env):
    result = subprocess.run(
        args, cwd=cwd, env=env, capture_output=True, text=True, timeout=25, check=False
    )
    assert result.returncode == 0, (
        'E11-T5 SDK identity: the controlled real helper/build invocation must complete: '
        + result.stdout
        + result.stderr
    )
    return result.stdout


def sdk_world(tmp_path, entry, change):
    work = tmp_path / 'edi'
    ci = work / 'tools/ci'
    ci.mkdir(parents=True)
    app = entry.startswith('app-')
    script = 'app-build.sh' if app else 'core-build.sh'
    shutil.copyfile(ROOT / 'tools/ci' / script, ci / script)
    (ci / 'crysta-src.sh').write_text('#!/bin/bash\nexit 0\n')
    (ci / 'build-crysta.sh').write_text(
        '#!/bin/bash\nset -eu\n'
        'prefix=build/crysta-prefix\n'
        'if [ -n "${CRYSTA_SDK_DIR:-}" ]; then prefix=build/crysta-consumer-prefix; fi\n'
        'if [ "${PIXI_ENVIRONMENT_NAME:-default}" = app ]; then prefix="$prefix-app"; fi\n'
        'if [ "${SDK_LINK_FIXTURE:-0}" = 1 ]; then\n'
        '  mkdir -p "$(dirname "$prefix")"\n'
        '  rm -f "$prefix"\n'
        '  ln -s "$SDK_IDENTITY_FIXTURE" "$prefix"\n'
        '  exit 0\n'
        'fi\n'
        'mkdir -p "$prefix/include" "$prefix/share/crysta-sdk"\n'
        'cp -p "$SDK_IDENTITY_FIXTURE/witness.hpp" "$prefix/include/witness.hpp"\n'
        'cp "$SDK_IDENTITY_FIXTURE/sha" "$prefix/.crysta-sha"\n'
        'cp "$SDK_IDENTITY_FIXTURE/manifest.json" "$prefix/share/crysta-sdk/manifest.json"\n'
    )
    prefix = (
        (
            'local-prefix'
            if entry == 'app-local'
            else 'crysta-prefix-app'
            if entry == 'app-pinned'
            else 'crysta-consumer-prefix-app'
        )
        if app
        else ('crysta-consumer-prefix' if entry == 'consumer' else 'crysta-prefix')
    )
    (work / 'CMakeLists.txt').write_text(
        'cmake_minimum_required(VERSION 3.21)\nproject(SdkIdentityWitness LANGUAGES CXX)\n'
        'if(EXISTS "${CMAKE_SOURCE_DIR}/reject-configure")\n'
        'message(FATAL_ERROR "fixture configure interruption")\nendif()\n'
        'add_executable(sdk_identity_witness main.cpp)\n'
        'add_custom_target(witness_gate COMMAND ${CMAKE_COMMAND}\n'
        '-DROOT=${CMAKE_SOURCE_DIR} -P ${CMAKE_SOURCE_DIR}/gate.cmake)\n'
        'add_dependencies(sdk_identity_witness witness_gate)\n'
        'target_include_directories(sdk_identity_witness PRIVATE '
        f'${{CMAKE_SOURCE_DIR}}/build/{prefix}/include)\n'
    )
    (work / 'gate.cmake').write_text(
        'if(EXISTS "${ROOT}/reject-build")\n'  # noqa: RUF027 - literal CMake variable.
        'message(FATAL_ERROR "fixture build interruption")\nendif()\n'
    )
    (work / 'main.cpp').write_text(
        '#include "witness.hpp"\n#include <iostream>\n'
        'int main(){std::cout << sdk_identity_witness() << "\\n";}\n'
    )
    sdk, packages = tmp_path / 'sdk', tmp_path / 'environment'
    sdk.mkdir()
    (sdk / 'include').mkdir()
    (sdk / 'share/crysta-sdk').mkdir(parents=True)
    (packages / 'conda-meta').mkdir(parents=True)
    env = {
        **os.environ,
        'CONDA_PREFIX': str(packages),
        'PIXI_ENVIRONMENT_NAME': 'app' if app else 'default',
        'SDK_IDENTITY_FIXTURE': str(sdk),
        'EDI_APP_TARGETS': 'sdk_identity_witness',
        'CCACHE_DIR': str(tmp_path / 'ccache'),
    }
    for key in [
        'CRYSTA_SDK_DIR',
        'CRYSTA_CONSUMER_SRC',
        'EDI_CRYSTA_PREFIX',
        'PYTEST_XDIST_WORKER',
        'CI',
        'EDI_USE_CONSUMER_BUILD',
        'EDI_CORE_TARGETS',
        'EDI_NATIVE_ARTIFACT',
        'EDI_GUI_COMPONENTS_SRC',
    ]:
        env.pop(key, None)
    if entry in {'app-candidate', 'consumer'}:
        env.update(CRYSTA_SDK_DIR=str(sdk), EDI_USE_CONSUMER_BUILD='1')
    build = work / 'build' / ('app' if app else 'ci-consumer' if entry == 'consumer' else 'ci')
    executable = build / 'sdk_identity_witness'
    destination = work / 'build' / prefix
    if entry == 'app-local':
        env['EDI_CRYSTA_PREFIX'] = str(destination)
    if change == 'retarget':
        env['SDK_LINK_FIXTURE'] = '1'
    return work, ci, script, sdk, env, destination, executable


@pytest.mark.parametrize('entry', ['app-pinned', 'app-candidate', 'app-local', 'core', 'consumer'])
@pytest.mark.parametrize(
    'change', ['identity', 'content', 'replacement', 'retarget', 'configure-retry', 'build-retry']
)
def test_sdk_replacement_at_the_same_prefix_rebuilds_consuming_objects(tmp_path, entry, change):
    work, ci, script, sdk, env, destination, executable = sdk_world(tmp_path, entry, change)
    for version in [111, 222]:
        if change == 'retarget':
            sdk = tmp_path / ('sdk-' + str(version))
            (sdk / 'include').mkdir(parents=True)
            (sdk / 'share/crysta-sdk').mkdir(parents=True)
            env['SDK_IDENTITY_FIXTURE'] = str(sdk)
        (sdk / 'witness.hpp').write_text(
            f'inline int sdk_identity_witness(){{return {version};}}\n'
        )
        os.utime(sdk / 'witness.hpp', (1_000_000_000, 1_000_000_000))
        identity = version if change == 'identity' else 111
        (sdk / 'sha').write_text(str(identity) * 13 + 'a\n')
        (sdk / 'manifest.json').write_text(
            json.dumps({
                'schema': 1,
                'source_sha': str(identity) * 13 + 'a',
                'source_tree': str(identity) * 13 + 'b',
            })
        )
        shutil.copy2(sdk / 'witness.hpp', sdk / 'include/witness.hpp')
        shutil.copy2(sdk / 'sha', sdk / '.crysta-sha')
        shutil.copy2(sdk / 'manifest.json', sdk / 'share/crysta-sdk/manifest.json')
        if version == 222 and change == 'replacement' and destination.exists():
            shutil.rmtree(destination)
        if entry == 'app-local':
            if destination.is_symlink():
                destination.unlink()
            if change == 'retarget':
                destination.parent.mkdir(parents=True, exist_ok=True)
                destination.symlink_to(sdk, target_is_directory=True)
            else:
                shutil.copytree(sdk, destination, dirs_exist_ok=True, copy_function=shutil.copy2)
        if version == 222 and change in {'configure-retry', 'build-retry'}:
            failure = 'configure' if change == 'configure-retry' else 'build'
            guard = work / ('reject-' + failure)
            guard.touch()
            interrupted = subprocess.run(
                ['bash', str(ci / script)],
                cwd=work,
                env=env,
                capture_output=True,
                text=True,
                timeout=25,
                check=False,
            )
            assert (
                interrupted.returncode != 0
                and ('fixture ' + failure + ' interruption')
                in interrupted.stdout + interrupted.stderr
            ), (
                'E11-T5 SDK identity: recovery control must first reach the deliberate '
                'configure/build interruption'
            )
            guard.unlink()
        run(['bash', str(ci / script)], work, env)
        assert run([str(executable)], work, env).strip() == str(version), (
            'E11-T5 SDK identity: replacing SDK content at one prefix with old header timestamps '
            'must execute the new header ABI, including app, ordinary core and consumer builds'
        )
        stamp = executable.stat().st_mtime_ns
        run(['bash', str(ci / script)], work, env)
        assert executable.stat().st_mtime_ns == stamp, (
            'E11-T5 SDK identity: an unchanged SDK/toolchain '
            'retains its valid incremental artifact'
        )


def test_actual_app_local_override_remains_forbidden_in_ci(tmp_path):
    work, ci, script, _, env, _, _ = sdk_world(tmp_path, 'app-local', 'identity')
    env['CI'] = 'true'
    result = subprocess.run(
        ['bash', str(ci / script)],
        cwd=work,
        env=env,
        capture_output=True,
        text=True,
        timeout=5,
        check=False,
    )
    assert result.returncode != 0 and all(
        token in result.stdout + result.stderr for token in ['EDI_CRYSTA_PREFIX', 'CI']
    ), (
        'E11-T5 SDK authority: the actual production app helper still refuses '
        'a local override in CI'
    )
    assert not (work / 'build/app').exists(), (
        'E11-T5 SDK authority: CI refuses the local override before configuring consumer artifacts'
    )
