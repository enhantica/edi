# SPDX-License-Identifier: BSD-3-Clause
"""An independent correct publisher validates the operation-policy witness itself."""

import json
import os
import shutil
import sys
import tempfile
import zipfile
from pathlib import Path


def write_archive(path, stage):
    with zipfile.ZipFile(path) as archive:
        for member in archive.infolist():
            target = stage / member.filename
            target.parent.mkdir(parents=True, exist_ok=True)
            with target.open('wb') as output:
                output.write(archive.read(member))
                output.flush()
                os.fsync(output.fileno())


def main():
    source, destination = map(Path, sys.argv[1:])
    record = json.loads((source / 'index.json').read_text(encoding='utf-8'))['entries'][0]
    file = record['files'][0]
    published = destination / (record['id'] + '-' + file['sha256'][:12])
    stage = Path(tempfile.mkdtemp(dir=destination.parent))
    try:
        write_archive(source / file['path'], stage)
        stage.rename(published)
    except OSError as error:
        print(str(error), file=sys.stderr)
        shutil.rmtree(stage)
        return 1
    else:
        print(published / 'reference')
        return 0


if __name__ == '__main__':
    raise SystemExit(main())
