"""Recover a saved-file witness only when its complete bytes match the existing main pin."""

import argparse
import base64
import hashlib
import json
import zlib
from pathlib import Path

HOME = Path(__file__).resolve().parent


def freeze(paths, output):
    main = json.loads((HOME / 'saved-main.json').read_text())
    cases = list(main['fit_projects'])
    if len(cases) != 1:
        raise ValueError('Recovery requires the single existing fitted-byte case')
    case = cases[0]
    experiments = {}
    for rule, path in paths.items():
        raw = path.read_bytes()
        if (
            hashlib.sha256(raw).hexdigest()
            != main['fit_projects'][case][rule]['experiments/experiment.edi']
        ):
            raise ValueError(
                'Recovery refuses every byte outside the original immutable whole-file hash'
            )
        experiments[rule] = base64.b64encode(zlib.compress(raw)).decode('ascii')
    output.write_text(
        json.dumps(
            {
                'kind': 'immutable saved-main file recovery',
                'source_commit': main['source_commit'],
                'case': case,
                'experiments': experiments,
            },
            indent=2,
        )
        + '\n',
        encoding='utf-8',
        newline='\n',
    )


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--iucr-19', type=Path, required=True)
    parser.add_argument('--iucr-99', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    freeze({'iucr_19': args.iucr_19, 'iucr_99': args.iucr_99}, args.output)
