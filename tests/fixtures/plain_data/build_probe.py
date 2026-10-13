"""Build a native observation host against the installed SDK and product app module."""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import tarfile
from pathlib import Path


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--root', type=Path, required=True)
    parser.add_argument('--build', type=Path, required=True)
    parser.add_argument('--sdk', type=Path, required=True)
    parser.add_argument('--gui-source', type=Path)
    parser.add_argument('--timing-observer', action='store_true')
    args = parser.parse_args()
    build = args.build.resolve()
    build.mkdir(parents=True, exist_ok=True)
    archive = build / 'source.tar'
    with archive.open('wb') as output:
        subprocess.run(['git', '-C', str(args.root), 'archive', 'HEAD'], stdout=output, check=True)
    source = build / 'source'
    source.mkdir(exist_ok=True)
    with tarfile.open(archive) as stream:
        stream.extractall(source, filter='data')
    fixture = Path(__file__).resolve().parent
    shutil.copytree(fixture, source / 'tests/fixtures/plain_data', dirs_exist_ok=True)
    cmake = source / 'CMakeLists.txt'
    cmake.write_text(cmake.read_text() + '\nadd_subdirectory(tests/fixtures/plain_data)\n')
    if args.timing_observer:
        revision = subprocess.check_output(
            ['git', '-C', str(args.root), 'rev-parse', 'HEAD'], text=True
        ).strip()
        objects = subprocess.check_output(
            [
                'git',
                '-C',
                str(args.root),
                'rev-parse',
                '--path-format=absolute',
                '--git-path',
                'objects',
            ],
            text=True,
        ).strip()
        subprocess.run(['git', 'init', '-q', str(source)], check=True)
        (source / '.git/objects/info/alternates').write_text(objects + '\n')
        subprocess.run(
            ['git', '-C', str(source), 'update-ref', 'refs/heads/observation', revision],
            check=True,
        )
        subprocess.run(
            ['git', '-C', str(source), 'symbolic-ref', 'HEAD', 'refs/heads/observation'],
            check=True,
        )
        subprocess.run(['git', '-C', str(source), 'read-tree', revision], check=True)
        # The accepted baseline includes this production timing scenario as a scratch overlay.
        for name in ['demo_driver.cpp', 'demo_driver.hpp']:
            shutil.copy2(args.root / 'app/src' / name, source / 'app/src' / name)
        shutil.copytree(
            fixture.parent / 'scan_timing',
            source / 'tests/fixtures/scan_timing',
            dirs_exist_ok=True,
        )
        cmake.write_text(cmake.read_text() + '\nadd_subdirectory(tests/fixtures/scan_timing)\n')
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
        '-DCMAKE_BUILD_TYPE=Release',
        '-DCMAKE_CXX_COMPILER_LAUNCHER=ccache',
        '-DCMAKE_PREFIX_PATH=' + str(args.sdk) + ';' + os.environ['CONDA_PREFIX'],
        '-Dcrysta_DIR=' + str(args.sdk / 'lib/cmake/crysta'),
    ]
    if args.gui_source:
        command += ['-DFETCHCONTENT_SOURCE_DIR_GUI_COMPONENTS=' + str(args.gui_source)]
    subprocess.run(command, check=True)
    subprocess.run(
        [
            'cmake',
            '--build',
            str(build / 'cmake'),
            '--target',
            'scan_timing_observer' if args.timing_observer else 'plain_data_probe',
            '-j',
        ],
        check=True,
    )
    target = (
        'scan_timing/scan_timing_observer'
        if args.timing_observer
        else 'plain_data/plain_data_probe'
    )
    print(build / 'cmake/tests/fixtures' / target)


if __name__ == '__main__':
    main()
