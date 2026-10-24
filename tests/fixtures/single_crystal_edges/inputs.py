"""Authored one-atom inputs and closed forms; no engine output supplies an oracle.

The neutron length 10.3 fm is the Sears Ni entry already frozen in the single-crystal
reference corpus. Larson uses ILL Mag2Pol manual eqs. 3.1-3.2. The sphere interpolation
is the independently transcribed Becker-Coppens reference in single_crystal/extinction.py.
"""

from __future__ import annotations

import math
from pathlib import Path

CELL = (5.1, 6.2, 7.3)
HKLS = ((1, 1, 1), (2, 1, 3), (4, 1, 3))
COEFFICIENTS = ('11', '22', '33', '12', '13', '23')
KINDS = (
    'none',
    'larson-isotropic',
    'larson-anisotropic',
    'becker-coppens-type-1',
    'becker-coppens-type-2',
    'becker-coppens-mixed',
)


def bare(hkl, biso=0.41):
    s2 = sum((h / a) ** 2 for h, a in zip(hkl, CELL, strict=True)) / 4
    return (1.03 * 0.73) ** 2 * math.exp(-2 * biso * s2)


def sphere(hkl, wavelength, distribution):
    """Type-II sphere interpolation at nontrivial mm/um and wavelength values."""
    s2 = sum((h / a) ** 2 for h, a in zip(hkl, CELL, strict=True)) / 4
    c = 1 - 2 * wavelength**2 * s2
    x = 1.5 * bare(hkl) * (wavelength * 28.4 / math.prod(CELL)) ** 2
    primary = (
        1 + 2 * x + (0.2 + 0.45 * c) * x * x / (1 + (0.22 - 0.12 * (0.5 - c) ** 2) * x)
    ) ** -0.5
    xs = 1.5 * bare(hkl) * wavelength**2 / math.prod(CELL) ** 2 * 37 * 28.4
    if distribution == 'gaussian':
        a, b, k = 0.58 + 0.48 * c + 0.24 * c * c, 0.02 - 0.025 * c, 2.12
    else:
        a, b, k = 0.025 + 0.285 * c, (0.15 - 0.2 * (0.75 - c) ** 2 if c > 0 else -0.45 * c), 2
    return primary * (1 + k * xs + a * xs * xs / (1 + b * xs)) ** -0.5


def fields(kind, distribution='gaussian', free=None):
    selected = {}
    if kind.startswith('becker'):
        selected['crystal_radius'] = 0.037
        if kind != 'becker-coppens-type-1':
            selected['domain_radius'] = 28.4
        if kind != 'becker-coppens-type-2':
            selected['mosaic_spread'] = 93100
    elif kind == 'larson-isotropic':
        selected['coefficient'] = 30
    elif kind == 'larson-anisotropic':
        selected.update(dict.fromkeys(('coefficient_' + c for c in COEFFICIENTS), 0.3))
    text = f'_extinction.type {kind}\n'
    if distribution is not None and kind.startswith('becker'):
        text += f'_extinction.mosaic_distribution {distribution}\n'
    for key, value in selected.items():
        text += f'_extinction.{key} {value}{"()" if key == free else ""}\n'
    return text


def project(  # noqa: PLR0913 - explicit orthogonal fixture axes
    root,
    *,
    tof=False,
    kind='none',
    distribution='gaussian',
    links=None,
    free=None,
    wavelength='1.6',
    extra='',
    hkls=HKLS,
    measured=None,
    banks=1,
):
    root = Path(root)
    (root / 'structures').mkdir(parents=True)
    (root / 'experiments').mkdir()
    structure = 'data_structure\n_edi.schema_version 3\n_space_group.name_h_m "P 1"\n'
    for key, number in zip(('a', 'b', 'c'), CELL, strict=True):
        structure += f'_cell.length_{key} {number}\n'
    structure += '_cell.angle_alpha 90\n_cell.angle_beta 90\n_cell.angle_gamma 90\n'
    structure += (
        'loop_\n_atom_site.id\n_atom_site.type_symbol\n_atom_site.wyckoff_letter\n'
        '_atom_site.fract_x\n_atom_site.fract_y\n_atom_site.fract_z\n'
        '_atom_site.occupancy\n_atom_site.adp_type\n_atom_site.adp_iso\n'
        'Ni Ni a .13 .27 .39 .73 Biso .41\n'
    )
    (root / 'structures/structure.edi').write_text(structure)
    links = links if links is not None else [('structure', '2.3()', True)]
    if any(key == 'other' for key, _, _ in links):
        (root / 'structures/other.edi').write_text(
            structure.replace('data_structure', 'data_other')
        )
    for bank in range(banks):
        name = 'bank' if banks == 1 else f'bank{bank + 1}'
        text = (
            f'data_{name}\n_edi.schema_version 3\n'
            '_experiment_type.sample_form "single crystal"\n'
            '_experiment_type.radiation_probe neutron\n_experiment_type.scattering_type bragg\n'
            f'_experiment_type.beam_mode "{"time-of-flight" if tof else "constant wavelength"}"\n'
            '_scattering_source.neutron_scattering_length sears1992\n'
        )
        if not tof:
            text += f'_instrument.setup_wavelength {wavelength}\n'
        text += fields(kind, distribution, free)
        text += (
            'loop_\n_linked_structure.structure_id\n'
            '_linked_structure.scale\n_linked_structure.enabled\n'
        )
        text += ''.join(
            f'{key} {scale} {"true" if enabled else "false"}\n' for key, scale, enabled in links
        )
        text += extra + '\nloop_\n_refln.index_h\n_refln.index_k\n_refln.index_l\n'
        text += '_refln.intensity_meas\n_refln.intensity_meas_su\n'
        if tof:
            text += '_refln.wavelength\n'
        for i, hkl in enumerate(hkls):
            observation = measured[bank][i] if measured is not None else 4.7 * bare(hkl)
            text += (
                ' '.join(map(str, (*hkl, observation, 0.3, *([1.2 + 0.2 * i] if tof else []))))
                + '\n'
            )
        (root / f'experiments/{name}.edi').write_text(text)
    return root


def relations(root, aliases, expressions):
    (root / 'analysis').mkdir(exist_ok=True)
    text = '_edi.schema_version 3\n'
    text += 'loop_\n_alias.id\n_alias.parameter_unique_name\n'
    text += ''.join(f'{key} {name}\n' for key, name in aliases.items())
    text += 'loop_\n_constraint.id\n_constraint.expression\n_constraint.enabled\n'
    text += ''.join(
        f'{expression.split("=")[0].strip()} "{expression}" true\n' for expression in expressions
    )
    (root / 'analysis/analysis.edi').write_text(text)


def weighted(root, weights):
    hkl = HKLS[0]
    root = project(
        root,
        kind='larson-isotropic',
        free='coefficient',
        banks=2,
        links=[('structure', '1', True)],
        hkls=(hkl,) * 3,
        measured=[[bare(hkl) * factor] * 3 for factor in (0.5, 0.8)],
    )
    relations(
        root, {'a': 'bank1.extinction.coefficient', 'b': 'bank2.extinction.coefficient'}, ['b = a']
    )
    with (root / 'analysis/analysis.edi').open('a') as stream:
        stream.write(
            '_fitting_mode.type joint\nloop_\n_joint_fit.experiment_id\n_joint_fit.weight\n'
        )
        stream.write(f'bank1 {weights[0]}\nbank2 {weights[1]}\n')
    s2 = sum((h / a) ** 2 for h, a in zip(hkl, CELL, strict=True)) / 4
    sine = 2 * 1.6 * math.sqrt(s2) * math.sqrt(1 - 1.6**2 * s2)
    factor = 0.001 * bare(hkl) * 1.6**3 / sine
    mean = (weights[0] * 0.5 + weights[1] * 0.8) / sum(weights)
    coefficient = (mean**-2 - 1) / factor
    chi2 = (
        3
        * bare(hkl) ** 2
        / 0.3**2
        * sum(w * (y - mean) ** 2 for w, y in zip(weights, (0.5, 0.8), strict=True))
        / 5
    )
    return root, coefficient, chi2


def powder(root):
    root = project(root)
    text = (
        'data_bank\n_edi.schema_version 3\n_experiment_type.sample_form powder\n'
        '_experiment_type.radiation_probe neutron\n_experiment_type.scattering_type bragg\n'
        '_experiment_type.beam_mode "constant wavelength"\n'
        '_instrument.setup_wavelength 1.54\n_instrument.calib_twotheta_offset 0\n'
        '_peak.type cwl-tch-pseudo-voigt\n'
        '_peak.broad_gauss_u 0\n_peak.broad_gauss_v 0\n_peak.broad_gauss_w .15\n'
        '_peak.broad_lorentz_x 0\n_peak.broad_lorentz_y 0\n'
        '_background.type polynomial\n_background.origin 40\n'
        'loop_\n_background.id\n_background.order\n_background.coef\n'
        'base 0 4\nloop_\n_linked_structure.structure_id\n_linked_structure.scale\nstructure .7\n'
        'loop_\n_data.two_theta\n_data.intensity_meas\n_data.intensity_meas_su\n'
    )
    text += ''.join(f'{x} 5 1\n' for x in range(40, 73, 4))
    (root / 'experiments/bank.edi').write_text(text)
    return root
