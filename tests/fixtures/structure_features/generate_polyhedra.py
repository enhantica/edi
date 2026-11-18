"""Independent Cartesian lattice enumeration and affine shell controls."""

import itertools
import json
import math
from pathlib import Path


def multiply(matrix, xyz):
    return [sum(matrix[3 * row + col] * xyz[col] for col in range(3)) for row in range(3)]


def generate():
    orthogonal = [2, 0, 0, 0, 20, 0, 0, 0, 20]
    skew = [2, 6, 0, 0, 2, 0, 0, 0, 20]
    cases = []
    for tag, matrix, fractional, cutoff in [
        ('orthogonal-distance', orthogonal, [[0.25, 0, 0], [0.25, 0.1, 0], [0.25, 0, 0.1]], 5),
        ('skew-distance', skew, [[0.25, 0, 0], [0.25, 0.1, 0], [0.25, 0, 0.05]], 2.5),
        (
            'orthogonal-bonds',
            orthogonal,
            [[0.25, 0.9, 0], [0.25, 0.9, 0.05], [0.25, 0.85, 0.1]],
            0,
        ),
        ('skew-bonds', skew, [[0.25, 0.5, 0], [0.25, 0.5, 0.05], [0.25, 0.4, 0.05]], 0),
    ]:
        points = [multiply(matrix, point) for point in fractional]
        expected = []
        adjacent = set()
        # Bounds certified in README: b,c by their orthogonal components,
        # then a by x = 2a + 6b + x_site, including the skew cancellation.
        for point, original in zip(fractional, points, strict=True):
            radius = cutoff or math.dist(original, [0, 0, 0])
            for shift in itertools.product(range(-20, 21), range(-3, 4), range(-2, 3)):
                xyz = multiply(matrix, [a + b for a, b in zip(point, shift, strict=True)])
                if 1e-9 < math.dist(xyz, [0, 0, 0]) <= radius + 1e-9:
                    expected.append(xyz)
                    if max(map(abs, shift)) <= 1:
                        adjacent.add(tuple(round(value, 10) for value in xyz))
        expected = sorted({tuple(round(value, 10) for value in xyz) for xyz in expected})
        cases.append({
            'tag': tag,
            'matrix': matrix,
            'fractional': fractional,
            'points': points,
            'cutoff': cutoff,
            'expected': expected,
            'beyond_adjacent': sorted(set(expected) - adjacent),
        })
    shells = [
        {
            'tag': 'coplanar-square',
            'points': [[x, y, x + 2 * y] for x, y in [(-1, -1), (1, -1), (1, 1), (-1, 1)]],
            'faces': 0,
            'volume': 0,
        },
        {
            'tag': 'coplanar-hexagon',
            'points': [
                [
                    math.cos(i * math.pi / 3),
                    math.sin(i * math.pi / 3),
                    math.cos(i * math.pi / 3) + 2 * math.sin(i * math.pi / 3),
                ]
                for i in range(6)
            ],
            'faces': 0,
            'volume': 0,
        },
        {
            'tag': 'octahedron',
            'points': [
                [sign if col == axis else 0 for col in range(3)]
                for axis in range(3)
                for sign in [-1, 1]
            ],
            'faces': 8,
            'volume': 4 / 3,
        },
        {
            'tag': 'cube',
            'points': list(itertools.product([-1, 1], repeat=3)),
            'faces': 12,
            'volume': 8,
        },
    ]
    for shell in shells:
        shell['hull'] = True
    return {'neighbourhoods': cases, 'shells': shells}


if __name__ == '__main__':
    Path(__file__).with_name('polyhedra-reference.json').write_text(
        json.dumps(generate(), indent=2) + '\n'
    )
