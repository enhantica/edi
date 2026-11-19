# SPDX-License-Identifier: BSD-3-Clause
"""Count actual Crysta forward calls, including calls made inside formatting code.

Run against the separately built native test; never builds or reads hidden test tiers.
"""

import argparse
import os
import re
import subprocess
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--gdb', default='gdb')
    parser.add_argument('--runner', default='build/app/app/edi_linked_structure_calculation_tests')
    args = parser.parse_args()
    result = subprocess.run(
        [
            args.gdb,
            '--nx',
            '-batch',
            '--return-child-result',
            '-x',
            str(Path(__file__).with_name('count.gdb')),
            '--args',
            args.runner,
            'oneAppendCalculatesOnce',
        ],
        env=os.environ | {'QT_QPA_PLATFORM': 'offscreen', 'QT_QUICK_BACKEND': 'software'},
        capture_output=True,
        text=True,
        check=False,
        timeout=60,
    )
    print(result.stdout, end='')
    print(result.stderr, end='')
    counts = re.findall(r'ENGINE_COUNTS calls=(\d+) parses=(\d+) renders=(\d+)', result.stdout)
    if result.returncode or len(counts) != 1 or int(counts[0][0]) != 1:
        raise SystemExit('A linked structure edit must make exactly one engine calculation')


if __name__ == '__main__':
    main()
