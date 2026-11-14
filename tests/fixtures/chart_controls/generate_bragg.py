"""Generate Bragg boundary values from owner colours and ADR-0038's position rule."""

import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path

from tests.fixtures.approved_palettes.reference import gradient

ROOT = Path(__file__).resolve().parents[3]
TOKENS = ['earth', 'classic', 'soft', 'natural', 'colourBlindSafe']
PUBLISHED = 'b16f9867ef1de464dfed731796848eb5ba60e739'
PUBLISHED_SOURCE = 'data/palettes/PROVENANCE.md'
PUBLISHED_SHA256 = '591fed1c9bf8ccb6ba8e1ad4fc24b34311449d7f3af25f6995e35807091c9905'


def published_palettes():
    """Read approved owner values from the immutable published release document."""
    raw = subprocess.check_output([
        'git',
        '-C',
        str(ROOT),
        'show',
        PUBLISHED + ':' + PUBLISHED_SOURCE,
    ])
    if hashlib.sha256(raw).hexdigest() != PUBLISHED_SHA256:
        raise ValueError('The independently published palette reference changed')
    text = raw.decode('utf-8')
    palettes = []
    for name in ('Main', 'Colour-blind safe'):
        section = text.split('### ' + name + '\n', 1)[1].split('\n### ', 1)[0]
        rows = re.findall(
            r'^\| figure \| ([0-9]+) \| `(#[0-9A-F]{6})` \| `(#[0-9A-F]{6})` \|$',
            section,
            re.MULTILINE,
        )
        if [int(row[0]) for row in rows] != list(range(11)):
            raise ValueError('Every approved palette retains exactly its eleven ordered colours')
        palettes.append({
            'name': name,
            'light': [r[1] for r in rows],
            'dark': [r[2] for r in rows],
            'roles': {
                role: {'light': light, 'dark': dark}
                for role, light, dark in re.findall(
                    r'^\| (total_calculation|background|difference) \| 0 \| '
                    r'`(#[0-9A-F]{6})` \| `(#[0-9A-F]{6})` \|$',
                    section,
                    re.MULTILINE,
                )
            },
        })
    if any(
        set(palette['roles']) != {'total_calculation', 'background', 'difference'}
        for palette in palettes
    ):
        raise ValueError('Every approved palette retains all three curve roles')
    return palettes


def main():
    if sys.argv[1:] not in ([], ['--current']):
        raise SystemExit('usage: generate_bragg.py [--current]')
    current = sys.argv[1:] == ['--current']
    palettes = (
        published_palettes()
        if current
        else json.loads(Path(__file__).with_name('owner.json').read_text())['palettes']
    )
    tokens = ['main', 'colourBlindSafe'] if current else TOKENS
    namespace = 'figure_bragg_current' if current else 'figure_bragg'
    output = [
        '#pragma once',
        '#include <cstddef>',
        '#include <string>',
        '#include <vector>',
        'namespace ' + namespace + ' {',
        (
            'struct Case { std::string scheme; std::size_t count, palette_size; bool dark; '
            'std::vector<std::size_t> positions; std::vector<std::string> colours; };'
        ),
        'inline const std::vector<Case> cases{',
    ]
    for token, palette in zip(tokens, palettes, strict=True):
        start = 2 if current or palette['name'] == 'Earth' else 1
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
    if current:
        output[:0] = [
            '// Approved colours: ' + PUBLISHED + ':' + PUBLISHED_SOURCE,
            '// Source SHA-256: ' + PUBLISHED_SHA256,
        ]
    target = 'bragg-current.hpp' if current else 'bragg.hpp'
    Path(__file__).with_name(target).write_text('\n'.join(output) + '\n', newline='\n')


if __name__ == '__main__':
    main()
