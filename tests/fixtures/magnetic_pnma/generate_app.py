"""Materialise the native magnetic input for the rendered app gates."""

import json
from pathlib import Path

import numpy as np

from tests.fixtures.magnetic_pnma import reference

if __name__ == '__main__':
    root = Path(__file__).parent / 'app-project'
    if not root.exists():
        reference.project(root)

    # Orthorhombic Bragg law and the independently expanded signed Pnma moments.
    angles = set()
    for h in range(12):
        for k in range(7):
            for index_l in range(6):
                if h == k == index_l == 0:
                    continue
                reciprocal = np.linalg.norm(
                    np.array([h, k, index_l]) / [10.308064, 6.002187, 4.787394]
                )
                argument = 1.87 * reciprocal / 2
                if argument >= 1 or reference.magnetic_squared((h, k, index_l)) < 1e-10:
                    continue
                angle = float(2 * np.degrees(np.arcsin(argument)) + 0.29433)
                if 7.996 < angle < 150.05 and not 64.65 <= angle <= 64.74:
                    angles.add(round(angle, 7))
    (root.parent / 'magnetic-ticks.json').write_text(json.dumps(sorted(angles), indent=2) + '\n')
