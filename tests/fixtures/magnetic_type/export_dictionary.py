"""Copy item identities from a supplied COMCIFS magnetic dictionary."""

import argparse
import hashlib
import json
import re
from pathlib import Path


def export(dictionary, destination):
    raw = dictionary.read_bytes()
    tags = sorted(set(re.findall(rb"_definition.id\s+['\"](_[^'\"]+)['\"]", raw)))
    destination.write_text(
        json.dumps(
            {
                'source': 'COMCIFS cif_mag.dic 1.1.0-dev (2026-10-30)',
                'sha256': hashlib.sha256(raw).hexdigest(),
                'tags': [tag.decode().lower() for tag in tags if b'_flags_' not in tag],
            },
            indent=2,
        )
        + '\n'
    )


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('dictionary', type=Path)
    parser.add_argument('destination', type=Path)
    args = parser.parse_args()
    export(args.dictionary, args.destination)
