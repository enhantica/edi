"""Real entry/link/run witnesses for selected installed SDK content, never scientific goldens."""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import sys
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


@pytest.mark.skipif(sys.platform not in ('linux', 'darwin'), reason='original native SDK platforms only')
def test_native_bootstrap554_real_outer_sibling_local_resolution_and_module_exclusion(tmp_path, installed_sdk):
    """Real installed target/constructor; no source-string or fake-bootstrap witness."""
    root = tmp_path / 'native-bootstrap'; root.mkdir()
    (root / 'observer.cpp').write_text(
        '#include <crysta/threading.hpp>\n#include <cstdlib>\n#include <iostream>\n'
        'extern "C" int bootstrap554_wait(){return std::getenv("OMP_WAIT_POLICY")?1:0;}\n'
        'extern "C" int bootstrap554_engine(){return crysta::threading::visible_concurrency();}\n'
        'int main(){auto w=std::getenv("OMP_WAIT_POLICY"),n=std::getenv("OMP_NUM_THREADS");'
        'std::cout<<"wait="<<(w?w:"<absent>")<<";team="<<(n?n:"<absent>")<<"\\n";}\n'
    )
    # Include the actual owning Edi project: its core import must serve sibling CLI and this outer scope.
    (root / 'CMakeLists.txt').write_text(
        'cmake_minimum_required(VERSION 3.24)\nproject(native_bootstrap554 LANGUAGES CXX)\n'
        'set(EDI_BUILD_APP OFF CACHE BOOL "" FORCE)\n'
        'set(EDI_BUILD_BINDINGS OFF CACHE BOOL "" FORCE)\n'
        'set(EDI_BUILD_ASSISTANT_NATIVE OFF CACHE BOOL "" FORCE)\n'
        f'add_subdirectory("{ROOT.as_posix()}" edi)\n'
        'add_executable(outer554 observer.cpp)\n'
        'target_compile_features(outer554 PRIVATE cxx_std_20)\n'
        'target_link_libraries(outer554 PRIVATE crysta::crysta '
        '"$<LINK_LIBRARY:WHOLE_ARCHIVE,crysta::process_defaults>")\n'
        'add_library(module554 MODULE observer.cpp)\n'
        'target_compile_features(module554 PRIVATE cxx_std_20)\n'
        'target_link_libraries(module554 PRIVATE crysta::crysta)\n'
        'set_target_properties(module554 PROPERTIES PREFIX "")\n'
        'file(GENERATE OUTPUT "${CMAKE_BINARY_DIR}/module-path.txt" CONTENT "$<TARGET_FILE:module554>")\n'
        'file(GENERATE OUTPUT "${CMAKE_BINARY_DIR}/cli-link.txt" '
        'CONTENT "$<TARGET_PROPERTY:easydiffraction,LINK_LIBRARIES>")\n'
        'file(GENERATE OUTPUT "${CMAKE_BINARY_DIR}/core-interface.txt" '
        'CONTENT "$<TARGET_PROPERTY:edi_core,INTERFACE_LINK_LIBRARIES>")\n'
    )
    env = {k:v for k,v in os.environ.items() if not k.startswith(('EDI_', 'CRYSTA_'))}
    for name in ('OMP_WAIT_POLICY','GOMP_SPINCOUNT','KMP_BLOCKTIME','OMP_NUM_THREADS','OMP_DYNAMIC'):
        env.pop(name, None)
    world = {'root':root, 'env':env}
    build = root / 'build'
    configured = invoke(['cmake','-S',str(root),'-B',str(build),
                         '-DCMAKE_PREFIX_PATH='+str(installed_sdk)],world)
    assert configured.returncode == 0, ('BOOTSTRAP554: actual Edi outer/sibling package resolution succeeds: ' + configured.stdout + configured.stderr)
    linked = (build/'cli-link.txt').read_text()
    assert 'WHOLE_ARCHIVE,crysta::process_defaults' in linked, 'actual sibling CLI explicitly owns bootstrap'
    assert 'process_defaults' not in (build/'core-interface.txt').read_text(), 'original core interface stays bootstrap-free'
    compiled = invoke(['cmake','--build',str(build),'--target','outer554','module554','-j2'],world)
    assert compiled.returncode == 0, ('BOOTSTRAP554: actual installed public native targets link: ' + compiled.stdout + compiled.stderr)
    executable = build/'outer554'
    healthy = invoke([str(executable)],world)
    assert healthy.returncode == 0 and healthy.stdout.startswith('wait=passive;team='), ('BOOTSTRAP554: executable constructor applies original defaults before main: ' + healthy.stdout+healthy.stderr)
    assert healthy.stdout.split('team=',1)[1].strip().isdigit(), 'real before-main bootstrap plants a team default'
    for name in ('OMP_WAIT_POLICY','GOMP_SPINCOUNT','KMP_BLOCKTIME'):
        owned = {'root':root, 'env':dict(env, **{name:''})}
        caller = invoke([str(executable)],owned)
        expected = 'wait=;team=<absent>' if name=='OMP_WAIT_POLICY' else 'wait=<absent>;team=<absent>'
        assert caller.returncode == 0 and caller.stdout.strip()==expected, 'caller PRESENCE including empty stands down whole policy'
    explicit = invoke([str(executable)],{'root':root,'env':dict(env,OMP_NUM_THREADS='3')})
    assert explicit.returncode == 0 and explicit.stdout.strip()=='wait=passive;team=3', ('BOOTSTRAP554: explicit team choice survives original bootstrap: ' + explicit.stdout+explicit.stderr)
    module = (build/'module-path.txt').read_text()
    observed = invoke([sys.executable,'-c',
        'import ctypes; m=ctypes.CDLL('+repr(module)+'); assert m.bootstrap554_engine()>0; '
        'assert m.bootstrap554_wait()==0; print("module-without-bootstrap")'],world)
    assert observed.returncode == 0 and 'module-without-bootstrap' in observed.stdout, ('BOOTSTRAP554: linked MODULE invokes public core without executable bootstrap: ' + observed.stdout+observed.stderr)
    # Original standalone find_package remains local in its own fresh project, separate from the outer global import.
    local = root/'local'
    shutil.copytree(ROOT/'tools/ci/crysta-consumer',local)
    local_build = root/'local-build'
    local_config = invoke(['cmake','-S',str(local),'-B',str(local_build),
                           '-DCMAKE_PREFIX_PATH='+str(installed_sdk)],world)
    assert local_config.returncode == 0, ('BOOTSTRAP554: original standalone local package import resolves: ' + local_config.stdout+local_config.stderr)
    local_link = invoke(['cmake','--build',str(local_build),'-j2'],world)
    assert local_link.returncode == 0, ('BOOTSTRAP554: original standalone public caller links: ' + local_link.stdout+local_link.stderr)
    probe = invoke([str(local_build/'crysta_consumer'),'--c22-t22-thread-probe'],world)
    assert probe.returncode == 0 and 'team=' in probe.stdout and 'cpu_wall=' in probe.stdout, ('BOOTSTRAP554: original standalone constructor reaches actual native probe: ' + probe.stdout+probe.stderr)
