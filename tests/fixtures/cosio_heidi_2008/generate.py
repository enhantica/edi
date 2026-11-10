"""Stage BP5014 supplementary data and independent Pnma/Brown/Larson references.

No product import. Scale is absent from the paper CIF: determine one scalar from
nuclear-only FullProf rows, never from magnetic reflections or measured F².
"""

import argparse
import hashlib
import json
import re
import shutil
from pathlib import Path

import gemmi
import numpy as np

HERE = Path(__file__).resolve().parent
TEMPERATURES = {'300K': '300K', '55K': '55K', '2.5K': '2point5K'}
UKEYS = ('11', '22', '33', '12', '13', '23')
MOMENTS = {'Co1': [1.20, 3.64, 0.57], 'Co2': [0.0, 3.35, 0.0]}
MOMENT_SU = {'Co1': [0.03, 0.02, 0.09], 'Co2': [0.0, 0.02, 0.0]}


def number(text):
    value = gemmi.cif.as_number(text)
    match = re.fullmatch(r'([+-]?\d+(?:\.\d+)?)(?:\((\d+)\))?', text)
    su = (
        int(match[2]) * 10 ** (-len(match[1].split('.')[1]) if '.' in match[1] else 0)
        if match and match[2]
        else 0.0
    )
    return [value, su]


def rows(path):
    table = (
        gemmi.cif
        .read_file(str(path))
        .sole_block()
        .find([
            '_refln_index_h',
            '_refln_index_k',
            '_refln_index_l',
            '_refln_F_squared_calc',
            '_refln_F_squared_meas',
            '_refln_F_squared_sigma',
            '_refln_observed_status',
        ])
    )
    return [
        [int(row[i]) for i in range(3)] + [float(row[i]) for i in range(3, 6)] + [row[6]]
        for row in table
    ]


def model(block, magnetic):
    atoms = block.find([
        '_atom_site_label',
        '_atom_site_type_symbol',
        '_atom_site_fract_x',
        '_atom_site_fract_y',
        '_atom_site_fract_z',
    ])
    anis = {
        row[0]: [number(v) for v in list(row)[1:]]
        for row in block.find(
            ['_atom_site_aniso_label'] + ['_atom_site_aniso_U_' + key for key in UKEYS]
        )
    }
    notes = '\n'.join(
        item.pair[1]
        for item in block
        if item.pair and 'anisotropic extinction coefficients' in item.pair[1]
    )
    ext = re.search(r'anisotropic extinction coefficients.*?:\s*([^;]+)', notes, re.DOTALL)[1]
    coefficients = re.findall(r'[+-]?\d+\.\d+(?:\(\d+\))?', ext)[:6]
    if len(coefficients) != 6:
        raise ValueError('The published CIF must state all six extinction coefficients')
    return {
        'cell': [number(block.find_value('_cell_length_' + axis)) for axis in 'abc'],
        'extinction': [number(value) for value in coefficients],
        'sites': [
            {
                'id': row[0],
                'element': row[1].capitalize(),
                'xyz': [number(value) for value in list(row)[2:]],
                'u': anis[row[0]],
                'moment': [
                    [v, s]
                    for v, s in zip(
                        MOMENTS.get(row[0], [0.0] * 3),
                        MOMENT_SU.get(row[0], [0.0] * 3),
                        strict=True,
                    )
                ]
                if magnetic
                else [[0.0, 0.0]] * 3,
            }
            for row in atoms
        ],
    }


def intensity(sample, hkls):  # noqa: PLR0914 - explicit independent physics
    cell = np.array([value[0] for value in sample['cell']])
    h = np.array(hkls, dtype=float)
    q = h / cell
    nuclear = np.zeros(len(h), complex)
    magnetic = np.zeros((len(h), 3), complex)
    for site in sample['sites']:
        xyz = [value[0] for value in site['xyz']]
        mu = np.array([value[0] for value in site['moment']])
        a, b, c, d, e, f = [value[0] for value in site['u']]
        tensor = np.array([[a, d, e], [d, b, f], [e, f, c]])
        seen = set()
        for op in gemmi.find_spacegroup_by_name('Pnma').operations():
            pos = np.array(op.apply_to_xyz(xyz))
            key = tuple(np.round(pos % 1, 7))
            if key in seen:
                continue
            seen.add(key)
            rotation = np.array(op.rot) / op.DEN
            u = rotation @ tensor @ rotation.T
            factor = np.exp(-2 * np.pi**2 * np.einsum('ni,ij,nj->n', q, u, q)) * np.exp(
                2j * np.pi * (h @ pos)
            )
            nuclear += gemmi.Element(site['element']).neutron92.get_coefs()[0] * factor / 10
            magnetic += factor[:, None] * (np.linalg.det(rotation) * rotation @ mu)[None, :]
    perpendicular = magnetic - q * (np.sum(q * magnetic, axis=1) / np.sum(q * q, axis=1))[:, None]
    s2 = np.sum(q * q, axis=1) / 4
    j0 = (
        0.4332 * np.exp(-14.3553 * s2)
        + 0.5857 * np.exp(-4.6077 * s2)
        - 0.0382 * np.exp(-0.1338 * s2)
        + 0.0179
    )
    mag2 = (1.91304273 * 2.8179403262 / 20) ** 2 * j0**2 * np.sum(abs(perpendicular) ** 2, axis=1)
    total = abs(nuclear) ** 2 + mag2
    hh, kk, ll = h.T
    c11, c22, c33, c12, c13, c23 = [value[0] for value in sample['extinction']]
    g = (
        c11 * hh * hh
        + c22 * kk * kk
        + c33 * ll * ll
        + c12 * hh * kk
        + c13 * hh * ll
        + c23 * kk * ll
    ) / (4 * s2)
    sin2theta = 2 * 0.552 * np.sqrt(s2) * np.sqrt(1 - 0.552**2 * s2)
    return total / np.sqrt(1 + 0.001 * g * total * 0.552**3 / sin2theta), mag2


def uncertain_parameters(sample):
    yield from sample['cell']
    yield from sample['extinction']
    for site in sample['sites']:
        yield from site['xyz']
        yield from site['u']
        yield from site['moment']


def build(source):  # noqa: PLR0914 - transparent external reference generation
    target = HERE / 'published'
    target.mkdir(exist_ok=True)
    for name in [f'bp5014-{temp}.hkl' for temp in TEMPERATURES]:
        if (source / name).resolve() != (target / name).resolve():
            shutil.copyfile(source / name, target / name)
    document = gemmi.cif.read_file(str(source / 'bp5014sup1.cif'))
    output = {
        ('source'): (
            'BP5014 (2008), DOI 10.1107/S010876810803214X; moments BP5024 (2009'
            ') Table 4, DOI 10.1107/S0108768109042499'
        ),
        'structure_source_sha256': hashlib.sha256(
            (source / 'bp5014sup1.cif').read_bytes()
        ).hexdigest(),
        'hashes': {
            path.name: hashlib.sha256(path.read_bytes()).hexdigest()
            for path in sorted(target.iterdir())
        },
        ('tolerance'): (
            'Three-s.u. L1 envelope of published CIF / Table 4 perturbations (c'
            'ovariances unavailable), plus 0.005 F² output rounding. Measuremen'
            't sigma is never used.'
        ),
        ('scale'): (
            'One externally calibrated scalar per temperature, least squares ag'
            'ainst nuclear-only FullProf F²calc > 1; no measured intensities or'
            ' product output.'
        ),
        'cases': {},
    }
    for temperature, name in TEMPERATURES.items():
        sample = model(document[name], temperature == '2.5K')
        data = rows(target / f'bp5014-{temperature}.hkl')
        hkl = [row[:3] for row in data]
        expected = np.array([row[3] for row in data])
        calculated, magnetic = intensity(sample, hkl)
        mask = (magnetic < 1e-15) & (expected > 1)
        scale = float(calculated[mask] @ expected[mask] / (calculated[mask] @ calculated[mask]))
        envelope = np.zeros(len(data))
        for value in uncertain_parameters(sample):
            initial, su = value
            if not su:
                continue
            value[0] = initial + su
            plus = intensity(sample, hkl)[0]
            value[0] = initial - su
            minus = intensity(sample, hkl)[0]
            value[0] = initial
            envelope += np.abs(scale * (plus - minus) / 2)
        tolerance = 0.005 + 3 * envelope
        output['cases'][temperature] = {
            'model': sample,
            'scale': scale,
            'rows': data,
            'tolerance': tolerance.tolist(),
            'independent_f2': (scale * calculated).tolist(),
            'magnetic_only': [
                row[:3]
                for row in data
                if gemmi
                .find_spacegroup_by_name('Pnma')
                .operations()
                .is_systematically_absent(row[:3])
            ],
        }
        mismatch = np.abs(scale * calculated - expected) > tolerance
        print(
            temperature,
            'rows',
            len(data),
            'source consistency misses',
            int(np.sum(mismatch)),
            'worst sigma ratio',
            float(max(abs(scale * calculated - expected) / tolerance)),
        )
    (HERE / 'reference.json').write_text(json.dumps(output, indent=2) + '\n')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--source', type=Path, required=True)
    build(parser.parse_args().source)
