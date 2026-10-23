"""Freeze independent upstream candidate tables; never read application colour data."""

import argparse
import ast
import hashlib
import json
import re
from pathlib import Path

from tests.fixtures.approved_palettes.reference import gradient


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('upstream', type=Path)
    parser.add_argument('--output', type=Path, default=Path(__file__).with_name('maps.json'))
    args = parser.parse_args()
    references = json.loads(args.output.read_text())

    def freeze(name, relative, url, license_id, license_relative, license_url, rows=None):
        raw = (args.upstream / relative).read_bytes()
        if rows is None:
            triples = [
                [float(v) for v in line.replace(',', ' ').split()]
                for line in raw.decode().splitlines()
                if line.strip()
            ]
            if len(triples) != 256 or any(len(row) != 3 for row in triples):
                raise ValueError('A source table must contain exactly 256 RGB triples')
            rows = ['#' + ''.join(f'{round(c * 255):02X}' for c in row) for row in triples]
        references[name] = {
            'source': url,
            'source_sha256': hashlib.sha256(raw).hexdigest(),
            'license': license_id,
            'license_source': license_url,
            'license_sha256': hashlib.sha256(
                (args.upstream / license_relative).read_bytes()
            ).hexdigest(),
            'colours': rows,
        }

    crameri = 'https://raw.githubusercontent.com/callumrollo/cmcrameri/78f02a088fa3c4fb4cb8aa92bd8e52389ab9d09a/'
    for name in ['batlow', 'oslo', 'lajolla', 'acton', 'devon', 'lapaz']:
        freeze(
            name,
            f'crameri/{name}.txt',
            crameri + f'cmcrameri/cmaps/{name}.txt',
            'MIT',
            'crameri/LICENSE',
            crameri + 'LICENSE',
        )
    cmocean = 'https://raw.githubusercontent.com/matplotlib/cmocean/59c35002c3aa5296b65d9646e52604c627441eb6/'
    for name in ['thermal', 'haline', 'deep', 'dense', 'ice', 'tempo']:
        freeze(
            name,
            f'cmocean/{name}-rgb.txt',
            cmocean + f'cmocean/rgb/{name}-rgb.txt',
            'MIT',
            'cmocean/LICENSE.txt',
            cmocean + 'LICENSE.txt',
        )
    cet = 'https://raw.githubusercontent.com/holoviz/colorcet/076eb84bf86c222cdac830073990f1a08c99778b/'
    for name, file in [
        ('cet-gouldian', 'linear_kbgoy_20-95_c57_n256.csv'),
        ('cet-l08', 'linear_bmy_10-95_c78_n256.csv'),
        ('cet-l06', 'linear_kbc_5-95_c73_n256.csv'),
        ('cet-l17', 'linear_worb_100-25_c53_n256.csv'),
        ('cet-l18', 'linear_wyor_100-45_c55_n256.csv'),
    ]:
        freeze(
            name,
            'cet/' + file,
            cet + 'assets/CET/' + file,
            'CC-BY-4.0',
            'cet/colorcet-LICENSE.txt',
            cet + 'LICENSE.txt',
        )
    turbo = args.upstream / 'turbo/turbo_colormap.py'
    for node in ast.parse(turbo.read_text()).body:
        if (
            isinstance(node, ast.Assign)
            and getattr(node.targets[0], 'id', '') == 'turbo_colormap_data'
        ):
            values = ast.literal_eval(node.value)
            rows = ['#' + ''.join(f'{round(c * 255):02X}' for c in row) for row in values]
            freeze(
                'turbo',
                'turbo/turbo_colormap.py',
                'https://gist.githubusercontent.com/mikhailov-work/ee72ba4191942acecc03fe6da94fc73f/raw/dccf2856de98e3c60c7f0ac8acf3c33d9726dfb8/turbo_colormap.py',
                'Apache-2.0',
                'apache-2.0.txt',
                'https://www.apache.org/licenses/LICENSE-2.0.txt',
                rows,
            )
    brewer = 'https://raw.githubusercontent.com/axismaps/colorbrewer/7d135fc4e19eda73f2eb1bf55fcdf4a04fe4881f/'
    source = (args.upstream / 'colorbrewer/colorbrewer_schemes.js').read_text()
    for name in ['YlGnBu', 'PuBu', 'GnBu', 'Blues', 'Greys', 'Purples', 'YlOrRd', 'YlOrBr']:
        section = re.search(r'^' + name + r':.*?\b9:\s*(\[[^\]]+\])', source, re.MULTILINE)
        if not section:
            raise ValueError('Missing independent nine-class sequential scheme ' + name)
        stops = [
            '#' + ''.join(f'{int(c):02X}' for c in re.findall(r'\d+', rgb))
            for rgb in ast.literal_eval(section[1])
        ]
        rows = []
        for index in range(256):
            position = 8 * index / 255
            segment = min(7, int(position))
            rows.append(gradient(stops[segment], stops[segment + 1], position - segment))
        freeze(
            name.lower(),
            'colorbrewer/colorbrewer_schemes.js',
            brewer + 'colorbrewer_schemes.js',
            'Apache-2.0',
            'colorbrewer/LICENCE.txt',
            brewer + 'LICENCE.txt',
            rows,
        )
    args.output.write_text(json.dumps(references, indent=2) + '\n')


if __name__ == '__main__':
    main()
