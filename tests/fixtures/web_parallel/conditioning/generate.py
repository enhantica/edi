"""Add conditioning quantities from a pre-web native fit, preserving scientific captures."""

import argparse
import hashlib
import json
import math
from decimal import Decimal, localcontext
from pathlib import Path

import numpy as np

from tests.fixtures.web_parallel import numeric

HERE = Path(__file__).resolve().parent.parent


def inverse(matrix):
    """Invert the captured native Gram matrix independently at 80 decimal digits."""
    with localcontext() as context:
        context.prec = 80
        n = len(matrix)
        rows = [
            [Decimal(x) for x in row] + [Decimal(int(i == j)) for j in range(n)]
            for i, row in enumerate(matrix)
        ]
        for k in range(n):
            pivot = max(range(k, n), key=lambda i: abs(rows[i][k]))
            if not rows[pivot][k]:
                raise ValueError('native conditioning requires a nonsingular Gram matrix')
            rows[k], rows[pivot] = rows[pivot], rows[k]
            divisor = rows[k][k]
            rows[k] = [x / divisor for x in rows[k]]
            for i in range(n):
                if i == k:
                    continue
                factor = rows[i][k]
                rows[i] = [a - factor * b for a, b in zip(rows[i], rows[k], strict=True)]
        return [[float(x) for x in row[n:]] for row in rows]


def bind_uncertainties(scientific, raw, covariance):
    """Bind saved native operands to the same native covariance columns."""
    n = len(raw['labels'])
    bindings = []
    seen = set()
    for document, rows in scientific.items():
        for ri, row in enumerate(rows):
            for ti, token in enumerate(row):
                operand = numeric._operand(token)
                if operand is None or operand[1] is None or operand[1] == 0:
                    continue
                value, sigma, _ = operand
                candidates = [
                    i
                    for i in range(n)
                    if math.isclose(value, raw['values'][i], rel_tol=1e-9, abs_tol=1e-11)
                    and math.isclose(
                        sigma, math.sqrt(covariance[i, i]), rel_tol=5e-9, abs_tol=5e-10
                    )
                ]
                if len(candidates) != 1:
                    raise ValueError(
                        'native conditioning must uniquely bind every saved uncertainty'
                    )
                i = candidates[0]
                bindings.append([document, ri, ti, i])
                seen.add(i)
    if not seen:
        raise ValueError('native conditioning requires saved fitted uncertainties')
    return bindings


def generate(case, raw_path, executable, sdk_manifest):
    raw = json.loads(raw_path.read_text())
    fixture = json.loads((HERE / f'{case}-native.json').read_text())
    scalars = dict(fixture['scientific']['analysis/analysis.edi'])
    if (
        raw['n_data'] != int(scalars['_fit_result.n_data_points'])
        or raw['iterations'] != int(scalars['_fit_result.iterations'])
        or not math.isclose(
            raw['reduced_chi_square'],
            float(scalars['_fit_result.reduced_chi_square']),
            rel_tol=1e-9,
            abs_tol=1e-11,
        )
    ):
        raise ValueError('native conditioning must belong to the unchanged captured fit')
    n = len(raw['labels'])
    normal = np.array(raw['normal']).reshape(n, n)
    covariance = np.array(raw['covariance']).reshape(n, n)
    np.linalg.cholesky(normal)
    scale = np.sqrt(np.diag(normal))
    scaled = normal / np.outer(scale, scale)
    singular = np.linalg.eigvalsh(scaled)
    if singular[0] <= 1e-15 * singular[-1]:
        raise ValueError('native conditioning refuses a covariance rank-cutoff boundary')
    bindings = bind_uncertainties(fixture['scientific'], raw, covariance)
    digest = hashlib.sha256(json.dumps(fixture['scientific'], sort_keys=True).encode()).hexdigest()
    result = {
        'reference': 'pre-web native SDK covariance and final weighted Jacobian',
        'sdk_source': json.loads(sdk_manifest.read_text())['source_sha'],
        'sdk_manifest_sha256': hashlib.sha256(sdk_manifest.read_bytes()).hexdigest(),
        'executable_sha256': hashlib.sha256(executable.read_bytes()).hexdigest(),
        'raw_capture_sha256': hashlib.sha256(raw_path.read_bytes()).hexdigest(),
        'scientific_sha256': digest,
        'n_data': raw['n_data'],
        'labels': raw['labels'],
        'scaled_normal': scaled.tolist(),
        'scaled_inverse_normal': inverse(scaled.tolist()),
        'bindings': bindings,
    }
    (HERE / f'{case}-conditioning.json').write_text(json.dumps(result, indent=2) + '\n')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('case', choices=['lbco', 'ncaf'])
    parser.add_argument('raw', type=Path)
    parser.add_argument('executable', type=Path)
    parser.add_argument('sdk_manifest', type=Path)
    args = parser.parse_args()
    generate(args.case, args.raw, args.executable, args.sdk_manifest)
