# SPDX-License-Identifier: BSD-3-Clause
"""Capture section outlines from an independently supplied tutorial repository."""

import argparse
import hashlib
import json
import re
import subprocess
from pathlib import Path


def headings(text):
    result = []
    for line in text.splitlines():
        match = re.match(r'^# (#{2}) (.+)', line)
        if match:
            title = re.sub(r'^[^\w]+', '', match[2]).strip()
            result.append(title)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('repository', type=Path)
    parser.add_argument('commit')
    parser.add_argument('output', type=Path)
    parser.add_argument('sources', nargs='+', help='Published notebook stem=reference blob')
    args = parser.parse_args()
    entries = {}
    for source in args.sources:
        name, blob = source.split('=', 1)
        payload = subprocess.check_output(['git', '-C', str(args.repository), 'show', blob])
        entries[name] = {
            'blob': blob,
            'sha256': hashlib.sha256(payload).hexdigest(),
            'sections': headings(payload.decode()),
        }
    args.output.write_text(
        json.dumps(
            {
                'reference': 'https://github.com/easyscience/diffraction-lib',
                'commit': args.commit,
                'scope': 'Corresponding technique; unmatched material uses its technique outline',
                'notebooks': entries,
            },
            indent=2,
            ensure_ascii=False,
        )
        + '\n'
    )


if __name__ == '__main__':
    main()
