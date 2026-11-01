"""Capture layout metadata while retaining every historical output byte pin."""

import argparse
import hashlib
import json
import zipfile
from pathlib import Path

from tests.fixtures.project_categories.historical_bytes import layout

ROOT = Path(__file__).resolve().parents[3]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source', type=Path)
    parser.add_argument('--revision', required=True)
    args = parser.parse_args()
    inherited = json.loads(args.source.read_text())['layouts']
    documents = [p.read_bytes() for p in (ROOT / 'tests/fixtures').rglob('*.edi')]
    for name in ('c13_t12_ids/baseline.zip', 'table_display/regression-inputs.zip'):
        with zipfile.ZipFile(ROOT / 'tests/fixtures' / name) as archive:
            documents.extend(archive.read(p) for p in archive.namelist() if p.endswith('.edi'))
    entries = [*inherited, *(layout(data) for data in documents)]
    record = {
        'source_revision': args.revision,
        'source_sha256': hashlib.sha256(args.source.read_bytes()).hexdigest(),
        'source': 'frozen category layout reference',
        'layouts': list({json.dumps(row, sort_keys=True): row for row in entries}.values()),
    }
    Path(__file__).with_name('historical-layouts.json').write_text(
        json.dumps(record, indent=2) + '\n'
    )


if __name__ == '__main__':
    main()
