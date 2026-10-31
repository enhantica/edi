"""Advance labelled byte pins only after reproducing their recorded baseline."""

import argparse
import gzip
import hashlib
import json
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--before', type=Path, required=True)
    parser.add_argument('--after', type=Path, required=True)
    args = parser.parse_args()
    root = Path(__file__).resolve().parent
    path = root / 'saved-main.json'
    original = path.read_bytes()
    pins = json.loads(original)
    old_rows = {
        (row['case'], row['rule']): row
        for row in json.loads(gzip.decompress(args.before.read_bytes()))
    }
    changes = []
    retained = []
    for row in json.loads(gzip.decompress(args.after.read_bytes())):
        key = row['case'], row['rule']
        before = old_rows[key]
        expected = pins['projects'][row['case']][row['rule']]
        if 'refused' in row or 'refused' in before:
            raise ValueError('A regression transition must save successfully: ' + repr(key))
        if before['hashes'] != expected:
            raise ValueError('The recorded main byte pins were not reproduced: ' + repr(key))
        if expected.keys() != row['hashes'].keys():
            retained.append({
                'case': key[0],
                'rule': key[1],
                'added': sorted(row['hashes'].keys() - expected.keys()),
                'removed': sorted(expected.keys() - row['hashes'].keys()),
            })
            continue
        for name, old_hash in expected.items():
            new_hash = row['hashes'][name]
            if new_hash != old_hash:
                changes.append({
                    'case': key[0],
                    'rule': key[1],
                    'path': name,
                    'before': old_hash,
                    'after': new_hash,
                })
                expected[name] = new_hash
    (root / 'saved-before-rounded.json').write_bytes(original)
    pins['save_transition'] = 'rounded-save-transitions.json'
    path.write_text(json.dumps(pins, indent=2, sort_keys=True) + '\n')
    (root / 'rounded-save-transitions.json').write_text(
        json.dumps(
            {
                'claim': (
                    'Regression pins for rounded saving and experiment metadata, '
                    'not physical references'
                ),
                'before_capture_sha256': hashlib.sha256(args.before.read_bytes()).hexdigest(),
                'after_capture_sha256': hashlib.sha256(args.after.read_bytes()).hexdigest(),
                'changes': changes,
                'retained_path_mismatches': retained,
            },
            indent=2,
        )
        + '\n'
    )


if __name__ == '__main__':
    main()
