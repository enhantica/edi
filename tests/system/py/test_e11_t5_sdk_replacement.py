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


@pytest.mark.parametrize('entry', ['app', 'core', 'consumer'])
def test_sdk_replacement_at_the_same_prefix_rebuilds_consuming_objects(tmp_path, entry):
    work = tmp_path / 'edi'
    ci = work / 'tools/ci'
    ci.mkdir(parents=True)
    script = 'app-build.sh' if entry == 'app' else 'core-build.sh'
    shutil.copyfile(ROOT / 'tools/ci' / script, ci / script)
    (ci / 'crysta-src.sh').write_text('#!/bin/bash\nexit 0\n')
    (ci / 'build-crysta.sh').write_text(
        '#!/bin/bash\nset -eu\n'
        'prefix=build/crysta-prefix\n'
        'if [ -n "${CRYSTA_SDK_DIR:-}" ]; then prefix=build/crysta-consumer-prefix; fi\n'
        'if [ "${PIXI_ENVIRONMENT_NAME:-default}" = app ]; then prefix="$prefix-app"; fi\n'
        'mkdir -p "$prefix/include" "$prefix/share/crysta-sdk"\n'
        'cp -p "$SDK_IDENTITY_FIXTURE/witness.hpp" "$prefix/include/witness.hpp"\n'
        'cp "$SDK_IDENTITY_FIXTURE/sha" "$prefix/.crysta-sha"\n'
        'cp "$SDK_IDENTITY_FIXTURE/manifest.json" "$prefix/share/crysta-sdk/manifest.json"\n'
    )
    prefix = (
        'crysta-consumer-prefix-app'
        if entry == 'app'
        else ('crysta-consumer-prefix' if entry == 'consumer' else 'crysta-prefix')
    )
    (work / 'CMakeLists.txt').write_text(
        'cmake_minimum_required(VERSION 3.21)\nproject(SdkIdentityWitness LANGUAGES CXX)\n'
        'add_executable(sdk_identity_witness main.cpp)\n'
        'target_include_directories(sdk_identity_witness PRIVATE '
        f'${{CMAKE_SOURCE_DIR}}/build/{prefix}/include)\n'
    )
    (work / 'main.cpp').write_text(
        '#include "witness.hpp"\n#include <iostream>\n'
        'int main(){std::cout << sdk_identity_witness() << "\\n";}\n'
    )
    sdk, packages = tmp_path / 'sdk', tmp_path / 'environment'
    sdk.mkdir()
    (packages / 'conda-meta').mkdir(parents=True)
    env = {
        **os.environ,
        'CONDA_PREFIX': str(packages),
        'PIXI_ENVIRONMENT_NAME': 'app' if entry == 'app' else 'default',
        'SDK_IDENTITY_FIXTURE': str(sdk),
        'EDI_APP_TARGETS': 'sdk_identity_witness',
        'CCACHE_DIR': str(tmp_path / 'ccache'),
    }
    for key in [
        'CRYSTA_SDK_DIR',
        'CRYSTA_CONSUMER_SRC',
        'EDI_CRYSTA_PREFIX',
        'PYTEST_XDIST_WORKER',
    ]:
        env.pop(key, None)
    if entry != 'core':
        env.update(CRYSTA_SDK_DIR=str(sdk), EDI_USE_CONSUMER_BUILD='1')
    build = (
        work
        / 'build'
        / ('app' if entry == 'app' else 'ci-consumer' if entry == 'consumer' else 'ci')
    )
    executable = build / 'sdk_identity_witness'
    for version in [111, 222]:
        (sdk / 'witness.hpp').write_text(
            f'inline int sdk_identity_witness(){{return {version};}}\n'
        )
        os.utime(sdk / 'witness.hpp', (1_000_000_000, 1_000_000_000))
        (sdk / 'sha').write_text(str(version) * 13 + 'a\n')
        (sdk / 'manifest.json').write_text(
            json.dumps({
                'schema': 1,
                'source_sha': str(version) * 13 + 'a',
                'source_tree': str(version) * 13 + 'b',
            })
        )
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
