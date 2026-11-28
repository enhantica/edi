"""Copy selected byte-pinned CIFs from an existing local COD cache."""

import argparse
import csv
import hashlib
from pathlib import Path

ENTRIES = ('1000003', '1000007', '1010067')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('cache', type=Path)
    parser.add_argument('census', type=Path)
    parser.add_argument('output', type=Path)
    parser.add_argument('--keep-source-header', action='store_true')
    args = parser.parse_args()
    with args.census.open(newline='', encoding='utf-8') as stream:
        rows = {row['cod_entry_id']: row for row in csv.DictReader(stream)}
    fixtures = {}
    for entry in ENTRIES:
        name = f'{entry}.cif'
        payload = (args.cache / name).read_bytes()
        if hashlib.sha256(payload).hexdigest() != rows[entry]['cif_sha256']:
            parser.error(f'{name} differs from its pinned census revision')
        if not args.keep_source_header:
            # Keep the revision and scientific payload while omitting the checkout URL.
            payload = b''.join(
                line
                for line in payload.splitlines(keepends=True)
                if not line.startswith(b'#$URL: ')
            )
        fixtures[name] = payload
    args.output.mkdir(parents=True, exist_ok=True)
    for name, payload in fixtures.items():
        (args.output / name).write_bytes(payload)


if __name__ == '__main__':
    main()
