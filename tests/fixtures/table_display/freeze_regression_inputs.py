"""Freeze reviewed input bytes used by the historical serialization witnesses."""

import argparse
import hashlib
import io
import json
import subprocess
import tarfile
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
CASES = [
    case.removeprefix('repo:')
    for case in json.loads(
        (ROOT / 'tests/fixtures/c34_t28_baseline/saved-bytes.json').read_text()
    )['cases']
    if case.startswith('repo:')
]


def record(revision):
    resolved = subprocess.check_output(
        ['git', '-C', str(ROOT), 'rev-parse', revision], text=True
    ).strip()
    files = {}
    with zipfile.ZipFile(HERE / 'regression-inputs.zip', 'w') as output:
        for case in CASES:
            relative = case
            payload = subprocess.check_output([
                'git',
                '-C',
                str(ROOT),
                'archive',
                resolved + ':' + relative,
            ])
            with tarfile.open(fileobj=io.BytesIO(payload)) as archive:
                for member in archive.getmembers():
                    if not member.isfile():
                        continue
                    data = archive.extractfile(member).read()
                    name = relative + '/' + member.name
                    files[name] = hashlib.sha256(data).hexdigest()
                    info = zipfile.ZipInfo(name, date_time=(2026, 10, 11, 0, 0, 0))
                    info.compress_type = zipfile.ZIP_DEFLATED
                    output.writestr(info, data)
    (HERE / 'regression-inputs.json').write_text(
        json.dumps(
            {
                'claim': 'REVIEWED INPUT BYTES: pre-catalogue source; no saved-output oracle',
                'source_revision': resolved,
                'files': files,
            },
            indent=2,
            sort_keys=True,
        )
        + '\n'
    )


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('revision')
    record(parser.parse_args().revision)
