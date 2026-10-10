"""Freeze the shipped notice input independently of ApplicationInfo and QML."""

import hashlib
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
source = ROOT / 'THIRD-PARTY-NOTICES'
text = source.read_text()
component_list = text.split('Components\n----------\n', 1)[1].split('Acknowledgements\n', 1)[0]
rows = []
for line in component_list.splitlines():
    match = re.fullmatch(r'- (.+?) \| licence: (.+?) \| (.+)', line)
    if not match:
        continue
    version = re.fullmatch(r'(.+) (\d+(?:\.\d+)+(?:[\w-]*))', match[1])
    rows.append({
        'component': version[1] if version else match[1],
        'version': version[2] if version else '',
        'licence': match[2],
        'use': match[3],
    })
assert any(row['component'] == 'Qt' and row['licence'] == 'LGPL-3.0-only' for row in rows), (
    'The independent notice fixture contains the Qt licence witness'
)
assert any(row['component'] == 'Eigen' and row['licence'] == 'MPL-2.0' for row in rows), (
    'The independent notice fixture contains the Eigen licence witness'
)
Path(__file__).with_name('notices.json').write_text(
    json.dumps(
        {
            'source': 'THIRD-PARTY-NOTICES',
            'sha256': hashlib.sha256(source.read_bytes()).hexdigest(),
            'rows': rows,
        },
        indent=2,
    )
    + '\n'
)
