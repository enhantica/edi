"""Advance labelled byte pins only after reproducing their recorded baseline."""

import argparse
import gzip
import hashlib
import importlib
import json
import tempfile
from pathlib import Path

from tests.fixtures.fittability.saved_reference import snapshot


def advance_table_helper(root, previous):
    case = 'tests/fixtures/table_display'
    asset = 'metadata_bytes.py'
    repo = root.parents[2]
    old_hash = hashlib.sha256(previous.read_bytes()).hexdigest()
    new_bytes = (repo / case / asset).read_bytes()
    new_hash = hashlib.sha256(new_bytes).hexdigest()
    pins = json.loads((root / 'saved-main.json').read_text())
    original = json.loads((root / 'saved-before-rounded.json').read_text())
    transition_path = root / 'rounded-save-transitions.json'
    transition = json.loads(transition_path.read_text())
    for rule in ['iucr_19', 'iucr_99']:
        expected = pins['projects'][case][rule]
        baseline = original['projects'][case][rule][asset]
        existing = [
            row
            for row in transition['changes']
            if (row['case'], row['rule'], row['path']) == (case, rule, asset)
        ]
        if expected[asset] != old_hash:
            raise ValueError('The copied helper must reproduce its current regression hash')
        if existing:
            if len(existing) != 1 or (existing[0]['before'], existing[0]['after']) != (
                baseline,
                old_hash,
            ):
                raise ValueError('The helper transition must bind its original and current pins')
        elif baseline != old_hash:
            raise ValueError('The first helper transition must reproduce its original pin')
        with tempfile.TemporaryDirectory() as folder:
            scratch = Path(folder)
            actual = snapshot(
                importlib.import_module('edi'),
                repo / case,
                scratch,
                rule,
                order_reference=expected,
            )
            if (scratch / 'saved' / asset).read_bytes() != new_bytes:
                raise ValueError('The saved helper must preserve the source asset bytes exactly')
        if actual != {**expected, asset: new_hash}:
            raise ValueError('Any other saved path or byte change refuses the helper transition')
        expected[asset] = new_hash
        if existing:
            existing[0]['after'] = new_hash
        else:
            transition['changes'].append({
                'case': case,
                'rule': rule,
                'path': asset,
                'before': old_hash,
                'after': new_hash,
            })
    transition['claim'] = (
        'Regression pins for rounded saving, experiment metadata and copied fixture helpers, '
        'not physical references'
    )
    (root / 'saved-main.json').write_text(json.dumps(pins, indent=2, sort_keys=True) + '\n')
    transition_path.write_text(json.dumps(transition, indent=2) + '\n')


def advance_table_assets(root, previous):
    """Advance only copied non-scientific assets after proving every other hash."""
    case = 'tests/fixtures/table_display'
    names = ('README.md', 'metadata_bytes.py', 'notices.json')
    repo = root.parents[2]
    path = root / 'saved-main.json'
    pins = json.loads(path.read_text())
    transition_path = root / 'rounded-save-transitions.json'
    transitions = json.loads(transition_path.read_text())
    old = {name: hashlib.sha256((previous / name).read_bytes()).hexdigest() for name in names}
    new = {name: (repo / case / name).read_bytes() for name in names}
    hashes = {name: hashlib.sha256(data).hexdigest() for name, data in new.items()}
    for rule in ('iucr_19', 'iucr_99'):
        expected = pins['projects'][case][rule]
        if any(expected[name] != old[name] for name in names):
            raise ValueError('Every old copied asset must reproduce its immutable current pin')
        with tempfile.TemporaryDirectory() as folder:
            scratch = Path(folder)
            actual = snapshot(
                importlib.import_module('edi'),
                repo / case,
                scratch,
                rule,
                order_reference=expected,
            )
            if any((scratch / 'saved' / name).read_bytes() != new[name] for name in names):
                raise ValueError('Saved copied assets must retain every actual source byte')
        if actual != {**expected, **hashes}:
            raise ValueError('Any other saved path or byte refuses the copied-asset transition')
        for name in names:
            expected[name] = hashes[name]
            transitions['changes'].append({
                'case': case,
                'rule': rule,
                'path': name,
                'before': old[name],
                'after': hashes[name],
                'reason': 'Copied asset changed in the merged source; scientific bytes unchanged',
            })
    path.write_text(json.dumps(pins, indent=2, sort_keys=True) + '\n')
    transition_path.write_text(json.dumps(transitions, indent=2) + '\n')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--before', type=Path)
    parser.add_argument('--after', type=Path)
    parser.add_argument('--before-helper', type=Path)
    parser.add_argument('--before-assets', type=Path)
    args = parser.parse_args()
    root = Path(__file__).resolve().parent
    if args.before_assets is not None:
        if any(value is not None for value in (args.before, args.after, args.before_helper)):
            parser.error('--before-assets cannot be combined with other transitions')
        advance_table_assets(root, args.before_assets)
        return
    if args.before_helper is not None:
        if args.before is not None or args.after is not None:
            parser.error('--before-helper cannot be combined with capture inputs')
        advance_table_helper(root, args.before_helper)
        return
    if args.before is None or args.after is None:
        parser.error('--before and --after are required for capture transitions')
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
