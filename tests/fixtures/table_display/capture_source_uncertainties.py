"""Capture the committed input spelling sweep, never fitted or saved outputs."""

import argparse
import hashlib
import json
import re
import subprocess
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('revision')
    revision = parser.parse_args().revision
    paths = subprocess.check_output(
        ['git', 'diff-tree', '--no-commit-id', '--name-only', '-r', revision],
        cwd=ROOT,
        text=True,
    ).splitlines()
    rows = {}
    archive = zipfile.ZipFile(
        Path(__file__).with_name('source-uncertainties.zip'),
        'w',
        compression=zipfile.ZIP_DEFLATED,
    )
    for name in paths:
        if not name.startswith('docs/user/cli/') or not name.endswith('.edi'):
            continue
        before, after = (
            subprocess.check_output(['git', 'show', revision + ':' + name], cwd=ROOT)
            for revision in (revision + '^', revision)
        )
        parts = re.split(rb'(?<=[\d.])\((\d+)\)', before)
        pattern = b''.join(
            re.escape(part) if i % 2 == 0 else rb'\((?:' + part + rb')?\)'
            for i, part in enumerate(parts)
        )
        assert re.fullmatch(pattern, after), (
            'The admitted sweep changes only authored initial uncertainty digits'
        )
        digest = hashlib.sha256(before).hexdigest()
        if digest not in archive.namelist():
            info = zipfile.ZipInfo(digest, date_time=(2026, 11, 17, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            archive.writestr(info, before)
        rows[name] = {
            'before_sha256': digest,
            'after_sha256': hashlib.sha256(after).hexdigest(),
        }
    archive.close()
    Path(__file__).with_name('source-uncertainties.json').write_text(
        json.dumps(rows, indent=2) + '\n'
    )


if __name__ == '__main__':
    main()
