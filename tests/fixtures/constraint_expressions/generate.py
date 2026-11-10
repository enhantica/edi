"""Write a rational least-squares reference without importing either engine."""

import json
from fractions import Fraction
from pathlib import Path


def reference():
    t = [Fraction(i, 10) for i in range(9)]
    design = [(1 + x * x, x - x * x) for x in t]
    aa = sum(a * a for a, _ in design)
    ab = sum(a * b for a, b in design)
    bb = sum(b * b for _, b in design)
    det = aa * bb - ab * ab
    inverse = ((bb / det, -ab / det), (-ab / det, aa / det))
    noise = [Fraction((-1) ** i, 10) for i in range(9)]
    projection = [sum(row[k] * n for row, n in zip(design, noise, strict=True)) for k in range(2)]
    correction = [sum(row[k] * projection[k] for k in range(2)) for row in inverse]
    residual = [
        n - a * correction[0] - b * correction[1] for (a, b), n in zip(design, noise, strict=True)
    ]
    mse = sum(e * e for e in residual) / (len(t) - 2)
    covariance = [[value * mse for value in row] for row in inverse]
    observed = [a * 5 + b * 2 + e for (a, b), e in zip(design, residual, strict=True)]
    return {
        'provenance': 'Exact rational normal equations for X=[1+t^2,t-t^2], unit weights; '
        'alternating noise projected into the orthogonal complement of X.',
        'x': [float(40 * (1 + x)) for x in t],
        'observed': [float(v) for v in observed],
        'independent': [5, 2],
        'dependent': 3,
        'covariance': [[float(v) for v in row] for row in covariance],
        'dependent_variance': float(covariance[0][0] + covariance[1][1] - 2 * covariance[0][1]),
        'diagonal_only_variance': float(covariance[0][0] + covariance[1][1]),
        'gradient': [1, -1],
        'reduced_chi_square': float(mse),
    }


if __name__ == '__main__':
    Path(__file__).with_name('covariance.json').write_text(
        json.dumps(reference(), indent=2) + '\n'
    )
