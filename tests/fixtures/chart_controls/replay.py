"""Replay the core witnesses on a selected committed tree with no product sibling."""

import argparse
import io
import os
import shutil
import subprocess
import sys
import tarfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('revision')
    parser.add_argument('destination', type=Path)
    args = parser.parse_args()
    destination = args.destination.resolve()
    destination.mkdir(parents=True, exist_ok=False)
    archive = subprocess.run(
        ['git', 'archive', args.revision, 'core', 'cmake', 'data'],
        cwd=ROOT,
        capture_output=True,
        check=True,
    )
    with tarfile.open(fileobj=io.BytesIO(archive.stdout)) as tree:
        tree.extractall(destination, filter='data')
    for folder in ('chart_controls', 'approved_palettes', 'palette_sources'):
        shutil.copytree(
            ROOT / f'tests/fixtures/{folder}', destination / f'tests/fixtures/{folder}'
        )
    tests = destination / 'tests/system/py'
    tests.mkdir(parents=True)
    shutil.copy2(ROOT / 'tests/system/py/test_chart_control_colours.py', tests)
    env = dict(os.environ, CI='true', GITHUB_ACTIONS='true')
    result = subprocess.run(
        [
            sys.executable,
            '-m',
            'pytest',
            'tests/system/py/test_chart_control_colours.py',
            '--confcutdir=tests/system/py',
            '-p',
            'no:cacheprovider',
            '--durations=0',
            '-ra',
        ],
        cwd=destination,
        env=env,
        check=False,
    )
    return result.returncode


if __name__ == '__main__':
    raise SystemExit(main())
