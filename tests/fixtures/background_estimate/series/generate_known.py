"Author cubic controls and extract committed FullProf fitted backgrounds once."

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
from numpy.polynomial import chebyshev, polynomial
from pybaselines import Baseline

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--output', required=True, type=Path)
args = parser.parse_args()
root = Path(__file__).resolve().parents[2]
dest = args.output
if dest.exists():
    message = 'Independent known-order controls must be generated into a new directory'
    raise FileExistsError(message)
dest.mkdir(parents=True)
src = root / 'background_estimate/comparison'


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


meta = {
    'command': (
        'python '
        'tests/fixtures/background_estimate/series/generate_known.py '
        '--output ../background-reference/series'
    ),
    'numpy': np.__version__,
    'pybaselines': '1.2.1',
    'cases': {},
}
# Cubic truth in each declared basis. LCG values are authored, not any product output.
x = np.linspace(20, 80, 1025)
state = 0xC34B28
noise = []
for _i in range(len(x)):
    state = (1664525 * state + 1013904223) & 0xFFFFFFFF
    noise.append(0.2 * (state / 4294967295 - 0.5))
noise = np.array(noise)
origin = 47.125
low = 17.0
high = 86.0
sigma = 0.15
centers = [27.0, 36.0, 49.0, 63.0, 74.0]
peaks = sum(100 * np.exp(-0.5 * ((x - center) / sigma) ** 2) for center in centers)
mask = np.any(abs(x[:, None] - np.array(centers)[None, :]) < 0.8, axis=1)
for kind in ['polynomial', 'chebyshev']:
    z = x / origin - 1 if kind == 'polynomial' else (2 * x - low - high) / (high - low)
    basis = polynomial if kind == 'polynomial' else chebyshev
    ev = basis.polyval if kind == 'polynomial' else basis.chebval
    truth = [50.0, 12.0, -5.0, 7.0]
    y = ev(z, truth) + noise + peaks
    curve = Baseline(x).arpls(y, lam=1000)[0]
    mad = 1.4826 * np.median(abs(np.diff(y, 2) - np.median(np.diff(y, 2)))) / np.sqrt(6)
    tolerance = 2 * mad
    radius = 3
    top = np.array([
        np.mean(y[max(0, i - radius) : min(len(y), i + radius + 1)]) for i in range(len(y))
    ])
    target = np.minimum(np.maximum(curve, 0), top)
    errors = []
    for count in range(1, 7):
        fit = (basis.polyfit if kind == 'polynomial' else basis.chebfit)(
            z[~mask], target[~mask], count - 1
        )
        err = np.max(abs(ev(z[~mask], fit) - target[~mask]))
        errors.append(float(err))
    print(
        kind,
        'noise',
        mad,
        'errors',
        errors,
        'coeferr',
        np.max(
            abs(
                (basis.polyfit if kind == 'polynomial' else basis.chebfit)(
                    z[~mask], target[~mask], 3
                )
                - truth
            )
        ),
        flush=True,
    )
    path = dest / ('known-' + kind + '.oracle')
    lines = [f'{len(x)} {origin:.17g} {low:.17g} {high:.17g} {mad:.17g} 4 .3']
    lines += [
        ' '.join(f'{v:.17g}' for v in row)
        for row in zip(x, y, mask.astype(float), ev(z, truth), strict=True)
    ]
    lines += [' '.join(map(str, truth))]
    path.write_text('\n'.join(lines) + '\n')
    np.savetxt(
        dest / ('known-' + kind + '.xye'), np.column_stack([x, y, np.ones(len(x))]), fmt='%.17g'
    )
    meta['cases']['known-' + kind] = {
        'sha256': sha(path),
        'seed': '0xC34B28',
        'noise': 'LCG32 uniform bounded +/-0.1',
        'truth': truth,
        'origin': origin,
        'domain': [low, high],
        'stage1': 'pybaselines Baseline.arpls(lam=1000)',
        'width': 6,
        'noise_mad': mad,
        'noise_convention': 'second-difference MAD * 1.4826 / sqrt(6), diffraction-lib constant',
        'candidate_errors': errors,
        'coefficient_absolute_tolerance': 0.3,
    }
(dest / 'controls.json').write_text(json.dumps(meta, indent=2) + '\n')
