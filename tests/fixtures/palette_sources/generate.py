"""Freeze published numeric palettes without importing any product code.

The cached publisher documents are supplied with --source-dir. Source hashes
identify the exact documents; only colour facts, not publisher code, are stored.
"""

import argparse
import ast
import hashlib
import json
import re
from pathlib import Path

HERE = Path(__file__).parent
URLS = {
    'matplotlib.py': 'https://raw.githubusercontent.com/matplotlib/matplotlib/v3.10.8/lib/matplotlib/_cm_listed.py',
    'matplotlib-categorical.py': 'https://raw.githubusercontent.com/matplotlib/matplotlib/v3.10.8/lib/matplotlib/_cm.py',
    'material.scss': 'https://raw.githubusercontent.com/material-components/material-components-web/v14.0.0/packages/mdc-theme/_color-palette.scss',
    'brewer.json': 'https://colorbrewer2.org/export/colorbrewer.json',
    'tol.html': 'https://sronpersonalpages.nl/~pault/',
    'okabe.html': 'https://jfly.uni-koeln.de/color/',
}


def hex_rgb(rgb):
    return '#' + ''.join(f'{round(value * 255):02X}' for value in rgb[:3])


def tol_colours(html, anchor):
    figure = re.search(
        r'<figure[^>]*id="' + re.escape(anchor) + r'"[^>]*>(.*?)</figure>', html, re.DOTALL
    )
    if figure is None:
        raise ValueError('The publisher must retain its named colour figure: ' + anchor)
    paragraph = re.search(r'<p>Colours[^<]+</p>', figure[1])
    if paragraph is None:
        raise ValueError('The publisher figure must carry its actual numeric colour list')
    return re.findall(r'#[0-9A-Fa-f]{6}', paragraph[0].split('Bad data:')[0])


def generate(directory):
    documents = {name: (directory / name).read_bytes() for name in URLS}
    tables = {}
    for node in ast.parse(documents['matplotlib.py']).body:
        if isinstance(node, ast.Assign) and isinstance(node.targets[0], ast.Name):
            name = node.targets[0].id
            if name in {'_viridis_data', '_cividis_data', '_plasma_data', '_magma_data'}:
                tables[name[1:-5]] = [hex_rgb(rgb) for rgb in ast.literal_eval(node.value)]
    if set(tables) != {'viridis', 'cividis', 'plasma', 'magma'}:
        raise ValueError('All four pinned publisher colormaps must be captured')
    categorical = {}
    for node in ast.parse(documents['matplotlib-categorical.py']).body:
        if (
            isinstance(node, ast.Assign)
            and isinstance(node.targets[0], ast.Name)
            and node.targets[0].id in {'_tab10_data', '_tab20b_data'}
        ):
            categorical[node.targets[0].id] = [
                hex_rgb(value) for value in ast.literal_eval(node.value)
            ]
    material = sorted(set(re.findall(r'#[0-9A-Fa-f]{6}', documents['material.scss'].decode())))
    brewer = json.loads(documents['brewer.json'])
    vivid = []
    for name, count in [('Dark2', '8'), ('Set1', '9')]:
        for text in brewer[name][count]:
            rgb = list(map(int, re.findall(r'\d+', text)))
            vivid.append('#' + ''.join(f'{v:02X}' for v in rgb))
    tol = documents['tol.html'].decode()
    bright = tol_colours(tol, 'fig:scheme_bright')
    muted = tol_colours(tol, 'fig:scheme_muted')
    iridescent = tol_colours(tol, 'fig:scheme_iridescent')
    # Numeric coordinates of the eight swatches in Okabe/Ito's Fig. 16.
    okabe = [
        '#000000',
        '#E69F00',
        '#56B4E9',
        '#009E73',
        '#F0E442',
        '#0072B2',
        '#D55E00',
        '#CC79A7',
    ]
    # Tableau 10, the published Matplotlib default cycle (rcsetup.py,
    # same 3.10.8 release as the captured colormap table).
    tableau = [
        '#1F77B4',
        '#FF7F0E',
        '#2CA02C',
        '#D62728',
        '#9467BD',
        '#8C564B',
        '#E377C2',
        '#7F7F7F',
        '#BCBD22',
        '#17BECF',
    ]
    schemes = [
        ('default', 'Default', material, material, tables['viridis']),
        ('colourBlindSafe', 'Colour-blind safe', okabe, muted, tables['cividis']),
        ('tableau', 'Tableau', tableau, categorical['_tab20b_data'], tables['plasma']),
        ('paulTol', 'Paul Tol', bright, tol_colours(tol, 'fig:scheme_highcontrast'), iridescent),
        ('vivid', 'Vivid', vivid[8:], vivid[:8], tables['magma']),
    ]
    reference = {
        'claim': 'Independent published source coordinates, not product-generated colours',
        'wcag': 'https://www.w3.org/TR/WCAG22/#dfn-relative-luminance',
        'sources': {
            name: {'url': URLS[name], 'sha256': hashlib.sha256(data).hexdigest()}
            for name, data in documents.items()
        },
        'tableau_source': 'https://github.com/matplotlib/matplotlib/blob/v3.10.8/lib/matplotlib/rcsetup.py',
        'required_pattern_hues': {
            'default': [
                '#03A9F4',
                '#795548',
                '#4CAF50',
                '#9C27B0',
                '#FFC107',
                '#3F51B5',
                '#00BCD4',
                '#CDDC39',
            ],
            'colourBlindSafe': okabe,
            'tableau': tableau,
            'paulTol': bright,
            'vivid': vivid[8:],
        },
        'adaptation_tolerance': (
            'Half an encoded 8-bit sRGB channel; independent Oklab bounds over all '
            'eight quantisation-box vertices'
        ),
        'schemes': [
            {
                'id': name,
                'label': label,
                'pattern': pattern,
                'structure': structure,
                'gradient': gradient,
            }
            for name, label, pattern, structure, gradient in schemes
        ],
    }
    (HERE / 'reference.json').write_text(json.dumps(reference, indent=2) + '\n')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source-dir', required=True, type=Path)
    generate(parser.parse_args().source_dir)
