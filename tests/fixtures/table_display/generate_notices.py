"""Freeze the shipped notice input independently of ApplicationInfo and QML."""

import hashlib
import json
import re
import textwrap
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
source = ROOT / 'THIRD-PARTY-NOTICES'
text = source.read_text()
catalogue = ROOT / 'DEPENDENCIES.md'
rows = []
header = []
for line in catalogue.read_text().splitlines():
    if not line.startswith('|'):
        header = []
        continue
    cells = [cell.strip() for cell in line.strip('|').split('|')]
    if cells[0] == 'Component':
        header = cells
        continue
    if not header or cells[0].startswith('---') or len(cells) != len(header):
        continue
    item = dict(zip(header, cells, strict=True))
    carried = item['Desktop app']
    if carried in {'', '—'}:
        continue
    version = re.search(r'\(([0-9][0-9A-Za-z.]*)\)', carried)
    rows.append({
        'component': item['Component'],
        'version': version[1] if version else item['Version'],
        'licence': item['Licence'],
        'use': item['In edi'],
    })
assert any(row['component'] == 'Qt' and row['licence'] == 'LGPL-3.0-only' for row in rows), (
    'The independent notice fixture contains the Qt licence witness'
)
assert any(row['component'] == 'Eigen' and row['licence'] == 'MPL-2.0' for row in rows), (
    'The independent notice fixture contains the Eigen licence witness'
)
licence_texts = {}
for name in ('SLEEF', 'Eigen'):
    section = re.search(rf'(?ms)^## {name}\n(.*?)(?=^## |\Z)', text)
    assert section, 'The independent notice has the selected component section'
    lines = section[1].splitlines()
    start = next(index for index, line in enumerate(lines) if line.startswith('    '))
    licence_texts[name] = textwrap.dedent('\n'.join(lines[start:])).strip()
    assert licence_texts[name], 'The selected component has its complete independent licence input'
Path(__file__).with_name('notices.json').write_text(
    json.dumps(
        {
            'source': 'THIRD-PARTY-NOTICES',
            'sha256': hashlib.sha256(source.read_bytes()).hexdigest(),
            'catalogue': 'DEPENDENCIES.md',
            'catalogue_sha256': hashlib.sha256(catalogue.read_bytes()).hexdigest(),
            'rows': rows,
            'licenceTexts': licence_texts,
        },
        indent=2,
    )
    + '\n'
)
