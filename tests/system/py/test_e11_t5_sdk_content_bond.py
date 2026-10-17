"""Real entry/link/run witnesses for selected installed SDK content, never scientific goldens."""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]


def invoke(argv, world, *, standalone=False):
    return subprocess.run(
        argv,
        cwd=world['root'],
        env=world['standalone_env'] if standalone else world['env'],
        capture_output=True,
        text=True,
        timeout=25,
        check=False,
    )


@pytest.fixture(scope='module')
def installed_sdk(tmp_path_factory):
    source = ROOT / 'build/crysta-prefix'
    assert (source / 'lib/cmake/crysta/crystaConfig.cmake').is_file(), (
        'SDK4: a real installed SDK must exist before the standalone content-bond witness'
    )
    template = tmp_path_factory.mktemp('copied-installed-sdk') / 'sdk'
    # Copy actual SDK bytes once. Never hard-link or modify the canonical installed SDK.
    shutil.copytree(source.resolve(), template)
    provenance = {
        'source_prefix': str(source.resolve()),
        'source_sha': (source / '.crysta-sha').read_text().strip(),
        'manifest_sha256': hashlib.sha256(
            (source / 'share/crysta-sdk/manifest.json').read_bytes()
        ).hexdigest(),
        'purpose': 'Private copied installed SDK; no SDK build, qualification or publication',
    }
    (template.parent / 'provenance.json').write_text(json.dumps(provenance, indent=2))
    return template


def unit_world(tmp_path, template, selection):
    root = tmp_path / 'edi'
    ci = root / 'tools/ci'
    ci.mkdir(parents=True)
    for name in ['core-build.sh', 'crysta-consumer.sh', 'sdk_content_identity.py']:
        shutil.copy2(ROOT / 'tools/ci' / name, ci / name)
    shutil.copytree(ROOT / 'tools/ci/crysta-consumer', ci / 'crysta-consumer')
    (ci / 'build-crysta.sh').write_text(
        '#!/bin/bash\nset -eu\n'
        'destination=build/crysta-prefix\n'
        'if [ -n "${CRYSTA_SDK_DIR:-}" ]; then destination=build/crysta-consumer-prefix; fi\n'
        'mkdir -p build\nrm -f "$destination"\n'
        'ln -s "$SDK_SELECTED_FIXTURE" "$destination"\n'
    )
    (ci / 'crysta-src.sh').write_text(
        '#!/bin/bash\nset -eu\nmkdir -p build/crysta-src\n'
        'cp "$SDK_SELECTED_FIXTURE/.crysta-sha" build/crysta-src/CRYSTA_SOURCE_SHA\n'
    )
    a, b = tmp_path / 'sdk-A', tmp_path / 'sdk-B'
    # Hard links below are only between these private copies, never into the installed SDK.
    shutil.copytree(template, a, copy_function=os.link)
    header = a / 'include/crysta/e11_build_identity_fixture.hpp'
    header.write_text('inline int e11_build_identity_fixture(){return 111;}\n')
    os.utime(header, (1_000_000_000, 1_000_000_000))
    shutil.copytree(a, b, copy_function=os.link)
    changed = b / header.relative_to(a)
    changed.unlink()
    changed.write_text('inline int e11_build_identity_fixture(){return 222;}\n')
    os.utime(changed, (1_000_000_000, 1_000_000_000))
    (root / 'CMakeLists.txt').write_text(
        'cmake_minimum_required(VERSION 3.21)\nproject(LinkedSdkWitness LANGUAGES CXX)\n'
        'if(EXISTS "${CMAKE_SOURCE_DIR}/reject-configure")\n'
        'message(FATAL_ERROR "fixture configure interruption")\nendif()\n'
        'file(MAKE_DIRECTORY "${CMAKE_BINARY_DIR}/python/edi")\n'
        'find_package(crysta CONFIG REQUIRED)\nadd_executable(edi_sdk_witness unit.cpp)\n'
        'target_compile_features(edi_sdk_witness PRIVATE cxx_std_20)\n'
        'target_link_libraries(edi_sdk_witness PRIVATE crysta::crysta)\n'
        'add_custom_target(build_gate COMMAND ${CMAKE_COMMAND} '
        '-DROOT=${CMAKE_SOURCE_DIR} -P ${CMAKE_SOURCE_DIR}/gate.cmake)\n'
        'add_dependencies(edi_sdk_witness build_gate)\n'
    )
    (root / 'gate.cmake').write_text(
        'if(EXISTS "${ROOT}/reject-build")\n'  # noqa: RUF027 - literal CMake syntax.
        'message(FATAL_ERROR "fixture build interruption")\nendif()\n'
    )
    (root / 'unit.cpp').write_text(
        '#include <cstdio>\n#include "crysta/scattering.hpp"\n'
        '#include "crysta/e11_build_identity_fixture.hpp"\n'
        'int main(){auto s=crysta::load_neutron_scattering();'
        'std::printf("unit identity=%d\\n",e11_build_identity_fixture());'
        'return s.b_c.at("Na")>0 ? 0 : 1;}\n'
    )
    # Preserve the actual standalone project and its public C++ call. Add only an independent
    # fixture observer; 111/222 describe build content, never physical scattering correctness.
    standalone = ci / 'crysta-consumer'
    with (standalone / 'CMakeLists.txt').open('a') as stream:
        stream.write('\ntarget_sources(crysta_consumer PRIVATE identity_observer.cpp)\n')
    (standalone / 'identity_observer.cpp').write_text(
        '#include <cstdio>\n#include "crysta/e11_build_identity_fixture.hpp"\n'
        'namespace {struct Print {Print(){std::printf("standalone identity=%d\\n",'
        'e11_build_identity_fixture());}} observed;}\n'
    )
    configuration = 'consumer' if selection.endswith('consumer') else 'ordinary'
    build = root / 'build' / ('ci-consumer' if configuration == 'consumer' else 'ci')
    env = {
        name: value
        for name, value in os.environ.items()
        if not name.startswith(('EDI_', 'CRYSTA_'))
    }
    env.update(
        SDK_SELECTED_FIXTURE=str(a),
        CMAKE_BUILD_PARALLEL_LEVEL='2',
        CCACHE_DISABLE='1',
        CMAKE_CXX_COMPILER_LAUNCHER='',
    )
    if configuration == 'consumer':
        env.update(CRYSTA_SDK_DIR=str(a), EDI_USE_CONSUMER_BUILD='1')
    if selection.startswith('extension-'):
        for name in ['ci', 'ci-consumer']:
            (root / 'build' / name / 'python/edi').mkdir(parents=True)
        env['EDI_EXTENSION_DIR'] = str(build / 'python/edi')
        # Explicit extension outranks the conflicting configuration selector.
        if configuration == 'ordinary':
            env['EDI_USE_CONSUMER_BUILD'] = '1'
    standalone_env = env.copy()
    if selection == 'extension-consumer':
        standalone_env.pop('EDI_USE_CONSUMER_BUILD', None)
    producer_names = ['core-build.sh', 'crysta-consumer.sh', 'sdk_content_identity.py']
    (root / 'fixture-producer-sha256.json').write_text(
        json.dumps(
            {
                name: hashlib.sha256((ROOT / 'tools/ci' / name).read_bytes()).hexdigest()
                for name in producer_names
            },
            indent=2,
        )
    )
    return {
        'root': root,
        'env': env,
        'standalone_env': standalone_env,
        'a': a,
        'b': b,
        'configuration': configuration,
        'executable': build / 'edi_sdk_witness',
        'prefix': root
        / 'build'
        / ('crysta-consumer-prefix' if configuration == 'consumer' else 'crysta-prefix'),
    }


@pytest.mark.parametrize(
    ('selection', 'interruption'),
    [
        ('ordinary', None),
        ('consumer', None),
        ('extension-ordinary', None),
        ('extension-consumer', None),
        ('ordinary', 'configure'),
        ('consumer', 'build'),
    ],
)
def test_standalone_proof_requires_the_actual_successful_selected_unit_content(
    tmp_path, installed_sdk, selection, interruption
):
    world = unit_world(tmp_path, installed_sdk, selection)
    built = invoke(['bash', 'tools/ci/core-build.sh'], world)
    assert built.returncode == 0, (
        'SDK4: the actual required core entry first builds a real linked fixture unit: '
        + built.stdout
        + built.stderr
    )
    original = invoke([str(world['executable'])], world)
    assert original.returncode == 0 and 'unit identity=111' in original.stdout, (
        'SDK4: the real original executable contains independently chosen SDK content A'
    )
    assert (world['a'] / '.crysta-sha').read_bytes() == (
        world['b'] / '.crysta-sha'
    ).read_bytes(), 'SDK4: the replacement deliberately retains the original SDK source identity'
    world['prefix'].unlink()
    world['prefix'].symlink_to(world['b'], target_is_directory=True)
    world['env']['SDK_SELECTED_FIXTURE'] = str(world['b'])
    world['standalone_env']['SDK_SELECTED_FIXTURE'] = str(world['b'])
    if world['configuration'] == 'consumer':
        world['env']['CRYSTA_SDK_DIR'] = str(world['b'])
        world['standalone_env']['CRYSTA_SDK_DIR'] = str(world['b'])
    if interruption:
        guard = world['root'] / ('reject-' + interruption)
        guard.touch()
        failed = invoke(['bash', 'tools/ci/core-build.sh'], world)
        assert (
            failed.returncode != 0
            and ('fixture ' + interruption + ' interruption') in failed.stdout + failed.stderr
        ), (
            'SDK4: the failed rebuild really reaches its configure/build failure, '
            'rather than manufacturing a successful-unit identity'
        )
        guard.unlink()
    refused = invoke(['bash', 'tools/ci/crysta-consumer.sh'], world, standalone=True)
    assert refused.returncode != 0 and (
        'rebuild' in (refused.stdout + refused.stderr).lower()
        or 'core-build' in refused.stdout + refused.stderr
    ), (
        'SDK4: standalone proof refuses same-source changed content until the selected '
        'edi unit has really rebuilt; an attempt key is insufficient'
    )
    assert 'installed-consumer gate: PASS' not in refused.stdout, (
        'SDK4: a freshly built standalone consumer cannot certify stale selected edi objects'
    )
    if interruption:
        # Failure controls stop at the attempted-build refusal. The four uninterrupted
        # selections below separately require the actual successful B rebuild and proof.
        return
    rebuilt = invoke(['bash', 'tools/ci/core-build.sh'], world)
    assert rebuilt.returncode == 0, (
        'SDK4: the required selected-unit rebuild completes after the actual refusal'
    )
    current = invoke([str(world['executable'])], world)
    assert current.returncode == 0 and 'unit identity=222' in current.stdout, (
        'SDK4: successful rebuild really consumes independently chosen replacement content B'
    )
    proven = invoke(['bash', 'tools/ci/crysta-consumer.sh'], world, standalone=True)
    assert proven.returncode == 0 and all(
        text in proven.stdout
        for text in [
            'standalone identity=222',
            'crysta zero-Python consumer OK:',
            'installed-consumer gate: PASS',
        ]
    ), (
        'SDK4: only the successfully rebuilt matching unit permits the real '
        'standalone configure/link/public-call proof of content B'
    )
