"""Freeze one independently executed saved-auto flow, labelled as a state regression input."""

import argparse
import hashlib
import json
import re
import subprocess
from pathlib import Path

from tests.fixtures.background_estimate.lifecycle import persisted_points

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]


def saved_digests(project):
    text = (project / 'experiments/hrpt.edi').read_text()
    result = {}
    for name in ['inputs_digest', 'points_digest']:
        tokens = re.findall(r'(?m)^_background_estimate\.' + name + r' ([0-9a-f]{16})$', text)
        if len(tokens) != 1 or int(tokens[0], 16) == 0:
            raise ValueError('A saved automatic input requires exactly one nonzero ' + name)
        result[name] = tokens[0]
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--engine-writer', type=Path, required=True)
    parser.add_argument('--engine-commit', required=True)
    args = parser.parse_args()
    if not re.fullmatch(r'[0-9a-f]{40}', args.engine_commit):
        parser.error('The author run requires the exact linked engine commit')
    source = HERE / 'projects/lifecycle-auto'
    destination = HERE / 'projects/lifecycle-saved-auto'
    receipt = HERE / 'saved-lifecycle.json'
    if destination.exists() or receipt.exists():
        parser.error('A frozen saved-auto regression input cannot be overwritten')
    old = json.loads((HERE / 'lifecycle-cases.json').read_text())['cases']['lifecycle-auto']
    source_hashes = {
        p.relative_to(source).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
        for p in sorted(source.rglob('*'))
        if p.is_file()
    }
    if source_hashes != old['sha256']:
        parser.error('The original digestless lifecycle input must retain every frozen byte')
    subprocess.run(
        [str(args.engine_writer.resolve()), str(source), str(destination), 'calculate'],
        capture_output=True,
        text=True,
        check=True,
        timeout=10,
    )
    record = {
        'claim': (
            'REGRESSION INPUT: independently executed calculate/save state; no physics oracle'
        ),
        'repository': 'https://github.com/enhantica/edi',
        'engine_commit': args.engine_commit,
        'command': 'python -m tests.fixtures.background_estimate.generate_saved_lifecycle '
        '--engine-writer ../background-reference/build/save_auto '
        '--engine-commit ' + args.engine_commit,
        'source': source.relative_to(ROOT).as_posix(),
        'source_sha256': source_hashes,
        'project': destination.relative_to(ROOT).as_posix(),
        'saved_digests': saved_digests(destination),
        'points': persisted_points(destination),
        'sha256': {
            p.relative_to(destination).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in sorted(destination.rglob('*'))
            if p.is_file()
        },
    }
    receipt.write_text(json.dumps(record, indent=2) + '\n')
    print('Recorded one full calculate/save flow with engine', args.engine_commit)


if __name__ == '__main__':
    main()
