"""Record external Git blob identities; never generate expected numerical results from edi.

Usage: python generate.py --crysta /path/to/crysta --diffraction-lib /path/to/diffraction-lib
The crysta tree is origin/main, and the upstream FullProf artifacts are at HEAD.
"""

from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path

HERE = Path(__file__).resolve().parent


def git(root, *args):
    return subprocess.check_output(['git', '-C', str(root), *args], text=True).strip()


def objects(root, ref, *paths):
    rows = git(root, 'ls-tree', '-r', ref, '--', *paths).splitlines()
    return {row.split('\t')[1]: row.split()[2] for row in rows}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--crysta', type=Path, required=True)
    parser.add_argument('--diffraction-lib', type=Path, required=True)
    args = parser.parse_args()
    ids = git(
        args.crysta, 'ls-tree', '-d', '--name-only', 'origin/main:tests/fitting'
    ).splitlines()
    seed = {
        'source': 'crysta',
        'ref': 'origin/main',
        'commit': git(args.crysta, 'rev-parse', 'origin/main'),
        'method': 'git ls-tree -r origin/main:tests/fitting/<id> -- project expected.json',
        'claim': (
            'Byte identity only. Expected numerical values retain their source kinds; '
            'crysta-produced fit outputs are regression pins, not correctness oracles.'
        ),
        'projects': {
            name: objects(
                args.crysta, f'origin/main:tests/fitting/{name}', 'project', 'expected.json'
            )
            for name in ids
        },
    }
    reference = 'docs/docs/verification/fullprof/pd-neut-tof_diamond_dream'
    fullprof = {
        'source': f'diffraction-lib/{reference}',
        'commit': git(args.diffraction_lib, 'rev-parse', 'HEAD'),
        'objects': objects(args.diffraction_lib, f'HEAD:{reference}'),
    }
    for name, data in [('source-objects.json', seed), ('fullprof-objects.json', fullprof)]:
        (HERE / name).write_text(json.dumps(data, indent=2) + '\n')


if __name__ == '__main__':
    main()
