# SPDX-License-Identifier: BSD-3-Clause
"""The tutorial transaction observer and the app build files its receipt names.

The observer's receipt (tests/fixtures/project_transactions/build.py) names every object,
library and SDK header it was linked from, by path and sha256, and the system tests check
each one. A system job has no app build of its own, so the app job packs exactly those files
next to the observer and each system job unpacks them:

    python tools/ci/tutorial_transaction_inputs.py pack    # app job, after building it
    python tools/ci/tutorial_transaction_inputs.py ensure  # before the system tier

Outside CI, `ensure` builds the observer when it is missing or older than the app build, so a
local system run prepares it on its own.
"""

import hashlib
import json
import os
import subprocess
import sys
import tarfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUTPUT = ROOT / 'build/tutorial-transactions'
RECEIPT = OUTPUT / 'receipt.json'
ARCHIVE = OUTPUT / 'inputs.tar'
PREFIX = 'tutorial-transactions:'


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def inputs(receipt: dict) -> dict[str, str]:
    """Every file outside the observer's folder the receipt binds, with its sha256."""
    named = dict(receipt['linked'])
    named.update(receipt['sdk'])
    for key in ('original_app_library', 'original_core_library'):
        named[receipt[key]['path']] = receipt[key]['sha256']
    files = {}
    for name, sha in named.items():
        path = Path(name)
        if OUTPUT in path.parents:
            continue
        if ROOT not in path.parents:
            raise SystemExit(f'{PREFIX} {path} is outside the checkout and cannot be carried')
        files[path.relative_to(ROOT).as_posix()] = sha
    return files


def differing(files: dict[str, str]) -> list[str]:
    """The files that are missing or hold other bytes than the receipt recorded."""
    return [
        name
        for name, sha in files.items()
        if not (ROOT / name).is_file() or digest(ROOT / name) != sha
    ]


def pack() -> None:
    files = inputs(json.loads(RECEIPT.read_text()))
    stale = differing(files)
    if stale:
        raise SystemExit(f'{PREFIX} {len(stale)} file(s) changed since the observer was built')
    with tarfile.open(ARCHIVE, 'w') as archive:
        for name in sorted(files):
            archive.add(ROOT / name, arcname=name, recursive=False)
    print(f'{PREFIX} packed {len(files)} file(s) into {ARCHIVE.relative_to(ROOT)}')


def build() -> None:
    if not (ROOT / 'build/app/CMakeCache.txt').is_file():
        subprocess.run(['bash', 'tools/ci/app-build.sh'], cwd=ROOT, check=True)
    output = str(OUTPUT.relative_to(ROOT))
    module = 'tests.fixtures.project_transactions.build'
    command = [sys.executable, '-m', module, '--root', '.', '--native', 'build/app']
    subprocess.run([*command, '--output', output], cwd=ROOT, check=True)


def ensure() -> None:
    in_ci = os.environ.get('CI') == 'true'
    if not RECEIPT.is_file():
        if in_ci:
            # No app job ran for this run: there is no observer, and the tests that need it say so.
            print(f'{PREFIX} no observer from the app job')
            return
        build()
        return
    files = inputs(json.loads(RECEIPT.read_text()))
    stale = differing(files)
    if not stale:
        print(f'{PREFIX} the observer and its {len(files)} input file(s) are in place')
        return
    # Unpack only into absent files: a different file here is a newer app build, kept as it is.
    absent = [name for name in stale if not (ROOT / name).exists()]
    if ARCHIVE.is_file() and len(absent) == len(stale):
        with tarfile.open(ARCHIVE) as archive:
            members = [archive.getmember(name) for name in absent]
            archive.extractall(ROOT, members=members, filter='data')
        stale = differing(files)
        if not stale:
            print(f'{PREFIX} unpacked {len(absent)} input file(s) from {ARCHIVE.name}')
            return
    if in_ci:
        raise SystemExit(f'{PREFIX} {len(stale)} file(s) missing or changed, e.g. {stale[0]}')
    build()


if __name__ == '__main__':
    commands = {'pack': pack, 'ensure': ensure}
    if len(sys.argv) != 2 or sys.argv[1] not in commands:
        raise SystemExit('usage: tutorial_transaction_inputs.py pack|ensure')
    commands[sys.argv[1]]()
