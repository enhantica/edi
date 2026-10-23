"""Require the complete Windows drawing witness, including both Qt web kits."""

import argparse
import hashlib
import itertools
import json
from pathlib import Path

SCENARIOS = (
    'rows',
    'antialiased-border',
    'outer-off',
    'both-clips',
    'layer',
    'cover',
    'structure-table',
    'experiment-table',
    'analysis-table',
    'sidebar-collapse',
    'popup-close',
)
CASES = set(itertools.product(('singlethread', 'multithread'), ('light', 'dark'), SCENARIOS))


def validate(document, head):
    if document.get('complete') is not True or document.get('errors') != []:
        raise ValueError('The Windows witness is incomplete or contains browser errors')
    if document.get('platform') != 'win32' or not document.get('browser'):
        raise ValueError('The witness must identify its actual Windows browser')
    rows = document.get('receipts', [])
    keys = [(row['mode'], row['theme'], row['scenario']) for row in rows]
    if len(keys) != len(CASES) or set(keys) != CASES:
        raise ValueError('Every kit, theme and clipping case must execute exactly once')
    for row in rows:
        if row['build'].get('ediCommit') != head:
            raise ValueError('The Windows artifact must match the exact checked-out head')
        if row.get('status') != 'passed' or not row['state'].get('completed'):
            raise ValueError('A skipped or incomplete input action is not a platform witness')
        if 'ANGLE' not in row['gpu']['renderer'] or not any(
            value in row['gpu']['renderer'] for value in ('D3D11', 'Direct3D11')
        ):
            raise ValueError('The actual browser must exercise Windows ANGLE D3D11')
        pixels = row['pixels']
        if pixels['visibleInside'] <= 0 or pixels['changed'] <= 0:
            raise ValueError('Real content and a real action must reach the pixel observer')
        validate_pixels(row, pixels)
        sources = row['build'].get('sources', {})
        if not any(name.endswith('.qml') for name in sources) or not any(
            name.endswith('.cpp') for name in sources
        ):
            raise ValueError(
                'The artifact must name both native observer and real QML preset sources'
            )


def validate_pixels(row, pixels):
    if row['scenario'] == 'outer-off':
        if pixels['afterOutside'] <= 0:
            raise ValueError('The disabled-clip escape must be exercised')
    elif pixels['visibleOutside'] != 0 or pixels['afterOutside'] != 0:
        raise ValueError('Escaped and stale pixels must match the independent empty reference')
    if row['scenario'] in {'popup-close', 'sidebar-collapse'} and pixels['afterInside'] != 0:
        raise ValueError('Vacated popup and group pixels must match the empty reference')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('directory', type=Path)
    parser.add_argument('head')
    args = parser.parse_args()
    document = json.loads((args.directory / 'receipt.json').read_text())
    validate(document, args.head)
    for row in document['receipts']:
        for phase in ('background', 'visible', 'after'):
            path = args.directory / f'{row["mode"]}-{row["theme"]}-{row["scenario"]}-{phase}.png'
            if (
                not path.is_file()
                or hashlib.sha256(path.read_bytes()).hexdigest() != row['screenshots'][phase]
            ):
                raise ValueError(
                    'Every compared screenshot must be retained with its original content hash'
                )
    print('Complete Windows clipping witness accepted')


if __name__ == '__main__':
    main()
