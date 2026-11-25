# SPDX-License-Identifier: BSD-3-Clause
"""Export crysta's source at a commit out of a checkout, with native paths on every platform.

python3 tools/ci/crysta_source_export.py CHECKOUT SHA DESTINATION
"""

from __future__ import annotations

import os
import posixpath
import shutil
import subprocess
import sys
import tarfile
import tempfile
from pathlib import Path


def extract(archive: Path, destination: Path) -> None:
    """Extract the tree with the same data filter as the SDK reader."""
    with tarfile.open(archive) as source:
        members = source.getmembers()
        # Windows cannot follow a link whose target is spelled with '/', and a tree walk over
        # one fails, so there each link becomes a copy of the file it names.
        links = [member for member in members if member.issym()] if os.name == 'nt' else []
        source.extractall(destination, [m for m in members if m not in links], filter='data')
        for link in links:
            folder = posixpath.dirname(link.name)
            target = posixpath.normpath(posixpath.join(folder, link.linkname))
            if target.startswith('../') or posixpath.isabs(target):
                raise ValueError(f'{link.name} links outside the source: {link.linkname}')
            copy = destination / link.name
            copy.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(destination / target, copy)


def main() -> int:
    """Export, or exit 1 with the reason and nothing of the source."""
    checkout, sha, destination = sys.argv[1], sys.argv[2], Path(sys.argv[3])
    try:
        with tempfile.TemporaryDirectory() as scratch:
            archive = Path(scratch) / 'source.tar'
            subprocess.run(
                ['git', '-C', checkout, 'archive', '--format=tar', '-o', str(archive), sha],
                check=True,
                capture_output=True,
            )
            destination.mkdir(parents=True, exist_ok=True)
            extract(archive, destination)
    except (OSError, ValueError, tarfile.TarError, subprocess.CalledProcessError) as error:
        print(f'source-export: REFUSED: {type(error).__name__}', file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
