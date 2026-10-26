"""Capture the owner-supplied 2026-10-23 CIF without changing its published values."""

import argparse
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('source', type=Path, nargs='?')
    args = parser.parse_args()
    row = json.loads((HERE / 'wyckoff_sources.json').read_text())['owner-tbti']
    target = HERE / row['file']
    raw = args.source.read_bytes() if args.source else target.read_bytes()
    if hashlib.sha256(raw).hexdigest() != row['fixture_sha256']:
        message = 'The owner-supplied fixture must match its independently captured content'
        raise RuntimeError(message)
    if args.source:
        target.write_bytes(raw)


if __name__ == '__main__':
    main()
