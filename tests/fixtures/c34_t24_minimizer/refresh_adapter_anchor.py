"""Refresh the current-source anchor after 's adapter extension.

The historical classification and its frozen input stay byte-identical.
Run from any directory with the edi pinned Python interpreter.
"""

from __future__ import annotations

import hashlib
import json
from operator import itemgetter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]


def main() -> None:
    path = ROOT / 'tests/unit/cpp/e09_t55_adapter_classification.json'
    document = json.loads(path.read_text())
    anchor = document['post_move_source']
    digest = hashlib.sha256()
    for entry in sorted(anchor['files'], key=itemgetter('path')):
        source = (ROOT / entry['path']).read_bytes()
        entry['sha256'] = hashlib.sha256(source).hexdigest()
        entry['lines'] = len(source.decode().splitlines())
        digest.update(entry['path'].encode())
        digest.update(b'\0')
        digest.update(str(len(source)).encode())
        digest.update(b'\0')
        digest.update(source)
    anchor['tree_sha256'] = digest.hexdigest()
    path.write_text(json.dumps(document, indent=2) + '\n')


if __name__ == '__main__':
    main()
