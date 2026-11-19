"""Keep only the structural census of the two supplied report-size examples."""

import hashlib
import io
import json
import sys
import zipfile
from pathlib import Path


def main():
    scenarios = []
    with (
        zipfile.ZipFile(sys.argv[1]) as outer,
        zipfile.ZipFile(io.BytesIO(outer.read('Archive.zip'))) as archive,
    ):
        for name in ('2026.11.22.txt', 'main.txt'):
            raw = archive.read(name)
            document = json.loads(raw)
            reads = sum(
                item.get('row', {}).get('payload', {}).get('tool') == 'inspect_data'
                for item in document['history_evidence']
            )
            scenarios.append({
                'id': name.removesuffix('.txt'),
                'source_sha256': hashlib.sha256(raw).hexdigest(),
                'source_bytes': len(raw),
                'inspection_calls': reads,
            })
    Path(__file__).with_name('reference.json').write_text(
        json.dumps(
            {'kind': 'Structural workload census; no private report text', 'scenarios': scenarios},
            indent=2,
        )
        + '\n'
    )


if __name__ == '__main__':
    main()
