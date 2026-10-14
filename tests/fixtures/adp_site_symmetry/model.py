"""Two distinct atoms on one independently specified Wyckoff site."""

import json
import math
from pathlib import Path

import numpy as np

REFERENCE = json.loads(Path(__file__).with_name('reference.json').read_text())
SITES = REFERENCE['sites']
SUFFIXES = ('11', '22', '33', '12', '13', '23')
KINDS = ('Uani', 'Bani', 'beta')
LABELS = ('La', 'Ba')
BISO = 8 * math.pi**2 * 0.023


def tensor(row, kind, atom=0):
    return np.asarray(row['types'][kind]['positive']) * (1 + 0.7 * atom)


def site(project, atom):
    rows = [row for row in project.structure.atom_sites if row.id == LABELS[atom]]
    assert len(rows) == 1, 'Each authored atom must retain its unique site identity'
    return rows[0]


def parameters(project, atom):
    rows = [row for row in project.structure.atom_site_aniso if row.id == LABELS[atom]]
    assert len(rows) == 1, 'A tensor row must belong to its authored atom identity'
    row = rows[0]
    return [getattr(row, 'adp_' + suffix) for suffix in SUFFIXES]


def components(project, atom):
    return np.asarray([parameter.value for parameter in parameters(project, atom)])


def basis(row, kind):
    return np.asarray(row['types'][kind]['basis']).T


def equivalent(row, kind, values):  # noqa: PLR0914 - explicit tensor/metric coefficients
    # trace(Ucart)/3 = sum_ij Ustar_ij * direct_metric_ij / 3.
    # U_cif_ij = Ustar_ij / (a*_i a*_j); beta = 2*pi^2 Ustar.
    a, b, c, alpha, beta, gamma = row['cell']
    ca, cb, cg = np.cos(np.radians([alpha, beta, gamma]))
    metric = np.array([
        [a * a, a * b * cg, a * c * cb],
        [a * b * cg, b * b, b * c * ca],
        [a * c * cb, b * c * ca, c * c],
    ])
    reciprocal = np.sqrt(np.diag(np.linalg.inv(metric)))
    x, y, z, xy, xz, yz = values
    represented = np.array([[x, xy, xz], [xy, y, yz], [xz, yz, z]])
    if kind == 'beta':
        return float(4 * np.sum(represented * metric) / 3)
    star = represented * np.outer(reciprocal, reciprocal)
    return float(np.sum(star * metric) / 3)


def materialize(root, row, kind, *, measured=None, overrides=None):
    root = Path(root)
    (root / 'structures').mkdir(parents=True, exist_ok=True)
    (root / 'project.edi').write_text('_edi.schema_version 3\n_metadata.name adp_site_symmetry\n')
    (root / 'experiments').mkdir(exist_ok=True)
    text = f'data_structure\n_edi.schema_version 3\n_space_group.name_h_m "{row["hm"]}"\n'
    if row['code'] != '-':
        text += f'_space_group.coord_system_code {row["code"]}\n'
    names = ('length_a', 'length_b', 'length_c', 'angle_alpha', 'angle_beta', 'angle_gamma')
    text += ''.join(
        f'_cell.{name} {value:.17g}\n' for name, value in zip(names, row['cell'], strict=True)
    )
    text += 'loop_\n' + ''.join(
        '_atom_site.' + name + '\n'
        for name in (
            'id',
            'type_symbol',
            'wyckoff_letter',
            'adp_type',
            'fract_x',
            'fract_y',
            'fract_z',
            'occupancy',
            'adp_iso',
        )
    )
    xyz = ' '.join(f'{value:.17g}' for value in row['xyz'])
    for atom, symbol in enumerate(('La', 'Ba')):
        scalar = (0.023 if kind in {'Uiso', 'Uani'} else BISO) * (1 + 0.7 * atom)
        if kind in KINDS:
            scalar = equivalent(row, kind, (overrides or {}).get(atom, tensor(row, kind, atom)))
        text += f'{symbol} {symbol} {row["letter"]} {kind} {xyz} 0.5 {scalar:.17g}\n'
    if kind in KINDS:
        text += 'loop_\n_atom_site_aniso.id\n' + ''.join(
            '_atom_site_aniso.adp_' + s + '\n' for s in SUFFIXES
        )
        for atom, symbol in enumerate(('La', 'Ba')):
            values = (overrides or {}).get(atom, tensor(row, kind, atom))
            text += symbol + ' ' + ' '.join(f'{value:.17g}' for value in values) + '\n'
    (root / 'structures/structure.edi').write_text(text)
    grid = np.linspace(20, 110, 241)
    values = np.zeros(len(grid)) if measured is None else measured
    experiment = """data_bank
_edi.schema_version 3
_experiment_type.sample_form powder
_experiment_type.radiation_probe neutron
_experiment_type.scattering_type bragg
_experiment_type.beam_mode "constant wavelength"
_scattering_source.neutron_scattering_length sears1992
_peak.type cwl-tch-pseudo-voigt
_peak.broad_gauss_u 0.036631
_peak.broad_gauss_v -0.068345
_peak.broad_gauss_w 0.131426
_peak.broad_lorentz_x 0
_peak.broad_lorentz_y 0
_peak.cutoff_fwhm 20
_instrument.setup_wavelength 1.54822
_instrument.calib_twotheta_offset 0
loop_
_linked_structure.structure_id
_linked_structure.scale
structure 1
loop_
_data.two_theta
_data.intensity_meas
_data.intensity_meas_su
"""
    experiment += ''.join(f'{x:.17g} {y:.17g} 1\n' for x, y in zip(grid, values, strict=True))
    (root / 'experiments/bank.edi').write_text(experiment)
    (root / 'analysis').mkdir(exist_ok=True)
    (root / 'analysis/analysis.edi').write_text(
        '_edi.schema_version 3\n_minimizer.max_iterations 40\n'
    )
    return root
