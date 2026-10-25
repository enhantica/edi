"""Remove executable location metadata while retaining its hash and every reference value."""

import json
from pathlib import Path

HERE = Path(__file__).resolve().parent


def main():
    for relative in ('fullprof.json', 'fitting/fullprof.json'):
        path = HERE / relative
        reference = json.loads(path.read_text())
        if not reference.get('fp2k_sha256'):
            message = 'Executable location removal must retain the binary digest'
            raise ValueError(message)
        reference.pop('fp2k', None)
        path.write_text(json.dumps(reference, indent=2) + '\n')


if __name__ == '__main__':
    main()
