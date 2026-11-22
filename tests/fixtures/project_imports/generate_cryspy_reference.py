"""Freeze cryspy's unmodified functional-test project from a libraries snapshot."""

import argparse
import hashlib
import json
from pathlib import Path

RELATIVE = Path('cryspy/tests/functional/PbSO4_unpol_powder_test/main.rcif')
SOURCE_BLOB = '4f50b8e4eecc0ec07e8c1df3901893e3a9ea591c'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('libraries', type=Path)
    arguments = parser.parse_args()
    payload = (arguments.libraries / RELATIVE).read_bytes()
    blob = hashlib.sha1(
        b'blob ' + str(len(payload)).encode() + b'\0' + payload, usedforsecurity=False
    ).hexdigest()
    if blob != SOURCE_BLOB:
        parser.error('The input must match the recorded upstream cryspy project blob')
    destination = Path(__file__).resolve().parent
    (destination / 'cryspy-pbso4.rcif').write_bytes(payload)
    (destination / 'cryspy-LICENSE').write_bytes(
        (arguments.libraries / 'cryspy/LICENSE').read_bytes()
    )
    (destination / 'cryspy-pbso4.json').write_text(
        json.dumps(
            {
                'source': str(RELATIVE),
                'libraries_snapshot': 'fff6d6ee34352bd05b2d650bdad9320ec6c5c5f8',
                'source_git_blob': SOURCE_BLOB,
                'sha256': hashlib.sha256(payload).hexdigest(),
                'transformations': [],
            },
            indent=2,
        )
        + '\n',
        encoding='utf-8',
    )


if __name__ == '__main__':
    main()
