"""Compile the public-parser consumer against an explicitly prepared complete core."""

import argparse
import hashlib
import json
import os
import subprocess
from pathlib import Path

HERE = Path(__file__).resolve().parent


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def inputs(root, backend, core, sdk):
    headers = root / ('core/include' if backend == 'edi' else 'include')
    result = {
        'backend': backend,
        'observer': digest(HERE / 'probe.cpp'),
        'builder': digest(HERE / 'build.py'),
        'core': digest(core),
        'headers': {
            str(p.relative_to(headers)): digest(p) for p in sorted(headers.rglob('*.hpp'))
        },
    }
    if sdk:
        result['sdk'] = {
            str(p.relative_to(sdk)): digest(p)
            for folder in ('include', 'lib/cmake')
            for p in sorted((sdk / folder).rglob('*'))
            if p.is_file()
        }
        result['sdk']['lib/libcrysta_core.a'] = digest(sdk / 'lib/libcrysta_core.a')
    return result


def validate(receipt, root):
    recipe = receipt['recipe']
    if (
        inputs(
            root,
            recipe['backend'],
            Path(recipe['core_path']),
            Path(recipe['sdk_path']) if recipe['sdk_path'] else None,
        )
        != receipt['inputs']
    ):
        raise RuntimeError('Parser receipt requires unchanged observer, core and public headers')
    binary = Path(receipt['binary'])
    if not binary.is_file() or digest(binary) != receipt['binary_sha256']:
        raise RuntimeError('Parser receipt requires the exact linked public API consumer')
    return binary


def build(root, backend, output, core, sdk=None):
    root, core, output = root.resolve(), core.resolve(), output.resolve()
    sdk = sdk.resolve() if sdk else None
    before = inputs(root, backend, core, sdk)
    output.mkdir(parents=True, exist_ok=True)
    recipe = {'backend': backend, 'core_path': str(core), 'sdk_path': str(sdk) if sdk else None}
    target = output / 'native/parser_probe'
    receipt_path = output / 'receipt.json'
    if receipt_path.is_file():
        receipt = json.loads(receipt_path.read_text())
        if receipt['inputs'] == before and receipt['recipe'] == recipe:
            validate(receipt, root)
            return receipt_path
    includes = root / ('core/include' if backend == 'edi' else 'include')
    text = f'''cmake_minimum_required(VERSION 3.20)
project(serialized_admission LANGUAGES CXX)
find_package(Threads REQUIRED)
find_package(Eigen3 CONFIG REQUIRED)
find_package(OpenMP REQUIRED)
find_library(SLEEF_LIBRARY NAMES sleef REQUIRED)
add_executable(parser_probe "{HERE / 'probe.cpp'}")
target_compile_features(parser_probe PRIVATE cxx_std_20)
target_compile_definitions(parser_probe PRIVATE
  [=[SERIALIZED_OBSERVER_SHA="{before['observer']}"]=])
target_include_directories(parser_probe PRIVATE "{includes}")
'''
    if backend == 'edi':
        text += f'''find_package(crysta CONFIG REQUIRED)
target_compile_definitions(parser_probe PRIVATE SERIALIZED_EDI)
target_link_libraries(parser_probe PRIVATE "{core}" crysta::crysta)
'''
    else:
        text += f'target_link_libraries(parser_probe PRIVATE "{core}")\n'
    text += """target_link_libraries(parser_probe PRIVATE Eigen3::Eigen OpenMP::OpenMP_CXX
  Threads::Threads ${SLEEF_LIBRARY})
"""
    (output / 'CMakeLists.txt').write_text(text)
    prefix = ';'.join(str(p) for p in (sdk, os.environ.get('CONDA_PREFIX')) if p)
    subprocess.run(
        [
            'cmake',
            '-S',
            str(output),
            '-B',
            str(output / 'native'),
            '-G',
            'Ninja',
            '-DCMAKE_BUILD_TYPE=Release',
            '-DCMAKE_PREFIX_PATH=' + prefix,
        ],
        check=True,
    )
    subprocess.run(
        ['cmake', '--build', str(output / 'native'), '--target', 'parser_probe', '-j', '4'],
        check=True,
    )
    if inputs(root, backend, core, sdk) != before:
        raise RuntimeError('Parser compilation inputs changed during the build')
    receipt = {
        'recipe': recipe,
        'inputs': before,
        'binary': str(target),
        'binary_sha256': digest(target),
    }
    validate(receipt, root)
    receipt_path.write_text(json.dumps(receipt, indent=2) + '\n')
    return receipt_path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, required=True)
    parser.add_argument('--backend', choices=('edi', 'crysta'), required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--core', type=Path, required=True)
    parser.add_argument('--sdk', type=Path)
    args = parser.parse_args()
    print(build(args.root, args.backend, args.output, args.core, args.sdk))


if __name__ == '__main__':
    main()
