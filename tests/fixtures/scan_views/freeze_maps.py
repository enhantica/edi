"""Freeze published colour tables without importing the application."""

import argparse
import ast
import hashlib
import json
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source', type=Path)
    parser.add_argument('--names', nargs='+', required=True)
    parser.add_argument('--source-url', required=True)
    parser.add_argument('--license', required=True)
    parser.add_argument('--license-source', required=True)
    args = parser.parse_args()
    raw = args.source.read_bytes()
    maps = {}
    for node in ast.parse(raw).body:
        if not isinstance(node, ast.Assign):
            continue
        name = getattr(node.targets[0], 'id', '')
        if name.removeprefix('_').removesuffix('_data') not in args.names:
            continue
        values = ast.literal_eval(node.value)
        if len(values) != 256 or any(len(row) != 3 for row in values):
            continue
        maps[name.removeprefix('_').removesuffix('_data')] = {
            'source': args.source_url,
            'source_sha256': hashlib.sha256(raw).hexdigest(),
            'license': args.license,
            'license_source': args.license_source,
            'colours': ['#' + ''.join(f'{round(c * 255):02X}' for c in row) for row in values],
        }
    Path(__file__).with_name('maps.json').write_text(json.dumps(maps, indent=2) + '\n')


if __name__ == '__main__':
    main()
