# SPDX-License-Identifier: BSD-3-Clause
"""Configure the same native compiler cache on Linux, macOS and Windows."""

from __future__ import annotations

import hashlib
import os
import subprocess
import sys
from pathlib import Path

import crysta_sdk


def main() -> None:
    """Write native paths and source/lock identity to GitHub's environment files."""

    # Pixi may rewrite editable package metadata during environment realization.
    # Restore and save must group objects by the same committed recipe inputs.
    def committed(name: str) -> bytes:
        return subprocess.check_output(['git', 'show', 'HEAD:' + name], timeout=5)

    pin = crysta_sdk.pinned(committed('pixi.toml').decode('utf-8'))[:12]
    lock = hashlib.sha256(committed('pixi.lock')).hexdigest()[:12]
    prefix = f'{os.environ["RUNNER_OS"]}-{os.environ["RUNNER_ARCH"]}-crysta-{pin}-lock-{lock}-'
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
    with Path(os.environ['GITHUB_OUTPUT']).open('a', encoding='utf-8') as output:
        output.write(f'prefix={prefix}\n')


if __name__ == '__main__':
    main()
