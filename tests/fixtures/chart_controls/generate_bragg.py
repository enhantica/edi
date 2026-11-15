"""Generate Bragg boundaries from approved design bytes and ADR-0084 positions."""

import json
import re
from pathlib import Path

from tests.fixtures.approved_palettes.reference import gradient

ROOT = Path(__file__).resolve().parents[3]
TOKENS = ['main', 'colourBlindSafe']


def approved_palettes():
    source = (ROOT / 'data/palettes/PROVENANCE.md').read_text()
    palettes = []
    for title in ('Main', 'Colour-blind safe'):
        block = source.split(f'### {title}\n', 1)[1].split('\n### ', 1)[0]
        rows = re.findall(
            r'^\| figure \| (\d+) \| `(#[0-9A-F]{6})` \| `(#[0-9A-F]{6})` \|$',
            block,
            re.MULTILINE,
        )
        if [int(row[0]) for row in rows] != list(range(11)):
            raise ValueError('Each approved palette must list its eleven ordered design colours')
        palettes.append({
            'name': title,
            'light': [row[1] for row in rows],
            'dark': [row[2] for row in rows],
        })
    return palettes


def main():
    palettes = approved_palettes()
    output = [
        '#pragma once',
        '#include <cstddef>',
        '#include <string>',
        '#include <vector>',
        'namespace figure_bragg {',
        (
            'struct Case { std::string scheme; std::size_t count, palette_size; bool dark; '
            'std::vector<std::size_t> positions; std::vector<std::string> colours; };'
        ),
        'inline const std::vector<Case> cases{',
    ]
    for token, palette in zip(TOKENS, palettes, strict=True):
        # Both current palettes reserve experiment positions 0 and 1 (ADR-0084).
        start = 2
        for count in (1, 2, 5, 6, 9, 10, 11, 17, 162):
            positions = list(range(start, start + count))
            size = positions[-1] + 1
            for theme in ('light', 'dark'):
                colours = palette[theme]
                expected = [
                    colours[position]
                    if position < 11
                    else gradient(colours[0], colours[1], (position - 10) / (size - 10))
                    for position in positions
                ]
                output.append(
                    '{'
                    + json.dumps(token)
                    + ','
                    + str(count)
                    + ','
                    + str(size)
                    + ','
                    + str(theme == 'dark').lower()
                    + ',{'
                    + ','.join(map(str, positions))
                    + '},{'
                    + ','.join(map(json.dumps, expected))
                    + '}},'
                )
    output.extend(['};', '}'])
    Path(__file__).with_name('bragg.hpp').write_text('\n'.join(output) + '\n')


if __name__ == '__main__':
    main()
