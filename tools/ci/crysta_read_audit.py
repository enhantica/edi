# SPDX-License-Identifier: BSD-3-Clause
"""Check that crysta's edi verification read no tracked edi file outside crysta's inputs.

    python3 tools/ci/crysta_read_audit.py --log FILE --root EDI_CHECKOUT

The verification's Python processes ran with tools/ci/read-audit on PYTHONPATH and
EDI_READ_AUDIT_LOG=FILE, EDI_READ_AUDIT_ROOT=EDI_CHECKOUT, so FILE lists every file under the
checkout they opened or imported. Each one Git tracks there has to be in the checkout's
tools/ci/crysta-inputs.txt, or crysta's jobs could be skipped for a change that alters what the
verification tests. A record without a tracked edi file refuses: the hook did not run.
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

from crysta_inputs import RefusedError, covers, inputs


def tracked(root: Path) -> set[str]:
    run = subprocess.run(
        ['git', '-C', str(root), 'ls-files', '-z'], capture_output=True, check=False
    )
    if run.returncode:
        raise RefusedError(f'git ls-files exited {run.returncode}')
    return set(filter(None, run.stdout.decode('utf-8', 'surrogateescape').split('\0')))


def outside(log: Path, root: Path) -> tuple[list[str], int]:
    """The tracked files read that are not inputs, and how many tracked files were read."""
    recorded = set(log.read_text(encoding='utf-8', errors='surrogateescape').splitlines())
    read = sorted(recorded & tracked(root))
    if not read:
        raise RefusedError(f'{log} records no tracked edi file: the read audit did not run')
    entries = inputs(root / 'tools/ci/crysta-inputs.txt')
    return [path for path in read if not covers(entries, path)], len(read)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--log', required=True, type=Path)
    parser.add_argument('--root', required=True, type=Path)
    args = parser.parse_args()
    try:
        found, count = outside(args.log, args.root)
    except (RefusedError, OSError) as refusal:
        print(f'crysta-read-audit: REFUSED: {refusal}', file=sys.stderr)
        return 1
    for path in found:
        print(
            f'crysta-read-audit: {path} was read and is not in crysta-inputs.txt', file=sys.stderr
        )
    if found:
        return 1
    print(f'crysta-read-audit: {count} tracked edi files read, every one a crysta input')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
