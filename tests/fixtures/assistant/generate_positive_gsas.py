"""Generate an independent positive source with the pinned upstream GSAS-II runtime.

Run explicitly with GSASIIscriptable and its native kernels installed. This
trusted fixture generator creates GPX; it is not an untrusted project reader.
"""

import argparse
import hashlib
import json
import random
from pathlib import Path

import numpy as np
from GSASII import GSASIImath, GSASIIpwd, GSASIIscriptable, GSASIIspc

random.seed(731)
np.random.seed(731)  # noqa: NPY002 - upstream GSAS-II uses NumPy global RNG
parser = argparse.ArgumentParser()
parser.add_argument(
    '--source-dir', type=Path, default=Path(__file__).resolve().parent / 'reference'
)
parser.add_argument(
    '--output-dir', type=Path, default=Path(__file__).resolve().parent / 'reference/positive-gsas'
)
args = parser.parse_args()
source = args.source_dir.resolve()
out = args.output_dir.resolve()
out.mkdir(exist_ok=True)
print('Trusted independent GSAS-II positive source generation', flush=True)
print('symmetry', GSASIIspc.SpcGroup('P n m a')[0], flush=True)
project = GSASIIscriptable.G2Project(newgpx=str(out / 'positive-pbso4.gpx'))
hist = project.add_powder_histogram(str(source / 'PBSO4.CWN'), str(source / 'inst_d1a.prm'))
phase = project.add_phase(str(source / 'PbSO4-Wyckoff.cif'), 'PbSO4', histograms=[hist])
for atom, uiso in zip(phase.data['Atoms'], [0.0073, 0.0121, 0.0187, 0.0094, 0.0235], strict=True):
    atom[10] = uiso
phase.data['Atoms'][-1][6] = 0.83
instrument = hist.data['Instrument Parameters'][0]
for key, value in {
    'U': 120.3,
    'V': -45.7,
    'W': 80.2,
    'X': 13.5,
    'Y': 4.2,
    'Z': 0.0,
    'SH/L': 0.01,
}.items():
    instrument[key] = [value, value, False]
hist.data['Background'] = [
    ['chebyschev-1', False, 3, 113.0, 17.0, -9.0],
    {
        'nDebye': 0,
        'debyeTerms': [],
        'nPeaks': 0,
        'peaksList': [],
        'background PWDR': ['', 1.0, False],
    },
]
hist.data['Sample Parameters']['Scale'] = [2350.0, False]
sample = phase.data['Histograms'][hist.name]
sample['Size'][1] = [7.5, 7.5, 1.0]
sample['Mustrain'][1] = [137.0, 137.0, 1.0]
sample['HStrain'][0] = [0.0 for _ in sample['HStrain'][0]]
sample['HStrain'][1] = [False for _ in sample['HStrain'][1]]
project.set_Controls('cycles', 0)
project.save()
project.do_refinements([{}])
project.save()
arrays = [
    np.asarray(hist.getdata(name)).tolist()
    for name in ['x', 'yobs', 'yweight', 'ycalc', 'background']
]
result = {
    'schema': 'independent-gsas-positive/1',
    'source_revision': 'c67a261f771a71461f6080a77efd91ab265abdf2',
    'source_gpx_sha256': hashlib.sha256((out / 'positive-pbso4.gpx').read_bytes()).hexdigest(),
    'phase': {
        'name': phase.name,
        'cell': phase.data['General']['Cell'],
        'space_group': phase.data['General']['SGData']['SpGrp'],
        'atoms': phase.data['Atoms'],
        'histogram': sample,
    },
    'histogram': {
        key: hist.data[key]
        for key in ['Instrument Parameters', 'Background', 'Sample Parameters', 'Limits']
    },
    'array_columns': ['two_theta', 'observed', 'weight', 'calculated', 'background'],
    'arrays': arrays,
}


def default(value):
    if isinstance(value, np.ndarray):
        return value.tolist()
    if isinstance(value, np.generic):
        return value.item()
    raise TypeError(type(value).__name__)


(out / 'positive-source-and-pattern.json').write_text(
    json.dumps(result, indent=2, default=default, allow_nan=False) + '\n'
)
print(
    'GPX',
    result['source_gpx_sha256'],
    'points',
    len(arrays[0]),
    'calc_nonzero',
    np.count_nonzero(arrays[3]),
    flush=True,
)
angles = np.array([10.0, 32.5, 73.0, 121.75, 155.85])
backgrounds = {}
for basis in ['chebyschev', 'chebyschev-1', 'cosine']:
    values, _ = GSASIIpwd.getBackground(
        '', {'Lam': 1.909, 'Back;0': 113.0, 'Back;1': 17.0, 'Back;2': -9.0}, basis, 'PNC', angles
    )
    backgrounds[basis] = values.tolist()
widths = []
for angle in [73.0, 121.75]:
    coefficients = {key: instrument[key][1] for key in ['U', 'V', 'W', 'X', 'Y', 'Z']}
    variance = GSASIImath.getCWsig(coefficients, angle)
    gamma = GSASIImath.getCWgam(coefficients, angle)
    widths.append({
        'two_theta_deg': angle,
        'variance_centideg_squared': variance,
        'gaussian_fwhm_squared_deg': 8 * np.log(2) * variance / 10000.0,
        'lorentz_fwhm_deg_instrument': gamma / 100.0,
        'lorentz_fwhm_deg_with_isotropic_sample': (
            gamma
            + 1.8 * 1.909 / (np.pi * 7.5 * np.cos(np.deg2rad(angle / 2)))
            + 0.018 * 137 * np.tan(np.deg2rad(angle / 2)) / np.pi
        )
        / 100.0,
    })
witnesses = {
    'schema': 'independent-assistant-seams/1',
    'gsas_source_revision': result['source_revision'],
    'weight_sigma': [
        {'index': i, 'weight': arrays[2][i], 'sigma': float(1 / np.sqrt(arrays[2][i]))}
        for i in [0, 72, 223, 1000, 2200]
    ],
    'displacement': [
        {
            'label': a[0],
            'uiso_angstrom_squared': a[10],
            'biso_angstrom_squared': float(8 * np.pi**2 * a[10]),
        }
        for a in phase.data['Atoms']
    ],
    'occupancy': [
        {'label': a[0], 'site_occupancy': a[6], 'site_multiplicity': a[8]}
        for a in phase.data['Atoms']
    ],
    'widths': widths,
    'background': {
        'angles_deg': angles.tolist(),
        'coefficients': [113.0, 17.0, -9.0],
        'values_by_declared_basis': backgrounds,
    },
    'fullprof': {
        'source': 'knowledge/fitting/fullprof/pd-neut-cwl_cosio-d20_biso-tied/PROVENANCE.md',
        'occupancy': [
            {
                'label': 'Co1',
                'site_multiplicity': 4,
                'general_multiplicity': 8,
                'pcr_occ': 0.5,
                'site_occupancy': 1.0,
            },
            {
                'label': 'O3',
                'site_multiplicity': 8,
                'general_multiplicity': 8,
                'pcr_occ': 1.0,
                'site_occupancy': 1.0,
            },
        ],
        'affine_shared_shift': {
            'starts': [0.01, 0.98759],
            'codewords': [181.0, 181.0],
            'shift': 0.15557,
            'values': [0.16557, 1.14316],
            'preserved_offset': 0.97759,
        },
    },
}
(out / 'mapping-witnesses.json').write_text(
    json.dumps(witnesses, indent=2, allow_nan=False) + '\n'
)
print('mapping witnesses', len(widths), len(backgrounds), flush=True)
