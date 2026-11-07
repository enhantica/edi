# SPDX-License-Identifier: BSD-3-Clause
"""Author tutorial files and hashes independently of their downloader."""

import hashlib
import json
from pathlib import Path


def build(root: Path) -> dict:
    directory = root / 'tutorials'
    directory.mkdir()
    entries = []
    for identity, order in [('alpha-second', 20), ('zulu-first', 10)]:
        notebook = {
            'nbformat': 4,
            'nbformat_minor': 5,
            'metadata': {},
            'cells': [
                {
                    'id': '0',
                    'cell_type': 'code',
                    'metadata': {},
                    'execution_count': None,
                    'outputs': [],
                    'source': [f'print({identity!r})\n'],
                }
            ],
        }
        payloads = {
            'ipynb': json.dumps(notebook).encode(),
            'py': f'print({identity!r})\n'.encode(),
        }
        files = []
        for file_format, content in payloads.items():
            name = f'{identity}.{file_format}'
            (directory / name).write_bytes(content)
            files.append({
                'path': name,
                'format': file_format,
                'bytes': len(content),
                'sha256': hashlib.sha256(content).hexdigest(),
            })
        entries.append({
            'id': identity,
            'kind': 'tutorial',
            'name': identity,
            'description': 'Independently authored tutorial',
            'order': order,
            'files': files,
        })
    index = {'schema': 'edi-data-index/1', 'entries': entries}
    (directory / 'index.json').write_text(json.dumps(index), encoding='utf-8')
    return index
