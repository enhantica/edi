"""Author one saved-state input under the exact placed-count contract; no physics oracle."""

import argparse
import hashlib
import json
import re
import shutil
import subprocess
from pathlib import Path

from tests.fixtures.background_estimate.generate_saved_lifecycle import saved_digests
from tests.fixtures.background_estimate.lifecycle import persisted_points

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]


def hashes(directory):
    return {
        path.relative_to(directory).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in sorted(directory.rglob('*'))
        if path.is_file()
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--cli', type=Path, required=True)
    parser.add_argument('--engine-commit', required=True)
    args = parser.parse_args()
    if not re.fullmatch(r'[0-9a-f]{40}', args.engine_commit):
        parser.error('Authoring requires the exact compiled engine commit')
    source = HERE / 'projects/lifecycle-auto'
    destination = HERE / 'projects/lifecycle-saved-placed'
    receipt = HERE / 'placed-lifecycle.json'
    old = json.loads((HERE / 'saved-lifecycle.json').read_text())
    if hashes(source) != old['source_sha256']:
        parser.error('The original digestless physical input must retain every frozen byte')
    if destination.exists() or receipt.exists():
        parser.error('A labelled state input cannot be overwritten')
    shutil.copytree(source, destination)
    subprocess.run(
        [str(args.cli.resolve()), str(destination), 'calc'],
        capture_output=True,
        text=True,
        check=True,
        timeout=5,
    )
    if len(persisted_points(destination)) != 9:
        parser.error('The exact-count state input must place all nine requested points')
    record = {
        'claim': (
            'REGRESSION INPUT: one calculate/save under exact placed-count semantics; '
            'no physics oracle'
        ),
        'repository': 'https://github.com/enhantica/edi',
        'writer': 'crysta C++ CLI',
        'engine_commit': args.engine_commit,
        'writer_binary_sha256': hashlib.sha256(args.cli.read_bytes()).hexdigest(),
        'command': 'python -m tests.fixtures.background_estimate.generate_placed_lifecycle '
        '--cli ../background-reference/bin/crysta --engine-commit ' + args.engine_commit,
        'source': source.relative_to(ROOT).as_posix(),
        'source_sha256': hashes(source),
        'project': destination.relative_to(ROOT).as_posix(),
        'saved_digests': saved_digests(destination),
        'points': persisted_points(destination),
        'sha256': hashes(destination),
        'supersedes_input_for_current_semantics': 'saved-lifecycle.json',
        'before_points': len(old['points']),
        'requested_placed_count': 9,
    }
    receipt.write_text(json.dumps(record, indent=2) + '\n')


if __name__ == '__main__':
    main()
