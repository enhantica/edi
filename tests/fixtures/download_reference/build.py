# SPDX-License-Identifier: BSD-3-Clause
"""Create a tiny independent collection with measured data and a saved-project archive."""

import hashlib
import json
import zipfile
from pathlib import Path

MEASUREMENT = b'1.25 17.125 0.5\n2.75 8.625 0.25\n'
PROJECT = b'data_project\n_project.name reference\n'


def build(root: Path) -> dict:
    root.mkdir(parents=True, exist_ok=True)
    (root / 'data').mkdir()
    (root / 'data/alpha.xye').write_bytes(MEASUREMENT)
    (root / 'data/zeta.xye').write_bytes(MEASUREMENT[::-1])
    with zipfile.ZipFile(root / 'data/project.zip', 'w') as archive:
        archive.writestr('reference/project.edi', PROJECT)
        archive.writestr('reference/structures/readme.txt', 'independent archive member\n')
    entries = []
    for identity, kind, relative, fmt in [
        ('zeta-data', 'data', 'data/zeta.xye', 'xye'),
        ('alpha-data', 'data', 'data/alpha.xye', 'xye'),
        ('proj-reference', 'project', 'data/project.zip', 'zip'),
    ]:
        content = (root / relative).read_bytes()
        entries.append({
            'id': identity,
            'kind': kind,
            'name': identity,
            'description': f'Independent {identity} record',
            'files': [
                {
                    'path': relative,
                    'format': fmt,
                    'bytes': len(content),
                    'sha256': hashlib.sha256(content).hexdigest(),
                }
            ],
        })
    index = {'schema': 'edi-data-index/1', 'entries': entries}
    (root / 'index.json').write_text(json.dumps(index))
    return index
