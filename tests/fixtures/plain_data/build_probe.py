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
        ['cmake', '--build', str(build / 'cmake'), '--target', 'plain_data_probe', '-j'],
        check=True,
    )
    print(build / 'cmake/tests/fixtures/plain_data/plain_data_probe')


if __name__ == '__main__':
    main()
