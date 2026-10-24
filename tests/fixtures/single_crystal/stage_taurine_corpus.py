"""Stage the sealed converged FullProf reference in the shared fit corpus."""

import argparse
import hashlib
import json
import shutil
from pathlib import Path


def stage(reference, destination):
    record = json.loads((reference / 'reference.json').read_text())
    for name, digest in record['artifacts'].items():
        if hashlib.sha256((reference / name).read_bytes()).hexdigest() != digest:
            message = 'A shared fit case must stage the sealed independent artifacts unchanged'
            raise ValueError(message)
    destination.mkdir(parents=True, exist_ok=False)
    for name in record['artifacts']:
        target = destination/name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(reference/name, target)
    shutil.copyfile(reference / 'reference.json', destination / 'reference.json')
    shutil.copyfile(reference / 'PROVENANCE.md', destination / 'PROVENANCE.md')
    quantities = {}
    for key, value, bound in [
        ('n_free', record['n_free'], 0),
        ('n_points_fitted', record['n_selected'], 0),
        (
            'reduced_chi_square',
            record['reduced_chi_square_from_printed_rows'],
            record['reduced_chi_square_from_printed_rows'] * 0.01,
        ),
    ]:
        quantities[key] = {'value': value, 'kind': 'reference', 'tol_abs': bound, 'tol_rel': None}
    expected = {
        'schema': 1,
        'source': {
            'engine': record['engine'],
            'artifact': 'reference.json',
            'provenance': 'PROVENANCE.md',
        },
        'quantities': quantities,
    }
    (destination / 'expected.json').write_text(json.dumps(expected, indent=2) + '\n')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--reference', type=Path, required=True)
    parser.add_argument('--destination', type=Path, required=True)
    arguments = parser.parse_args()
    stage(arguments.reference, arguments.destination)
