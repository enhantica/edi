# SPDX-License-Identifier: BSD-3-Clause
"""Put the generated interface record into a packed SDK, in place of the tracked one.

    python3 tools/ci/sdk_surface.py CHECKOUT SHA ARCHIVE...

crysta's tracked record also holds review history. edi's superset gate reads three things of it:
the schema, the direction of the constraint and the public names with their members. The SDK
carries those alone, generated from the record of the commit the SDK is of; the check of what is
stored accepts that form and no other. The archive's checksum file is written again.
"""

from __future__ import annotations

import gzip
import hashlib
import io
import json
import re
import subprocess
import sys
import tarfile
from pathlib import Path

TRACKED = 'data/python-surface.json'
MEMBER = 'share/crysta/python-surface.json'


def generated(tracked: bytes) -> bytes:
    """The record the SDK carries, from the tracked one."""
    record = json.loads(tracked)
    made = {
        'schema': record['schema'],
        'directionality': re.sub(r' \([^()]*\)', '', record['directionality']),
        'public': {
            name: {'members': list(entry['members'])}
            for name, entry in sorted(record['public'].items())
        },
    }
    named = [made['directionality'], *made['public']]
    named += [member for entry in made['public'].values() for member in entry['members']]
    if not isinstance(made['schema'], int) or not all(isinstance(name, str) for name in named):
        raise ValueError('the record has another form')
    if not all(re.fullmatch(r'\w+', name) for name in named[1:]):
        raise ValueError('a public name is not a name')
    return (json.dumps(made, ensure_ascii=False, indent=1) + '\n').encode()


def replace(archive: Path, record: bytes) -> None:
    """Write the archive again with this record, everything else as it is, and its checksum."""
    with tarfile.open(archive) as held:
        members = [
            (entry, held.extractfile(entry).read() if entry.isreg() else b'') for entry in held
        ]
    if [entry.name for entry, _ in members].count(MEMBER) != 1:
        raise ValueError('the archive has no one interface record')
    packed = io.BytesIO()
    with tarfile.open(fileobj=packed, mode='w') as made:
        for entry, data in members:
            content = record if entry.name == MEMBER else data
            if entry.isreg():
                entry.size = len(content)
            made.addfile(entry, io.BytesIO(content) if entry.isreg() else None)
    archive.write_bytes(gzip.compress(packed.getvalue(), mtime=0))
    digest = hashlib.sha256(archive.read_bytes()).hexdigest()
    checksum = archive.with_name(archive.name + '.sha256')
    checksum.write_text(f'{digest}  {archive.name}\n', encoding='ascii', newline='\n')


def main() -> int:
    """Replace the record in each archive; nothing of the tracked one is printed."""
    checkout, sha, *archives = sys.argv[1:]
    show = ['git', '-C', checkout, 'show', f'{sha}:{TRACKED}']
    try:
        record = generated(subprocess.run(show, capture_output=True, check=True).stdout)
        for archive in archives:
            replace(Path(archive), record)
    except (OSError, ValueError, KeyError, TypeError, AttributeError, tarfile.TarError) as error:
        print(f'sdk-surface: REFUSED: {type(error).__name__}', file=sys.stderr)
        return 1
    except subprocess.CalledProcessError:
        print('sdk-surface: REFUSED: the commit has no interface record', file=sys.stderr)
        return 1
    print(f'sdk-surface: {len(archives)} archives carry the generated interface record')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
