"""Build a real public-model observer against an explicitly selected native core."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
from pathlib import Path

HERE = Path(__file__).resolve().parent


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def build(root, backend, output, *, sdk=None, core=None, headers=None):  # noqa: PLR0914
    headers = headers or root
    if backend == 'crysta':
        core = core or root / 'build/tests/libcrysta_core.a'
    else:
        consumer = bool(
            os.environ.get('EDI_USE_CONSUMER_BUILD') or os.environ.get('CRYSTA_CONSUMER_SRC')
        )
        directory = 'ci-consumer' if consumer else 'ci'
        core = core or root / 'build' / directory / 'core/libedi_core.a'
        sdk = sdk or root / 'build' / ('crysta-consumer-prefix' if consumer else 'crysta-prefix')
    if not core.is_file():
        message = f'The native model observer requires the prepared {backend} core: {core}'
        raise FileNotFoundError(message)
    output.mkdir(parents=True, exist_ok=True)
    inputs = {
        'backend': backend,
        'source': digest(HERE / 'probe.cpp'),
        'builder': digest(HERE / 'build_probe.py'),
        'core': digest(core),
    }
    prefix = [str(sdk)] if sdk else []
    if sdk:
        inputs['sdk_model'] = digest(sdk / 'include/crysta/model.hpp')
    inputs['model'] = digest(
        headers
        / ('core/include/edi/model.hpp' if backend == 'edi' else 'include/crysta/model.hpp')
    )
    inputs['public_headers'] = hashlib.sha256(
        b''.join(
            p.read_bytes()
            for folder in (headers / 'include', headers / 'core/include')
            if folder.is_dir()
            for p in sorted(folder.rglob('*.hpp'))
        )
    ).hexdigest()
    recipe = {
        **inputs,
        'core_path': str(core.resolve()),
        'headers': str(headers.resolve()),
        'sdk': str(sdk.resolve()) if sdk else None,
    }
    executable = output / 'cmake/edge_probe'
    receipt = output / 'inputs.json'
    if receipt.is_file() and executable.is_file():
        cached = json.loads(receipt.read_text())
        if cached.get('recipe') == recipe and cached.get('executable') == digest(executable):
            return executable
    raw_core = '' if sdk else str(core)
    edi_core = str(core) if backend == 'edi' else ''
    text = f'''cmake_minimum_required(VERSION 3.20)
project(single_crystal_edges LANGUAGES CXX)
find_package(Threads REQUIRED)
if("{raw_core}" STREQUAL "")
  find_package(crysta CONFIG REQUIRED)
  set(engine_target crysta::crysta)
else()
  find_package(Eigen3 CONFIG REQUIRED)
  find_package(OpenMP)
  find_library(SLEEF_LIBRARY NAMES sleef)
  add_library(edge_core STATIC IMPORTED)
  set_target_properties(edge_core PROPERTIES IMPORTED_LOCATION "{raw_core}")
  set(engine_target edge_core Eigen3::Eigen)
  if(OpenMP_CXX_FOUND)
    list(APPEND engine_target OpenMP::OpenMP_CXX)
  endif()
  if(SLEEF_LIBRARY)
    list(APPEND engine_target ${{SLEEF_LIBRARY}})
  endif()
endif()
add_executable(edge_probe "{(HERE / 'probe.cpp').as_posix()}")
target_compile_features(edge_probe PRIVATE cxx_std_20)
target_compile_definitions(edge_probe PRIVATE EDGE_SOURCE_SHA=\\\"{inputs['source']}\\\")
target_include_directories(edge_probe PRIVATE
  "{headers.as_posix()}/include" "{headers.as_posix()}/core/include")
target_link_libraries(edge_probe PRIVATE
  {('"' + edi_core + '" ') if edi_core else ''}${{engine_target}} Threads::Threads)
'''
    if backend == 'edi':
        text += 'target_compile_definitions(edge_probe PRIVATE EDGE_EDI)\n'
    (output / 'CMakeLists.txt').write_text(text)
    prefix += [os.environ.get('CONDA_PREFIX', '')]
    cmake = shutil.which('cmake')
    if cmake is None:
        message = 'The native observer requires CMake'
        raise FileNotFoundError(message)
    subprocess.run(
        [
            cmake,
            '-S',
            str(output),
            '-B',
            str(output / 'cmake'),
            '-G',
            'Ninja',
            '-DCMAKE_BUILD_TYPE=Release',
            '-DCMAKE_PREFIX_PATH=' + ';'.join(prefix),
        ],
        check=True,
    )
    subprocess.run(
        [
            cmake,
            '--build',
            str(output / 'cmake'),
            '--target',
            'edge_probe',
            '--parallel',
            (
                subprocess.check_output(
                    [shutil.which('bash'), str(root / 'tools/ci/test-workers.sh')], text=True
                ).strip()
                if backend == 'crysta'
                else str(os.cpu_count() or 1)
            ),
        ],
        check=True,
    )
    receipt.write_text(
        json.dumps({'recipe': recipe, 'executable': digest(executable)}, indent=2) + '\n'
    )
    return executable


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--root', type=Path, required=True)
    parser.add_argument('--backend', choices=('crysta', 'edi'), required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--sdk', type=Path)
    parser.add_argument('--core', type=Path)
    parser.add_argument('--headers', type=Path)
    args = parser.parse_args()
    print(
        build(
            args.root,
            args.backend,
            args.output,
            sdk=args.sdk,
            core=args.core,
            headers=args.headers,
        )
    )


if __name__ == '__main__':
    main()
