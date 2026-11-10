# SPDX-License-Identifier: BSD-3-Clause
"""The Python files of the published wheel, by their name in it (no compiled extension).

Its top-level packages are `easydiffraction`, the name a user imports (ADR-0079), and `edi`, the
module it stands for. tools/installer/python_wheel.py writes them and
tools/checks/wheel_packages.py checks them.
"""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PACKAGES = ('easydiffraction', 'edi')


def package_files() -> dict[str, Path]:
    files = {
        f'{name}/{path.name}': path
        for name in PACKAGES
        for path in sorted((ROOT / 'lib' / name).glob('*.py'))
    }
    for path in sorted((ROOT / 'data/report/vendor').iterdir()):
        if path.is_file():
            files[f'edi/data/report/vendor/{path.name}'] = path
    return files
