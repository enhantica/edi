#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-3-Clause
"""Compile the app with MSVC and edi's warnings as errors (ADR-0093): CI's `app · Windows` job.

    python tools/ci/app-windows-build.py --crysta-source DIR --work DIR

It takes Qt, the crysta SDK and the compiler settings from the installer's own build
(tools/installer/build.py), so the app compiles as the Windows installer compiles it, and stops
once edi_app and the CLI are built and carry the UTF-8 code page (ADR-0109): nothing is staged.
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'installer'))

import build  # the installer's helpers, found through the path above


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split('\n\n', 1)[0])
    parser.add_argument('--crysta-source', type=Path, required=True)
    parser.add_argument('--work', type=Path, required=True)
    args = parser.parse_args()
    if not (args.crysta_source / 'include/crysta/model.hpp').is_file():
        raise SystemExit('app-windows-build: the crysta source checkout is missing')
    qt = build.resolve_qt_prefix(None)
    prefix = build.acquire_sdk(args.crysta_source.resolve())
    app = args.work.resolve() / 'app'
    build.run([
        'cmake',
        '-S',
        build.ROOT,
        '-B',
        app,
        '-G',
        'Ninja',
        '-DCMAKE_BUILD_TYPE=Release',
        f'-DPython_EXECUTABLE={sys.executable}',
        '-DCMAKE_CXX_FLAGS=' + build.WINDOWS_CXX_FLAGS,
        '-DCMAKE_MSVC_RUNTIME_LIBRARY=MultiThreadedDLL',
        '-DEDI_WERROR=ON',
        '-DEDI_BUILD_APP=ON',
        '-DEDI_BUILD_BINDINGS=OFF',
        f'-DCMAKE_PREFIX_PATH={prefix.as_posix()};{qt.as_posix()}',
    ])
    # Every file compiles even after one fails, so one run lists every warning made an error.
    targets = ['--target', 'edi_app', 'easydiffraction']
    build.run(['cmake', '--build', app, *targets, '--parallel', '4', '--', '-k', '0'])
    # The programs' own embedded manifests, and Python's, which must fail the same check.
    check = Path(__file__).resolve().parent / 'windows_manifest.py'
    programs = [app / 'app/edi_app.exe', app / 'cli/easydiffraction.exe']
    subprocess.run([sys.executable, check, *programs], check=True)
    subprocess.run([sys.executable, check, '--refused', sys.executable], check=True)


if __name__ == '__main__':
    main()
