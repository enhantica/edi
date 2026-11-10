# SPDX-License-Identifier: BSD-3-Clause
"""Build the Linux transport fixture explicitly before its scoped test run."""

import argparse
import hashlib
import json
import subprocess
from pathlib import Path


def sources():
    root = Path(__file__).resolve().parent
    return {
        name: hashlib.sha256((root / name).read_bytes()).hexdigest()
        for name in ('CMakeLists.txt', 'recorded_curl.c', 'offline_guard.c')
    }


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('destination', type=Path)
    parser.add_argument('--curl-headers', required=True, type=Path)
    args = parser.parse_args()
    root = Path(__file__).resolve().parent
    subprocess.run(
        [
            'cmake',
            '-S',
            str(root),
            '-B',
            str(args.destination),
            '-DCURL_HEADERS=' + str(args.curl_headers.resolve()),
        ],
        check=True,
    )
    subprocess.run(['cmake', '--build', str(args.destination), '-j', '4'], check=True)
    (args.destination / 'sources.json').write_text(json.dumps(sources()), encoding='utf-8')
