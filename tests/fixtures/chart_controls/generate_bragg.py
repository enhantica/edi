"""Generate Bragg boundary values from owner colours and ADR-0038's position rule."""

import json
from pathlib import Path

from tests.fixtures.approved_palettes.reference import gradient

ROOT = Path(__file__).resolve().parents[3]
TOKENS = ['earth', 'classic', 'soft', 'natural', 'colourBlindSafe']


def main():
    palettes = json.loads(Path(__file__).with_name('owner.json').read_text())['palettes']
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
        start = 2 if palette['name'] == 'Earth' else 1
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
