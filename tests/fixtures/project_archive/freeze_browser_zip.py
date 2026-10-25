"""Retain a real browser download as a layout regression fixture."""

import argparse
import hashlib
import json
import re
from pathlib import Path
from zipfile import ZipFile


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('download', type=Path)
    parser.add_argument('--source', required=True)
    args = parser.parse_args()
    raw = args.download.read_bytes()
    with ZipFile(args.download) as archive:
        members = sorted(archive.namelist())
        record = archive.read('project.edi').decode()
    name = re.search(r'^_metadata.name\s+(?:"([^"]+)"|(\S+))', record, re.MULTILINE)
    if not name:
        raise SystemExit('The downloaded archive has no project name')
    destination = Path(__file__).parent
    (destination / 'browser-saved-project.zip').write_bytes(raw)
    manifest = {
        'purpose': 'Web-produced archive layout regression; no scientific accuracy claim',
        'producer': args.source,
        'sha256': hashlib.sha256(raw).hexdigest(),
        'members': members,
        'name': name.group(1) or name.group(2),
    }
    (destination / 'browser-saved-project.json').write_text(json.dumps(manifest, indent=2) + '\n')


if __name__ == '__main__':
    main()
