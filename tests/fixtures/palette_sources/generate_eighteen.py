"""Freeze numeric facts from primary publishers; never import production code.

Run with --source-dir containing the documents named by sources.json. Designs
are inspired by owner-supplied references, and intentionally carry no numeric pin.
The previous five-scheme fixture retains the independently captured map tables.
"""

import argparse
import hashlib
import json
import re
from pathlib import Path

from generate import tol_colours

HERE = Path(__file__).parent


def generate(directory):
    old = json.loads((HERE / 'reference-five.json').read_text())
    manifest = json.loads((HERE / 'captured-sources.json').read_text())
    documents = {name: (directory / name).read_bytes() for name in manifest}
    for name, document in documents.items():
        if hashlib.sha256(document).hexdigest() != manifest[name]['sha256']:
            raise ValueError('Publisher capture changed: ' + name)

    def text(name):
        return documents[name].decode()

    def d3(name):
        packed = re.search(r'colors\("([0-9a-f]+)"\)', text(name))[1]
        return ['#' + packed[i : i + 6].upper() for i in range(0, len(packed), 6)]

    def carbon(theme):
        block = (
            text('carbon.js').split('export const categorical' + theme + ' = [')[1].split('];')[0]
        )
        return ['#' + colour.upper() for colour in re.findall(r"hex: '([0-9a-f]{6})'", block)]

    def brewer(name, count):
        data = json.loads(text('brewer.json'))[name][str(count)]
        return [
            '#' + ''.join(f'{int(v):02X}' for v in re.findall(r'\d+', colour)) for colour in data
        ]

    def apple(theme):
        data = json.loads(text('apple.json'))['references']
        values = []
        for name, row in data.items():
            if re.fullmatch('colors-unified-[a-z]+-' + theme + r'\.png', name):
                channels = re.findall(r'[RGB]-(\d+)', row.get('alt', ''))
                if len(channels) == 3:
                    values.append('#' + ''.join(f'{int(v):02X}' for v in channels))
        if len(values) != 12:
            raise ValueError(
                'The Apple primary regular-contrast table must contain twelve system colours'
            )
        return values

    tol = text('tol.html')
    bright, muted = tol_colours(tol, 'fig:scheme_bright'), tol_colours(tol, 'fig:scheme_muted')
    okabe = next(row for row in old['schemes'] if row['id'] == 'colourBlindSafe')['pattern']
    nord = re.findall(r'\$nord\d+:\s*(#[0-9a-fA-F]{6})', text('nord.scss'))
    solarized = re.findall(r'\$\w+:\s*(#[0-9a-fA-F]{6})', text('solarized.md'))
    cat = json.loads(text('catppuccin.json'))
    themes = {
        theme: [row['hex'] for row in cat[flavour]['colors'].values()]
        for theme, flavour in [('light', 'latte'), ('dark', 'mocha')]
    }
    petroff = [
        '#' + value.upper() for value in re.findall(r"'([0-9a-f]{6})'", text('petroff.mplstyle'))
    ]
    schemes = []
    inspirations = [
        'https://www.design-seeds.com/',
        'https://akulakreative.com/',
        'https://www.paperheartdesign.com/',
    ]

    def add(identity, label, light, dark=None, kind='published', urls=None):
        dark = light if dark is None else dark
        schemes.append({
            'id': identity,
            'label': label,
            'kind': kind,
            'pattern': sorted(set(light + dark)),
            'structure': sorted(set(light + dark)),
            'sources_by_theme': {'light': light, 'dark': dark},
            'source_urls': urls or [],
        })

    for identity, label in [
        ('coast', 'Coast'),
        ('garden', 'Garden'),
        ('peaceful', 'Peaceful'),
        ('fogForest', 'Fog forest'),
        ('sage', 'Sage'),
    ]:
        add(identity, label, [], kind='design', urls=inspirations)
    add('okabeIto', 'Okabe-Ito', okabe, urls=[old['sources']['okabe.html']['url']])
    add('paulTolBright', 'Paul Tol bright', bright, urls=[manifest['tol.html']['url']])
    add('paulTolMuted', 'Paul Tol muted', muted, urls=[manifest['tol.html']['url']])
    add('tableau', 'Tableau 10', d3('d3-tableau.js'), urls=[manifest['d3-tableau.js']['url']])
    add(
        'observable',
        'Observable 10',
        d3('d3-observable.js'),
        urls=[manifest['d3-observable.js']['url']],
    )
    add(
        'carbon',
        'IBM Carbon',
        carbon('Light'),
        carbon('Dark'),
        urls=[manifest['carbon.js']['url']],
    )
    add('dark2', 'ColorBrewer Dark2', brewer('Dark2', 8), urls=[manifest['brewer.json']['url']])
    add('petroff', 'Petroff', petroff, urls=[manifest['petroff.mplstyle']['url']])
    add('vivid', 'Vivid', brewer('Set1', 9), urls=[manifest['brewer.json']['url']])
    add('nord', 'Nord', nord, kind='theme', urls=[manifest['nord.scss']['url']])
    add('solarized', 'Solarized', solarized, kind='theme', urls=[manifest['solarized.md']['url']])
    add(
        'catppuccin',
        'Catppuccin',
        themes['light'],
        themes['dark'],
        kind='theme',
        urls=[manifest['catppuccin.json']['url']],
    )
    add(
        'apple',
        'Apple',
        apple('light'),
        apple('dark'),
        kind='theme',
        urls=[manifest['apple.json']['url']],
    )
    result = {
        'claim': (
            'Primary publisher coordinates; owner-inspired designs have no generated-output pin'
        ),
        'wcag': old['wcag'],
        'oklab': 'https://bottosson.github.io/posts/oklab/',
        'sources': {**old['sources'], **manifest},
        'default': 'coast',
        'schemes': schemes,
        'published_maps': {row['id']: row['gradient'] for row in old['schemes']},
        'calc_hue_range': {
            'claim': (
                'Short OKLCH hue arc between the two independently specified calculated colours'
            ),
            'light': '#F44336',
            'dark': '#EF9A9A',
        },
        'provenance_mapping': (
            'Under the named scheme heading: each categorical row cites '
            'either source/light/dark or source-light/source-dark/light/dark RGB values. '
            'An unchanged source may cite its own RGB directly.'
        ),
    }
    (HERE / 'reference.json').write_text(json.dumps(result, indent=2) + '\n')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source-dir', type=Path, required=True)
    generate(parser.parse_args().source_dir)
