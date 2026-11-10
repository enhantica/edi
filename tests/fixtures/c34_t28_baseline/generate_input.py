"""Derive the small freshness input from committed  input bytes.

The explicit input changes are the supported schema-3 marker and two background
points, plus an explicit cutoff. This creates no calculated expected output.
Run with --crysta <checkout>.
"""

import argparse
import shutil
import subprocess
from pathlib import Path

BASE = '0c163576ea32c5773a73d52c7e0f4fec96d1f61e'
SOURCE = 'tests/fixtures/c34_t26_diffraction_lib/boundaries/inputs/cw-inside/'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--crysta', type=Path, required=True)
    args = parser.parse_args()
    git = shutil.which('git')
    if not git:
        parser.error('Git is required to read the committed reference input')
    subprocess.run(
        [git, '-C', str(args.crysta), 'merge-base', '--is-ancestor', BASE, 'origin/main'],
        check=True,
    )
    paths = subprocess.check_output(
        [git, '-C', str(args.crysta), 'ls-tree', '-r', '--name-only', BASE, '--', SOURCE],
        text=True,
    ).splitlines()
    destination = Path(__file__).with_name('freshness-input')
    for path in paths:
        text = subprocess.check_output(
            [git, '-C', str(args.crysta), 'show', BASE + ':' + path], text=True
        ).replace('_edi.schema_version 1', '_edi.schema_version 3')
        relative = Path(path.removeprefix(SOURCE))
        if relative == Path('experiments/experiment.edi'):
            text += (
                '\n_peak.cutoff_fwhm 8.2\n_background.type line-segment\nloop_\n'
                '_background.id\n_background.position\n_background.intensity\n1 20 0\n2 75 0\n'
            )
        target = destination / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(text)


if __name__ == '__main__':
    main()
