"""Freeze owner records without importing any edi implementation."""

import argparse
import hashlib
import json
import re
from pathlib import Path

NAMES = [
    ('earth', 'Earth'),
    ('standard', 'Classic'),
    ('soft', 'Soft'),
    ('natural', 'Natural'),
    ('clear', 'Colour-blind safe'),
]


def section(text, title):
    return text.split(title, 1)[1].split('\n## ', 1)[0]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('records', type=Path)
    parser.add_argument('--elements', type=Path, required=True)
    args = parser.parse_args()
    raw = args.records.read_bytes()
    text = raw.decode()
    light = section(
        text,
        'five palettes and the calc red, light mode',
    )
    dark = section(
        text,
        'dark colours calmer, shades beyond 11 items',
    )
    palettes = []
    for old, name in NAMES:
        row = {'name': name}
        for theme, block in [('light', light), ('dark', dark)]:
            line = re.search(r'^- edi ' + old + r': (.*)$', block, re.MULTILINE)[1]
            row[theme] = re.findall(r'#[0-9A-F]{6}', line)
            if len(row[theme]) != 11:
                raise ValueError('Each owner palette must have eleven colours')
        palettes.append(row)
    output = {
        'source': 'Approved palette design records dated 2026-10-26 and 2026-10-27',
        'source_sha256': hashlib.sha256(raw).hexdigest(),
        'palettes': palettes,
        'calc': {'light': '#AD1A6B', 'dark': '#FC4F81'},
        'maps': ['Blue-Red', 'Viridis', 'Batlow', 'Inferno', 'Lapaz', 'Greys'],
        'blue_red': {
            'light': ['#FFFFFF', '#3F7FBF', '#C8323C'],
            'dark': ['#181818', '#6AA6EA', '#FC4F81'],
        },
    }
    Path(__file__).with_name('element-styles.tsv').write_bytes(args.elements.read_bytes())
    Path(__file__).with_name('owner.json').write_text(json.dumps(output, indent=2) + '\n')


if __name__ == '__main__':
    main()
