"""Select independently frozen cctbx Wyckoff subspaces; never import a product engine."""

import argparse
import hashlib
import itertools
import json
import shlex
from pathlib import Path

import numpy as np

SELECTED = {
    (221, 'a'): 'cubic',
    (123, 'a'): 'tetragonal',
    (191, 'a'): 'hexagonal',
    (1, 'a'): 'general',
}


def generate(table, destinations):
    rows = {}
    for line in table.read_text().splitlines():
        tokens = shlex.split(line)
        key = (int(tokens[0]), tokens[2])
        if key not in SELECTED:
            continue
        rank = int(tokens[13])
        row = {
            'it': key[0],
            'letter': key[1],
            'code': tokens[1],
            'hm': tokens[3],
            'cell': list(map(float, tokens[4:10])),
            'xyz': list(map(float, tokens[10:13])),
            'rank': rank,
            'types': {},
        }
        cursor = 14
        for kind in ('Uani', 'Bani', 'beta'):
            positive = list(map(float, tokens[cursor : cursor + 6]))
            cursor += 6
            basis = [
                list(map(float, tokens[cursor + 6 * i : cursor + 6 * i + 6])) for i in range(rank)
            ]
            cursor += 6 * rank
            row['types'][kind] = {'positive': positive, 'basis': basis}
        if cursor != len(tokens):
            message = 'The cctbx row must retain all three complete subspaces'
            raise ValueError(message)
        rows[SELECTED[key]] = row
    if set(rows) != set(SELECTED.values()):
        message = 'The independent table must supply every selected site symmetry'
        raise ValueError(message)
    output = {
        'reference': 'cctbx-base 2026.8 via anisotropic_adps/generate.py',
        'table_sha256': hashlib.sha256(table.read_bytes()).hexdigest(),
        'sites': rows,
    }
    for directory in destinations:
        directory.mkdir(parents=True, exist_ok=True)
        (directory / 'reference.json').write_text(json.dumps(output, indent=2) + '\n')
    gui_inputs(rows, destinations)


def gui_inputs(rows, destinations):
    from model import equivalent, materialize  # noqa: PLC0415 - load after freezing references

    for directory in destinations:
        gui = {'sites': rows, 'weights': {}, 'completion': {}}
        for name, row in rows.items():
            gui['weights'][name] = {
                kind: [equivalent(row, kind, value) for value in np.eye(6)]
                for kind in ('Uani', 'Bani', 'beta')
            }
            gui['completion'][name] = {}
            for kind in ('Uani', 'Bani', 'beta'):
                matrix = np.asarray(row['types'][kind]['basis']).T
                maps = {}
                for indices in itertools.combinations(range(6), row['rank']):
                    selected = matrix[list(indices)]
                    if np.linalg.matrix_rank(selected) == row['rank']:
                        maps[','.join(map(str, indices))] = (
                            matrix @ np.linalg.inv(selected)
                        ).tolist()
                gui['completion'][name][kind] = maps
            materialize(directory / 'gui' / name, row, 'Biso')
        (directory / 'oracle.js').write_text(
            '.pragma library\nvar frozen = ' + json.dumps(gui) + ';\n'
        )


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--table', type=Path, required=True)
    parser.add_argument('--output', type=Path, action='append', required=True)
    args = parser.parse_args()
    generate(args.table, args.output)
