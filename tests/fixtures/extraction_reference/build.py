# SPDX-License-Identifier: BSD-3-Clause
"""Explicitly build the operation-failure fixture under the caller's build lock."""

import argparse
import hashlib
import json
import subprocess
from pathlib import Path


def sources():
    root = Path(__file__).resolve().parent
    return {
        name: hashlib.sha256((root / name).read_bytes()).hexdigest()
        for name in ('CMakeLists.txt', 'failures.cpp', 'control.cpp')
    }


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('destination', type=Path)
    args = parser.parse_args()
    subprocess.run(
        ['cmake', '-S', str(Path(__file__).resolve().parent), '-B', str(args.destination)],
        check=True,
    )
    subprocess.run(['cmake', '--build', str(args.destination), '-j', '4'], check=True)
    (args.destination / 'sources.json').write_text(json.dumps(sources()), encoding='utf-8')
