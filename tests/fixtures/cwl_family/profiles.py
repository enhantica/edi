"""Independent isolated cubic reflection and normalized Npr line shapes."""

import hashlib
import json
import math
import re
from pathlib import Path

import numpy as np

TOKENS = (
    'cwl-gaussian',
    'cwl-lorentzian',
    'cwl-pseudo-voigt',
    'cwl-pseudo-voigt-berar-baldinozzi',
    'cwl-tch-pseudo-voigt',
    'cwl-tch-pseudo-voigt-fcj',
)
RETIRED = ('cwl-thompson-' + 'cox-hastings', 'cwl-pseudo-voigt-berar-' + 'baldinozzi-asymmetry')
U, V, W = 0.061, -0.027, 0.085
ETA, SLOPE = 0.23, 0.0031


def geometry(wavelength=1.54):
    theta = math.asin(wavelength / 8)
    centre = math.degrees(2 * theta)
    width = math.sqrt(U * math.tan(theta) ** 2 + V * math.tan(theta) + W)
    grid = centre + width * np.array([-1.4, -0.8, -0.31, 0, 0.27, 0.75, 1.3])
    # Na scattering length: the committed FullProf-compatible Sears table, in fm.
    area = 6 * 3.63**2 * 0.01 / (math.sin(theta) * math.sin(2 * theta))
    return centre, width, grid, area


def shape(delta, width, eta):
    gaussian = (
        math.sqrt(4 * math.log(2) / math.pi)
        / width
        * np.exp(-4 * math.log(2) * (delta / width) ** 2)
    )
    lorentzian = 2 / (math.pi * width) / (1 + 4 * (delta / width) ** 2)
    return (1 - eta) * gaussian + eta * lorentzian


def write_project(root, token, wavelength=1.54, extra=''):
    root = Path(root)
    (root / 'structures').mkdir(parents=True)
    (root / 'experiments').mkdir()
    (root / 'structures/phase.edi').write_text(
        """data_phase
_edi.schema_version 3
_cell.length_a 4
_cell.length_b 4
_cell.length_c 4
_cell.angle_alpha 90
_cell.angle_beta 90
_cell.angle_gamma 90
_space_group.name_h_m "P m -3 m"
loop_
_atom_site.id
_atom_site.type_symbol
_atom_site.wyckoff_letter
_atom_site.adp_type
_atom_site.fract_x
_atom_site.fract_y
_atom_site.fract_z
_atom_site.occupancy
_atom_site.adp_iso
Na Na a Biso 0 0 0 1 0
"""
    )
    _, _, grid, _ = geometry(wavelength)
    if token in RETIRED or token.startswith('cwl-tch-'):
        extra = '_peak.broad_lorentz_x 0\n_peak.broad_lorentz_y 0\n' + extra
    if token.endswith('-fcj') or token == RETIRED[0]:
        extra += '_peak.asym_fcj_1 .08\n_peak.asym_fcj_2 .08\n'
    text = (
        'data_bank\n_edi.schema_version 3\n'
        '_experiment_type.beam_mode "constant wavelength"\n'
        '_scattering_source.neutron_scattering_length sears1992\n'
        f'_peak.type {token}\n_peak.broad_gauss_u {U}\n'
        f'_peak.broad_gauss_v {V}\n_peak.broad_gauss_w {W}\n'
        '_peak.cutoff_fwhm 8\n'
        f'_instrument.setup_wavelength {wavelength}\n'
        '_instrument.calib_twotheta_offset 0\n'
        + extra
        + '\nloop_\n_linked_structure.structure_id\n_linked_structure.scale\nphase 1\n'
        'loop_\n_data.two_theta\n_data.intensity_meas\n_data.intensity_meas_su\n'
    )
    text += ''.join(f'{x:.17g} 0 1\n' for x in grid)
    (root / 'experiments/bank.edi').write_text(text)
    return root


def mixing_parameters(peak):
    intercepts = ('mixing_eta', 'mixing_eta_0', 'eta', 'eta_0')
    slopes = ('mixing_x', 'mixing_eta_1', 'eta_x', 'eta_slope')
    intercept = next((getattr(peak, name) for name in intercepts if hasattr(peak, name)), None)
    slope = next((getattr(peak, name) for name in slopes if hasattr(peak, name)), None)
    assert intercept is not None, 'Plain pseudo-Voigt must expose a dictionary eta intercept'
    assert slope is not None, 'Plain pseudo-Voigt must expose a dictionary eta slope'
    return intercept, slope


def retired_hits(paths):
    pattern = re.compile('|'.join(re.escape(token) + r'(?![a-z-])' for token in RETIRED))
    return [
        str(path)
        for path in paths
        if path.is_file() and pattern.search(path.read_bytes().decode('utf-8', errors='ignore'))
    ]


def migration_hits(paths, root):
    fixture = root / 'tests/fixtures/cwl_family'
    hashes = json.loads((fixture / 'rename-input-sha256.json').read_text())
    historical = fixture / 'rename_inputs/fcj/experiments/bank.edi'
    return retired_hits([
        path
        for path in paths
        if not (
            path == historical
            and path.is_file()
            and not path.is_symlink()
            and hashlib.sha256(path.read_bytes()).hexdigest() == hashes['fcj/experiments/bank.edi']
        )
    ])
