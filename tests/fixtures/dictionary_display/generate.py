"""Freeze the upstream name inventory without importing either product."""

import argparse
import hashlib
import json
import shutil
import subprocess
from pathlib import Path

ANCHOR = '0ffba46f'
INVENTORY = 'docs/dev/adrs/accepted/edstar-project-persistence/handler-inventory.json'


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('upstream', type=Path)
    args = parser.parse_args()
    raw = subprocess.check_output([
        shutil.which('git'),
        '-C',
        str(args.upstream),
        'show',
        f'{ANCHOR}:{INVENTORY}',
    ])
    payload = {
        'source': 'https://github.com/easyscience/diffraction-lib',
        'anchor': ANCHOR,
        'path': INVENTORY,
        'sha256': hashlib.sha256(raw).hexdigest(),
        'entries': [
            {key: row[key] for key in ('unique_name', 'edi_names', 'cif_names')}
            for row in json.loads(raw)['entries']
        ],
    }
    Path(__file__).with_name('upstream-names.json').write_text(
        json.dumps(payload, indent=2) + '\n'
    )


if __name__ == '__main__':
    main()
