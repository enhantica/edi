"""Configure the actual GUI base adapter against private, non-Git source copies.

The caller supplies the already acquired pinned archive or checkout: no test-time
networking, SDK, Qt installation, or compiler is needed. Run after app acquisition.
"""

from __future__ import annotations

import argparse
import shutil
import subprocess
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]


def configure(
    cmake: str, adapter: Path, project: Path, source: Path, name: str
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [
            cmake,
            '-S',
            str(project),
            '-B',
            str(project.parent / name),
            f'-DTEST_BASE_SOURCE={source}',
            f'-DTEST_ADAPTER={adapter}',
        ],
        capture_output=True,
        text=True,
        check=False,
        timeout=10,
    )


def cached_source(build_dir: Path) -> Path:
    cache = build_dir.resolve() / 'CMakeCache.txt'
    if not cache.is_file():
        raise RuntimeError(f'Configured app cache is missing: {cache}')
    entries = {}
    wanted = ('FETCHCONTENT_SOURCE_DIR_GUI_COMPONENTS', 'FETCHCONTENT_BASE_DIR')
    for line in cache.read_text().splitlines():
        for key in wanted:
            if line.startswith(key + ':'):
                if key in entries:
                    raise RuntimeError(f'Duplicate dependency source entry in {cache}: {key}')
                if '=' not in line:
                    raise RuntimeError(f'Malformed dependency source entry in {cache}: {key}')
                entries[key] = line.split('=', 1)[1]
    override = entries.get('FETCHCONTENT_SOURCE_DIR_GUI_COMPONENTS', '')
    base = entries.get('FETCHCONTENT_BASE_DIR', '')
    if not override and not base:
        raise RuntimeError(f'App cache does not declare the acquired GUI base source: {cache}')
    source = Path(override) if override else Path(base) / 'gui_components-src'
    if not source.is_absolute() or not source.is_dir():
        raise RuntimeError(f'App cache GUI source is not an existing absolute directory: {source}')
    return source


def check(source: Path, cmake: str) -> None:
    adapter = ROOT / 'cmake/EdiGuiBase.cmake'
    if not (source / 'src/EasyApplication/Gui/Components/ListView.qml').is_file():
        raise RuntimeError('Supply the already acquired pinned gui-components source root')
    # These real upstream siblings exercise the component-sort versus full-path-sort seam.
    if (
        not (source / 'src/EasyApplication/Logic/Maintenance.py').is_file()
        or not (source / 'src/EasyApplication/Logic/Maintenance/Updater.qml').is_file()
    ):
        raise RuntimeError(
            'The pinned source must include both Maintenance.py and Maintenance/Updater.qml'
        )
    with tempfile.TemporaryDirectory(prefix='edi-gui-base-configure-') as directory:
        scratch = Path(directory)
        plain = scratch / 'archive'
        shutil.copytree(source / 'src', plain / 'src')
        project = scratch / 'project'
        modules = project / 'modules'
        modules.mkdir(parents=True)
        # Acquisition is already complete. All identity checks stay in the actual adapter;
        # only network population and downstream Qt module/resource declarations are stubbed.
        (modules / 'FetchContent.cmake').write_text("""
function(FetchContent_Declare name)
    if(NOT name STREQUAL "gui_components")
        message(FATAL_ERROR "Unexpected dependency")
    endif()
    cmake_parse_arguments(P "" "URL;URL_HASH" "" ${ARGN})
    if(NOT P_URL STREQUAL "https://github.com/easyscience/gui-components/archive/${EDI_GUI_COMPONENTS_SHA}.tar.gz")
        message(FATAL_ERROR "Archive URL does not use the declared revision")
    endif()
    if(NOT P_URL_HASH STREQUAL "SHA256=${EDI_GUI_COMPONENTS_ARCHIVE_SHA256}")
        message(FATAL_ERROR "Archive content hash is not declared")
    endif()
endfunction()
function(FetchContent_MakeAvailable name)
    set(${name}_SOURCE_DIR "${TEST_BASE_SOURCE}" PARENT_SCOPE)
endfunction()
""")
        (project / 'CMakeLists.txt').write_text("""
cmake_minimum_required(VERSION 3.26)
project(GuiBaseArchiveProbe NONE)
list(PREPEND CMAKE_MODULE_PATH "${CMAKE_CURRENT_SOURCE_DIR}/modules")
function(qt_add_library)
endfunction()
function(qt_add_qml_module)
endfunction()
function(qt_add_resources)
endfunction()
include("${TEST_ADAPTER}")
file(WRITE "${CMAKE_BINARY_DIR}/accepted" "${EDI_GUI_COMPONENTS_SHA}")
""")
        clean = configure(cmake, adapter, project, plain, 'clean')
        if clean.returncode != 0 or not (scratch / 'clean/accepted').is_file():
            raise RuntimeError('Clean pinned archive was refused:\n' + clean.stdout + clean.stderr)
        target = plain / 'src/EasyApplication/Gui/Components/ListView.qml'
        original = target.read_bytes()
        target.write_bytes(original + b'\n// configure gate modified-byte control\n')
        altered = configure(cmake, adapter, project, plain, 'modified')
        target.write_bytes(original)
        extra = plain / 'src/extra-configure-control.qml'
        extra.write_text('import QtQuick\nItem {}\n')
        extended = configure(cmake, adapter, project, plain, 'extra')
        for name, result in (('modified', altered), ('extra', extended)):
            output = result.stdout + result.stderr
            if result.returncode == 0 or (scratch / name / 'accepted').exists():
                raise RuntimeError(f'{name} source passed the pinned adapter')
            if 'src/ files unmodified' not in ' '.join(output.split()):
                raise RuntimeError(f'{name} source failed outside the identity check:\n' + output)
        print(
            'gui-base configure: clean plain archive accepted; '
            'modified byte and extra source refused'
        )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument('--source-dir', type=Path)
    source.add_argument('--build-dir', type=Path)
    parser.add_argument('--cmake', default=shutil.which('cmake'))
    args = parser.parse_args()
    if not args.cmake:
        parser.error('CMake is unavailable; pass --cmake or run in the app environment')
    source_dir = (
        cached_source(args.build_dir) if args.build_dir is not None else args.source_dir.resolve()
    )
    check(source_dir, args.cmake)


if __name__ == '__main__':
    main()
