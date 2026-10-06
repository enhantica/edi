"""Build the observation host without touching the product build or app tier switches."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import tarfile
from pathlib import Path


def fingerprint(root):
    paths = sorted({
        *root.glob('app/src/*'),
        *root.glob('app/qml/**/*.qml'),
        *root.glob('core/src/*'),
        *root.glob('core/include/edi/*'),
        root / 'CMakeLists.txt',
        root / 'app/CMakeLists.txt',
        root / 'core/CMakeLists.txt',
        root / 'pixi.toml',
        root / 'pixi.lock',
        *root.glob('data/*'),
        *root.glob('app/resources/**/*'),
        *root.glob('docs/user/cli/*/project/**/*'),
    })
    return {
        str(path.relative_to(root)): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in paths
        if path.is_file()
    }


def fixture_fingerprint(root):
    return {
        str(path.relative_to(root)): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in sorted(root.rglob('*'))
        if path.is_file() and path.suffix in {'.cpp', '.hpp', '.py', '.txt'}
    }


def fingerprint_headers(root):
    return {
        str(path.relative_to(root)): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in sorted(root.rglob('*.hpp'))
    }


def run(command, **kwargs):
    subprocess.run(command, check=True, **kwargs)


def snapshot(root, build, fixture):
    source = build / 'source'
    source.mkdir(parents=True, exist_ok=True)
    (source / 'app/src/scan_contract_sink.hpp').unlink(missing_ok=True)
    (source / 'core/src/scan_contract_fit_sink.hpp').unlink(missing_ok=True)
    archive = build / 'source.tar'
    with archive.open('wb') as stream:
        run(['git', '-C', str(root), 'archive', 'HEAD'], stdout=stream)
    with tarfile.open(archive) as stream:
        stream.extractall(source, filter='data')
    shutil.copytree(fixture, source / 'tests/fixtures/scan_app', dirs_exist_ok=True)
    hashes = fingerprint(source)
    adapter = source / 'core/src/adapter.cpp'
    text = adapter.read_text()
    marker = 'const PreambleCallback& on_start, const CancelCallback& should_cancel) {'
    if text.count(marker) != 1:
        raise RuntimeError(
            'Single fit identity actor must reach the effective measured-data entry'
        )
    text = text.replace(marker, marker + '\n    scan_contract_fit_data(grid, observed, sigma);', 1)
    adapter.write_text('#include "scan_contract_fit_sink.hpp"\n' + text)
    shutil.copyfile(
        fixture / 'scan_contract_fit_sink.hpp', source / 'core/src/scan_contract_fit_sink.hpp'
    )
    cmake = source / 'CMakeLists.txt'
    cmake.write_text(cmake.read_text() + '\nadd_subdirectory(tests/fixtures/scan_app)\n')
    core_cmake = source / 'core/CMakeLists.txt'
    core_cmake.write_text(
        core_cmake.read_text() + '\nfile(GENERATE OUTPUT "${CMAKE_BINARY_DIR}/scan-core-sdk.txt" '
        'CONTENT "$<TARGET_FILE:crysta::crysta>\\n'
        '$<TARGET_PROPERTY:crysta::crysta,INTERFACE_INCLUDE_DIRECTORIES>")\n'
    )
    layer = source / 'app/src/measured_layer.cpp'
    marker = '    points_ = points;'
    text = layer.read_text()
    if text.count(marker) != 1:
        raise RuntimeError('Evolution observer must reach MeasuredLayer.setData')
    text = text.replace(
        marker, '    scan_contract_layer_receipt(points, low, high);\n' + marker, 1
    )
    text = '#include "scan_contract_sink.hpp"\n' + text
    layer.write_text(text)
    shutil.copyfile(fixture / 'scan_contract_sink.hpp', source / 'app/src/scan_contract_sink.hpp')
    return source, hashes


def observe_entry(library, build, symbol, replacement, destination, objcopy):
    members = subprocess.check_output(['llvm-ar', 't', str(library)], text=True).splitlines()
    definitions = subprocess.check_output(
        ['llvm-nm', '-A', '--defined-only', str(library)], text=True
    ).splitlines()
    found = [line for line in definitions if line.split()[-1:] == [symbol]]
    if len(found) != 1:
        raise RuntimeError('Native actor must reach one compiled public entry definition')
    member = [
        name
        for name in members
        if any(
            token in found[0] for token in (':' + name + ':', '(' + name + '):', '[' + name + ']:')
        )
    ]
    if len(member) != 1:
        raise RuntimeError('Native actor must bind its actual archive member')
    fit_object = build / destination
    with fit_object.open('wb') as output:
        run(['llvm-ar', 'p', str(library), member[0]], stdout=output)
    run([objcopy, '--redefine-sym=' + symbol + '=' + replacement, str(fit_object)])
    return fit_object


def observed_object(sdk, build, fixture):
    # Rename only the public driver definition and optimizer reference in the SDK object.
    # Its instruction bytes and all reads/CSV writes remain the installed implementation.
    library = sdk / 'lib/libcrysta_core.a'
    member = [
        name
        for name in subprocess.check_output(['llvm-ar', 't', str(library)], text=True).splitlines()
        if name == 'sequential.cpp.o'
    ]
    if len(member) != 1:
        raise RuntimeError('Scan execution: installed SDK must have one compiled scan object')
    native_object = build / 'observed_scan.o'
    with native_object.open('wb') as output:
        run(['llvm-ar', 'p', str(library), member[0]], stdout=output)
    symbols = subprocess.check_output(
        ['llvm-nm', '-g', str(native_object)], text=True
    ).splitlines()
    names = [line.split()[-1] for line in symbols if line.split()]
    optimizer = [name for name in names if '11fit_project' in name]
    # Obtain this toolchain's exact wrapper symbol spellings from its own object.
    wrapper_object = build / 'boundary.o'
    run([
        os.environ.get('CXX', 'c++'),
        '-std=c++20',
        '-I' + str(sdk / 'include'),
        '-I' + str(Path(os.environ['CONDA_PREFIX']) / 'include/eigen3'),
        '-I' + str(fixture),
        '-c',
        str(fixture / 'native_boundary.cpp'),
        '-o',
        str(wrapper_object),
    ])
    wrappers = subprocess.check_output(
        ['llvm-nm', '-g', str(wrapper_object)], text=True
    ).splitlines()
    wrapper_names = [line.split()[-1] for line in wrappers if line.split()]
    driver = [
        name for name in names if '22sequential_fit_project' in name and name in wrapper_names
    ]
    if len(optimizer) != 1 or len(driver) != 1:
        raise RuntimeError('Scan execution: compiled native boundaries must resolve uniquely')
    real = next(name for name in wrapper_names if 'scan_contract_real_sequential' in name)
    reader = [
        name for name in wrapper_names if 'read_sequential_scan_data' in name
    ]
    if len(reader) != 1:
        raise RuntimeError('Pending-selection actor must reach the compiled public dataset reader')
    real_reader = next(name for name in wrapper_names if 'scan_contract_real_dataset_read' in name)
    entry = next(name for name in wrapper_names if 'scan_contract_optimizer' in name)
    objcopy = shutil.which('llvm-objcopy')
    if not objcopy:
        raise RuntimeError('Scan execution: declared LLVM object-copy tool is required')
    run([
        objcopy,
        '--redefine-sym=' + driver[0] + '=' + real,
        '--redefine-sym=' + optimizer[0] + '=' + entry,
        str(native_object),
    ])
    real_fit = next(name for name in wrapper_names if 'scan_contract_real_fit' in name)
    fit_object = observe_entry(
        library, build, optimizer[0], real_fit, 'observed_fit.o', objcopy
    )
    reader_object = observe_entry(
        library, build, reader[0], real_reader, 'observed_reader.o', objcopy
    )
    return native_object, fit_object, reader_object


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--root', type=Path, required=True)
    parser.add_argument('--build', type=Path, required=True)
    parser.add_argument('--sdk', type=Path, required=True)
    parser.add_argument('--engine-source', type=Path)
    parser.add_argument('--gui-source', type=Path)
    parser.add_argument('--python', type=Path)
    args = parser.parse_args()
    root = args.root.resolve()
    build = args.build.resolve()
    fixture = Path(__file__).resolve().parent
    source, hashes = snapshot(root, build, fixture)
    native_object, fit_object, reader_object = observed_object(args.sdk, build, fixture)
    command = [
        'cmake',
        '-S',
        str(source),
        '-B',
        str(build / 'cmake'),
        '-G',
        'Ninja',
        '-DEDI_BUILD_APP=ON',
        '-DEDI_BUILD_BINDINGS=OFF',
        '-DSCAN_CONTRACT_NATIVE_OBJECT=' + str(native_object),
        '-DSCAN_CONTRACT_NATIVE_FIT_OBJECT=' + str(fit_object),
        '-DSCAN_CONTRACT_NATIVE_READ_OBJECT=' + str(reader_object),
        '-DCMAKE_BUILD_TYPE=Release',
        '-DCMAKE_CXX_COMPILER_LAUNCHER=ccache',
        '-DCMAKE_PREFIX_PATH=' + str(args.sdk) + ';' + os.environ['CONDA_PREFIX'],
        '-Dcrysta_DIR=' + str(args.sdk / 'lib/cmake/crysta'),
    ]
    if args.python:
        command.extend([
            '-DPython_EXECUTABLE=' + str(args.python),
            '-Dnanobind_DIR='
            + subprocess.check_output(
                [str(args.python), '-m', 'nanobind', '--cmake_dir'], text=True
            ).strip(),
        ])
    if os.environ.get('CXX'):
        command.append('-DCMAKE_CXX_COMPILER=' + os.environ['CXX'])
    command.append('-DSCAN_CONTRACT_ENGINE_SOURCE=' + str(args.engine_source))
    if args.gui_source:
        command.append('-DFETCHCONTENT_SOURCE_DIR_GUI_COMPONENTS=' + str(args.gui_source))
    run(command)
    expected = (args.sdk / 'lib/libcrysta_core.a').resolve()
    for record in ('scan-core-sdk.txt', 'scan-reference-sdk.txt'):
        lines = (build / 'cmake' / record).read_text().splitlines()
        includes = lines[1].split(';')
        if (
            Path(lines[0]).resolve() != expected
            or str((args.sdk / 'include').resolve()) not in includes
        ):
            raise RuntimeError('Scan execution: effective CMake SDK library/header paths differ')
    jobs = (
        os.environ.get('CMAKE_BUILD_PARALLEL_LEVEL')
        or subprocess.check_output(
            ['bash', str(args.engine_source / 'tools/ci/test-workers.sh')], text=True
        ).strip()
    )
    run([
        'cmake',
        '--build',
        str(build / 'cmake'),
        '--target',
        'scan_app_probe',
        'scan_reference',
        '-j',
        jobs,
    ])
    receipt = {
        'production': hashes,
        'fixture': fixture_fingerprint(fixture),
        'sdk_headers': fingerprint_headers(args.sdk / 'include'),
        'engine_sha': subprocess.check_output(
            ['git', '-C', str(args.engine_source), 'rev-parse', 'HEAD'], text=True
        ).strip()
        if args.engine_source
        else None,
        'sdk_library': hashlib.sha256(
            (args.sdk / 'lib/libcrysta_core.a').read_bytes()
        ).hexdigest(),
        'engine_source': str(args.engine_source),
        'executable': str(build / 'cmake/tests/fixtures/scan_app/scan_app_probe'),
    }
    receipt['reference_package'] = str(build / 'cmake/tests/fixtures/scan_app/reference/package')
    receipt['reference_source'] = {
        str(path.relative_to(args.engine_source)): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in sorted((args.engine_source / 'src/bindings').rglob('*'))
        if path.is_file()
    }
    receipt['reference_binary'] = {
        path.name: hashlib.sha256(path.read_bytes()).hexdigest()
        for path in sorted(Path(receipt['reference_package']).glob('crysta/_crysta.*'))
        if path.is_file()
    }
    receipt['binary'] = hashlib.sha256(Path(receipt['executable']).read_bytes()).hexdigest()
    (build / 'receipt.json').write_text(json.dumps(receipt, indent=2) + '\n')


if __name__ == '__main__':
    main()
