import itertools
import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(sys.argv[1])))
from tests.fixtures.palette_sources import oklab_reference as reference

witnesses = [
    ('Default', '#03A9F4', 'light'),
    ('Default', '#4CAF50', 'light'),
    ('Default', '#FFC107', 'light'),
    ('Okabe-Ito', '#009E73', 'dark'),
    ('Tol', '#CCBB44', 'light'),
    ('Vivid', '#4DAF4A', 'light'),
]
ref = []
for label, source, theme in witnesses:
    bg = '#FFFFFF' if theme == 'light' else '#444444'
    calc = '#F44336' if theme == 'light' else '#EF9A9A'
    ideal = reference.smallest_adaptation(source, bg, calc)
    ref.append((label, source, theme, bg, calc, ideal))
M = np.array(reference.RGB_TO_LMS)
N = np.array(reference.LMS_TO_LAB)


def lab(v):
    linear = np.where(v <= 0.04045, v / 12.92, ((v + 0.055) / 1.055) ** 2.4)
    return np.cbrt(linear @ M.T) @ N.T


found = [[] for _ in ref]
nearest = [None for _ in ref]
g, b = np.meshgrid(np.arange(256), np.arange(256), indexing='ij')
for red in range(256):
    coords = np.column_stack((np.full(65536, red), g.ravel(), b.ravel()))
    v = coords / 255
    values = lab(v)
    # Explicitly enumerate every vertex of every half-LSB cell, no monotonicity assumption.
    tol = np.zeros(65536)
    hue_tol = np.zeros(65536)
    hue = np.degrees(np.arctan2(values[:, 2], values[:, 1]))
    for signs in itertools.product((-0.5, 0.5), repeat=3):
        vertex = lab(np.clip(v + np.array(signs) / 255, 0, 1))
        tol = np.maximum(tol, np.abs(vertex[:, 0] - values[:, 0]))
        hue_tol = np.maximum(
            hue_tol,
            np.abs((np.degrees(np.arctan2(vertex[:, 2], vertex[:, 1])) - hue + 180) % 360 - 180),
        )
    for i, (_, source, _theme, bg, calc, ideal) in enumerate(ref):
        delta = np.abs(values[:, 0] - ideal[0])
        source_hue = reference.polar(source)[2]
        angle = np.abs(
            (np.degrees(np.arctan2(values[:, 2], values[:, 1])) - source_hue + 180) % 360 - 180
        )
        # Nearest/full-step candidates are searched in the same exhaustive lattice.
        chosen = np.nonzero((delta <= 2 * tol + 2e-7) & (angle <= hue_tol + 1e-5))[0]
        for j in chosen:
            hx = '#' + ''.join(f'{x:02X}' for x in coords[j])
            if (
                reference.contrast(hx, bg) < 3
                or reference.distance(hx, calc) < 0.10
                or not reference.gamut_hue_chroma_preserved(source, hx)
            ):
                continue
            d = float(delta[j])
            half = reference.lightness_quantisation_tolerance(hx)
            if d <= half:
                found[i].append((hx, d, half))
            if nearest[i] is None or d < nearest[i][1]:
                nearest[i] = (hx, d, half)
    if red % 16 == 0:
        print('exhaustive red channel', red, flush=True)
print(
    json.dumps(
        [
            {
                'scheme': t[0],
                'source': t[1],
                'theme': t[2],
                'half_step_passing': found[i],
                'nearest_passing_within_full_step': nearest[i],
            }
            for i, t in enumerate(ref)
        ],
        indent=2,
    )
)
