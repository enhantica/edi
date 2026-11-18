"""Bounded readonly preparation for the one-point, two-bank PR witness."""

import argparse
import hashlib
import importlib
import json
import subprocess
import sys
from pathlib import Path

import numpy as np

from tests.fixtures.joint_series import ncaf

ROOT = Path(__file__).resolve().parents[3]
POINTS = 1
BANKS = 2
TIMEOUT = 10


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def tree(path):
    return {str(p.relative_to(path)): digest(p) for p in path.rglob('*') if p.is_file()}


def specification(root, engine):
    extension = Path(engine._edi.__file__ if engine.__name__ == 'edi' else engine.__file__)
    folder = root / 'tests/fixtures/joint_series'
    return {
        'extension': digest(extension),
        'source': {
            name: digest(folder / name) for name in ('prepare_seeded.py', 'ncaf.py', 'cases.py')
        },
        'observations': tree(ncaf.CASE / 'project'),
        'reference': digest(ncaf.CASE / 'expected.json'),
        'points': POINTS,
        'banks': BANKS,
    }


def directory(root, spec):
    key = hashlib.sha256(json.dumps(spec, sort_keys=True).encode()).hexdigest()
    return root / 'build/joint-series-seeded' / key


def validate(output, spec):
    receipt = output / 'prepared.json'
    assert receipt.is_file(), 'PR seeded input requires the declared shared preparation step'
    record = json.loads(receipt.read_text())
    assert record['spec'] == spec, (
        'Seeded preparation must match the selected engine and reference inputs'
    )
    assert tree(output / 'input') == record['input'], (
        'Prepared seeded input must preserve every authenticated staged observation and parameter'
    )
    profile = output / 'profiles.npz'
    assert profile.is_file(), 'Seeded preparation must retain its calculated fixed-profile basis'
    assert digest(profile) == record['profiles'], (
        'The conditional linear reference must retain the prepared profile bytes'
    )
    return output / 'input', profile


def prepared(root, engine):
    spec = specification(root, engine)
    path, profile = validate(directory(root, spec), spec)
    with np.load(profile, allow_pickle=False) as arrays:
        baseline = {
            bank: arrays['base_' + str(i)].copy() for i, bank in enumerate(ncaf.BANKS[:BANKS])
        }
        columns = {
            bank: arrays['profile_' + str(i)].copy() for i, bank in enumerate(ncaf.BANKS[:BANKS])
        }
    return path, (baseline, columns)


def build(root, engine):
    spec = specification(root, engine)
    output = directory(root, spec)
    if (output / 'prepared.json').exists():
        validate(output, spec)
        return output
    output.mkdir(parents=True, exist_ok=True)
    lock = output / 'preparing'
    lock.mkdir()
    try:
        path = ncaf.prepare(output / 'input', points=POINTS, descent='fast_descent', small=True)
        model = engine.Project.load(path)
        ncaf.fixed_atoms(model)
        model.analysis.fitting_mode = 'joint'
        baseline, columns = ncaf.linear_profiles(model)
        values = {}
        for i, bank in enumerate(ncaf.BANKS[:BANKS]):
            values['base_' + str(i)] = baseline[bank]
            values['profile_' + str(i)] = columns[bank]
        np.savez(output / 'profiles.npz', **values)
        record = {'spec': spec, 'input': tree(path), 'profiles': digest(output / 'profiles.npz')}
        (output / 'prepared.json').write_text(json.dumps(record, sort_keys=True) + '\n')
    finally:
        lock.rmdir()
    validate(output, spec)
    return output


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--engine', choices=('crysta', 'edi'), required=True)
    parser.add_argument('--worker', action='store_true')
    args = parser.parse_args()
    if args.worker:
        print(build(ROOT, importlib.import_module(args.engine)), flush=True)
    else:
        subprocess.run(
            [
                sys.executable,
                '-m',
                'tests.fixtures.joint_series.prepare_seeded',
                '--engine',
                args.engine,
                '--worker',
            ],
            check=True,
            timeout=TIMEOUT,
        )


if __name__ == '__main__':
    main()
