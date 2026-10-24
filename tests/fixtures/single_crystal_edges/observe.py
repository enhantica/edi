"""Run the real model observer; crashes and truncated protocols are never refusals."""

import os
import subprocess
from collections import defaultdict


def observe(executable, root, action, *arguments):
    result = subprocess.run(
        [
            str(executable),
            str(root),
            action,
            str(root.parent / (root.name + '-saved')),
            *map(str, arguments),
        ],
        check=False,
        text=True,
        capture_output=True,
        timeout=15,
        env={**os.environ, 'OMP_NUM_THREADS': '1', 'OPENBLAS_NUM_THREADS': '1'},
    )
    if (
        result.returncode
        or not result.stdout.startswith('BEGIN\n')
        or not result.stdout.endswith('END\n')
    ):
        message = (
            'Reflection model must terminate normally with a complete observation, '
            f'never crash on malformed input: {result.returncode}\n'
            f'{result.stdout}\n{result.stderr}'
        )
        raise AssertionError(message)
    rows = defaultdict(list)
    for line in result.stdout.splitlines()[1:-1]:
        key, *values = line.split('\t')
        rows[key].append(values)
    rows['error'] = bytes.fromhex(rows['error'][0][0]).decode()
    rows['ok'] = rows['ok'] == [['1']]
    rows['notes'] = result.stderr
    return rows


def snapshot(rows, prefix):
    return {
        key.removeprefix(prefix): value for key, value in rows.items() if key.startswith(prefix)
    }


def params(rows, prefix='after:'):
    return {
        name: (float(value), free == '1', start)
        for name, value, free, start in rows[prefix + 'param']
    }


def numbers(rows, key):
    return list(map(float, rows[key][0]))
