# SPDX-License-Identifier: BSD-3-Clause
"""Configure the same native compiler cache on Linux, macOS and Windows."""

from __future__ import annotations

import hashlib
import os
import sys
from pathlib import Path

import crysta_sdk


def main() -> None:
    """Write native paths and source/lock identity to GitHub's environment files."""
    directory = Path.home() / '.cache/edi-ccache'
    directory.mkdir(parents=True, exist_ok=True)
    settings = {
        'CCACHE_DIR': str(directory),
        'CCACHE_MAXSIZE': sys.argv[1],
        'CCACHE_COMPILERCHECK': 'content',
        'CMAKE_C_COMPILER_LAUNCHER': 'ccache',
        'CMAKE_CXX_COMPILER_LAUNCHER': 'ccache',
    }
    with Path(os.environ['GITHUB_ENV']).open('a', encoding='utf-8') as output:
        output.writelines(f'{key}={value}\n' for key, value in settings.items())
    pin = crysta_sdk.pinned(Path('pixi.toml').read_text(encoding='utf-8'))[:12]
    lock = hashlib.sha256(Path('pixi.lock').read_bytes()).hexdigest()[:12]
    prefix = f'{os.environ["RUNNER_OS"]}-{os.environ["RUNNER_ARCH"]}-crysta-{pin}-lock-{lock}-'
    with Path(os.environ['GITHUB_OUTPUT']).open('a', encoding='utf-8') as output:
        output.write(f'prefix={prefix}\n')


if __name__ == '__main__':
    main()
