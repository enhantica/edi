"""Extract 's independent oracle; never import edi or its element table.

Run with --source pointing at a local diffraction-lib checkout. Only the two
literal dictionaries from the plan's frozen published data module are read.
"""

import argparse
import ast
import csv
import hashlib
import io
import json
import subprocess
from pathlib import Path

COMMIT = 'c0654956a1281f1ea3f3467c3367167f93edee18'
MODULE = 'src/easydiffraction/display/structure/assets/elements.py'


def generate(source: Path, output: Path) -> None:
    raw = subprocess.check_output(['git', '-C', str(source), 'show', f'{COMMIT}:{MODULE}'])
    tables = {}
    for node in ast.parse(raw).body:
        if (
            isinstance(node, ast.AnnAssign)
            and isinstance(node.target, ast.Name)
            and node.target.id in {'ELEMENT_RADII', 'ELEMENT_COLORS'}
        ):
            tables[node.target.id] = ast.literal_eval(node.value)
    radii, colors = tables['ELEMENT_RADII'], tables['ELEMENT_COLORS']
    if list(radii) != list(colors) or len(radii) != 118:
        raise ValueError(' I6 upstream table must cover H through Og in matching order')
    text = io.StringIO()
    writer = csv.writer(text, delimiter='\t', lineterminator='\n')
    writer.writerow(['symbol', 'jmol', 'vesta', 'covalent', 'van_der_waals', 'ionic'])
    for symbol, models in radii.items():
        palette = colors[symbol]

        def rgb(value):
            return '' if value is None else '#' + ''.join(f'{channel:02X}' for channel in value)

        writer.writerow([
            symbol,
            rgb(palette['jmol']),
            rgb(palette.get('vesta')),
            models['covalent'],
            models['vdw'],
            '' if models.get('ionic') is None else models['ionic'],
        ])
    output.mkdir(parents=True, exist_ok=True)
    fixture = text.getvalue().encode()
    (output / 'published-elements.tsv').write_bytes(fixture)
    provenance = {
        'source': 'https://github.com/easyscience/diffraction-lib',
        'commit': COMMIT,
        'file': MODULE,
        'source_sha256': hashlib.sha256(raw).hexdigest(),
        'fixture_sha256': hashlib.sha256(fixture).hexdigest(),
        'licences': ['BSD-3-Clause', 'MIT'],
        'published_sources': [
            'EasyDiffractionBeta easyDiffractionApp/Logic/Tables.py PERIODIC_TABLE',
            'pymatgen src/pymatgen/vis/ElementColorSchemes.yaml VESTA',
            'pymatgen dev_scripts/periodic_table_resources/Shannon_Radii.csv',
        ],
        'selection_rule': 'diffraction-lib assets/LICENSES.md representative-radius selection',
        'command': 'python tests/fixtures/e04_t10/generate.py --source <diffraction-lib-checkout>',
    }
    (output / 'provenance.json').write_text(json.dumps(provenance, indent=2) + '\n')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, required=True)
    parser.add_argument('--output', type=Path, default=Path(__file__).parent)
    args = parser.parse_args()
    generate(args.source, args.output)
