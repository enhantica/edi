"""Copy the approved colour coordinates without importing the application."""

import argparse
import hashlib
import json
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source', type=Path)
    args = parser.parse_args()
    raw = args.source.read_bytes()
    palettes = []
    for option in json.loads(raw)['options']:
        row = {'name': option['name'], 'default': option.get('default', False)}
        for theme in ('light', 'dark'):
            colours = [item['hex'] for item in option[theme]]
            row[theme] = {
                'structures': colours[:5],
                'measured': colours[5:10],
                'total_calculation': colours[10],
                'background': colours[11],
                'difference': colours[12],
            }
        palettes.append(row)
    Path(__file__).with_name('colours.json').write_text(
        json.dumps(
            {
                'source_sha256': hashlib.sha256(raw).hexdigest(),
                'palettes': palettes,
            },
            indent=2,
        )
        + '\n'
    )


if __name__ == '__main__':
    main()
