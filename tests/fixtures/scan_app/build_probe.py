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
    paths = sorted({*root.glob('app/src/*'), *root.glob('app/qml/**/*.qml'),
                    *root.glob('core/src/*'), *root.glob('core/include/edi/*'),
                    root / 'CMakeLists.txt', root / 'app/CMakeLists.txt',
                    root / 'core/CMakeLists.txt', root / 'pixi.toml', root / 'pixi.lock',
                    *root.glob('data/*'), *root.glob('app/resources/**/*'),
                    *root.glob('docs/user/cli/*/project/**/*')})
    return {str(path.relative_to(root)): hashlib.sha256(path.read_bytes()).hexdigest()
            for path in paths if path.is_file()}


def fixture_fingerprint(root):
    return {path.name: hashlib.sha256(path.read_bytes()).hexdigest()
            for path in sorted(root.glob('*')) if path.is_file()
            and path.suffix in {'.cpp', '.hpp', '.py', '.txt'}}



def fingerprint_headers(root):
    return {str(path.relative_to(root)): hashlib.sha256(path.read_bytes()).hexdigest()
            for path in sorted(root.rglob('*.hpp'))}


def run(command, **kwargs):
    subprocess.run(command, check=True, **kwargs)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--root', type=Path, required=True)
    parser.add_argument('--build', type=Path, required=True)
    parser.add_argument('--sdk', type=Path, required=True)
    parser.add_argument('--engine-source', type=Path)
    parser.add_argument('--gui-source', type=Path)
    args = parser.parse_args()
    root = args.root.resolve()
    build = args.build.resolve()
    source = build / 'source'
    source.mkdir(parents=True, exist_ok=True)
    archive = build / 'source.tar'
    with archive.open('wb') as stream:
        run(['git', '-C', str(root), 'archive', 'HEAD'], stdout=stream)
    with tarfile.open(archive) as stream:
        stream.extractall(source, filter='data')
    fixture = Path(__file__).resolve().parent
    shutil.copytree(fixture, source / 'tests/fixtures/scan_app', dirs_exist_ok=True)
    hashes = fingerprint(source)
    cmake = source / 'CMakeLists.txt'
    cmake.write_text(cmake.read_text() + '\nadd_subdirectory(tests/fixtures/scan_app)\n')
    layer = source / 'app/src/measured_layer.cpp'
    marker = '    points_ = points;'
    text = layer.read_text()
    if text.count(marker) != 1:
        raise RuntimeError('Evolution observer must reach MeasuredLayer.setData')
    text = text.replace(marker, '    scan_contract_layer_receipt(points, low, high);\n' + marker, 1)
    text = '#include "scan_contract_sink.hpp"\n' + text
    layer.write_text(text)
    shutil.copyfile(fixture / 'scan_contract_sink.hpp', source / 'app/src/scan_contract_sink.hpp')
    if args.engine_source:
        native = (args.engine_source / 'src/core/sequential.cpp').read_text()
        call = 'last_result = fit_project(working, on_iteration, should_cancel);'
        if native.count(call) != 1:
            raise RuntimeError('Optimizer observer must reach one native scan entry')
        native = native.replace(call, 'scan_contract_work(file_name, working);\n        ' + call)
        event = 'on_file_complete(row);'
        if native.count(event) != 1:
            raise RuntimeError('Completion observer must reach the durable native event')
        native = native.replace(event, event + '\n            scan_contract_file_completed(file_name);', 1)
        observed = source / 'tests/fixtures/scan_app/observed_engine.cpp'
        observed.write_text('#include "scan_contract_work.hpp"\n' + native)
    command = ['cmake', '-S', str(source), '-B', str(build / 'cmake'), '-G', 'Ninja',
               '-DEDI_BUILD_APP=ON', '-DEDI_BUILD_BINDINGS=OFF',
               '-DCMAKE_BUILD_TYPE=Release', '-DCMAKE_CXX_COMPILER_LAUNCHER=ccache',
               '-DCMAKE_PREFIX_PATH=' + str(args.sdk) + ';' + os.environ['CONDA_PREFIX']]
    if os.environ.get('CXX'):
        command.append('-DCMAKE_CXX_COMPILER=' + os.environ['CXX'])
    if args.engine_source:
        command.append('-DSCAN_CONTRACT_ENGINE_SOURCE=' + str(args.engine_source))
    if args.gui_source:
        command.append('-DFETCHCONTENT_SOURCE_DIR_GUI_COMPONENTS=' + str(args.gui_source))
    run(command)
    run(['cmake', '--build', str(build / 'cmake'), '--target', 'scan_app_probe', '-j', '2'])
    receipt = {'production': hashes,
               'fixture': fixture_fingerprint(fixture),
               'sdk_headers': fingerprint_headers(args.sdk / 'include'),
               'engine_sha': subprocess.check_output(['git', '-C', str(args.engine_source), 'rev-parse', 'HEAD'], text=True).strip() if args.engine_source else None,
               'sdk_library': hashlib.sha256((args.sdk / 'lib/libcrysta_core.a').read_bytes()).hexdigest(),
               'engine_source': str(args.engine_source),
               'executable': str(build / 'cmake/tests/fixtures/scan_app/scan_app_probe')}
    receipt['binary'] = hashlib.sha256(Path(receipt['executable']).read_bytes()).hexdigest()
    (build / 'receipt.json').write_text(json.dumps(receipt, indent=2) + '\n')


if __name__ == '__main__':
    main()
