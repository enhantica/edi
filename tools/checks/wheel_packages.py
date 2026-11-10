#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-3-Clause
"""The published wheel's top-level package is `easydiffraction` (ADR-0079).

A notebook installs the wheel and runs `import easydiffraction as edi`, so a wheel without that
package fails in every fresh environment, as in Colab. This reads the file list the wheel writer
uses.
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'tools/installer'))

from wheel_layout import package_files  # noqa: E402


def main() -> int:
    names = package_files()
    tops = sorted({name.split('/', 1)[0] for name in names})
    if 'easydiffraction/__init__.py' not in names:
        found = ', '.join(tops)
        print(f'the wheel has no easydiffraction package (top level: {found})', file=sys.stderr)
        return 1
    print('wheel top-level packages: ' + ', '.join(tops))
    return 0


if __name__ == '__main__':
    sys.exit(main())
