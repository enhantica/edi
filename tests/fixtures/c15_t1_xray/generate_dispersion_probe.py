"""Freeze independent DABAX/Cromer-Liberman Fe rows; never import crysta.

Run with the external rietx data file as the sole argument. This distribution
contains FPRIME 3F with the Kissel-Pratt correction, not Sasaki's uncorrected CL.
"""

import hashlib
import json
import math
import sys
from itertools import pairwise
from pathlib import Path

SOURCE = Path(sys.argv[1])
ROOT = Path(__file__).resolve().parent
raw = SOURCE.read_bytes()
section = raw.decode().split('#S  26 Fe\n', 1)[1].split('#S ', 1)[0]
rows = [
    list(map(float, line.split()))
    for line in section.splitlines()
    if line and not line.startswith('#')
]
lo, hi = next((a, b) for a, b in pairwise(rows) if a[0] < 10007 < b[0])
edge_lo, edge_hi = next((a, b) for a, b in pairwise(rows) if b[2] - a[2] > 1)
# CODATA exact SI constants (2019): h*c/e = 12398.419843320026 eV Angstrom.
hc = 12398.419843320026
cases = []
for fraction in (0.25, 0.75):
    energy = lo[0] + fraction * (hi[0] - lo[0])
    # ADR-0066 at 153d5cfb: linear fp in log E, linear log fpp in log E.
    log_fraction = math.log(energy / lo[0]) / math.log(hi[0] / lo[0])
    fp = lo[1] + log_fraction * (hi[1] - lo[1])
    fpp = math.exp(math.log(lo[2]) + log_fraction * math.log(hi[2] / lo[2]))
    cases.append([hc / energy, fp, fpp])
(ROOT / 'cromer_liberman_fe.tsv').write_text(
    ''.join(' '.join(f'{v:.17g}' for v in row) + '\n' for row in cases)
)
manifest = {
    'source': 'ESRF DABAX f1f2_CromerLiberman.dat, FPRIME 3F + Kissel-Pratt',
    'distribution': 'rietx/src/rietx/data/f1f2_CromerLiberman.dat',
    'libraries_commit': '57d1cf5fcad9ba4fd86224eb4047af35214766cd',
    'sha256': hashlib.sha256(raw).hexdigest(),
    'hc_eV_A': hc,
    'interpolation': 'ADR-0066 153d5cfb: fp linear in log E; fpp log-log',
    'smooth_rows': [lo, hi],
    'edge_rows': [edge_lo, edge_hi],
    'edge_wavelength': hc / ((edge_lo[0] + edge_hi[0]) / 2),
    'outside_wavelengths': [hc / 2900, hc / 71000],
    'cases': cases,
}
(ROOT / 'cromer_liberman_fe.json').write_text(json.dumps(manifest, indent=2) + '\n')
(ROOT / 'cromer_liberman_refusals.tsv').write_text(
    ''.join(f'{w:.17g}\n' for w in [manifest['edge_wavelength'], *manifest['outside_wavelengths']])
)
