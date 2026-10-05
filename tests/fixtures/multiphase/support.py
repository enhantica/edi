"""Authored phases and independent linearity/Bragg-law controls."""

import math
from pathlib import Path

import numpy as np

LENGTHS = {'alpha': (2.2, 3.1, 4.3), 'beta': (3.3, 4.6, 5.7)}
SCALES = {'alpha': 2.75, 'beta': 0.375}


def grid():
    return np.asarray(
        sorted(
            2 * math.degrees(math.asin(1.54 / (2 * a)))
            for lengths in LENGTHS.values()
            for a in lengths
        )
    )


def write_project(
    root, phases=('alpha', 'beta'), scales=None, texture=None, biso=0.8, measured=None
):
    root = Path(root)
    scales = SCALES if scales is None else scales
    (root / 'structures').mkdir(parents=True)
    (root / 'experiments').mkdir()
    for name in phases:
        a, b, c = LENGTHS[name]
        text = f"""data_{name}
_edi.schema_version 3
_cell.length_a {a}
_cell.length_b {b}
_cell.length_c {c}
_cell.angle_alpha 90
_cell.angle_beta 90
_cell.angle_gamma 90
_space_group.name_h_m "P 1"
loop_
_atom_site.id
_atom_site.wyckoff_letter
_atom_site.type_symbol
_atom_site.adp_type
_atom_site.fract_x
_atom_site.fract_y
_atom_site.fract_z
_atom_site.occupancy
_atom_site.adp_iso
X a Gd Biso 0 0 0 0.7 {biso}
"""
        (root / 'structures' / f'{name}.edi').write_text(text)
    text = """data_pattern
_edi.schema_version 3
_experiment_type.sample_form powder
_experiment_type.radiation_probe neutron
_experiment_type.scattering_type bragg
_experiment_type.beam_mode "constant wavelength"
_scattering_source.neutron_scattering_length sears1992
_peak.type cwl-pseudo-voigt
_peak.broad_gauss_u 0
_peak.broad_gauss_v 0
_peak.broad_gauss_w 0.01
_peak.broad_lorentz_x 0
_peak.broad_lorentz_y 0
_peak.cutoff_fwhm 5
_instrument.calib_twotheta_offset 0
_instrument.setup_wavelength 1.54
loop_
_linked_structure.structure_id
_linked_structure.scale
"""
    text += ''.join(f'{name} {scales[name]}\n' for name in phases)
    if texture:
        text += '\nloop_\n' + ''.join(
            f'_preferred_orientation.{k}\n'
            for k in (
                'structure_id',
                'march_r',
                'march_random_fract',
                'index_h',
                'index_k',
                'index_l',
            )
        )
        for name, (ratio, fraction, axis) in texture.items():
            text += f'{name} {ratio} {fraction} {" ".join(map(str, axis))}\n'
    values = np.zeros(len(grid())) if measured is None else measured
    text += '\nloop_\n_data.two_theta\n_data.intensity_meas\n_data.intensity_meas_su\n'
    text += ''.join(f'{x:.17g} {y:.17g} 1\n' for x, y in zip(grid(), values, strict=True))
    (root / 'experiments/pattern.edi').write_text(text)
    (root / 'analysis').mkdir()
    (root / 'analysis/analysis.edi').write_text(
        '_edi.schema_version 3\n_minimizer.max_iterations 12\n'
        '_minimizer.chi_square_tolerance 1e-10\n'
    )
    return root


def links(experiment):
    rows = getattr(experiment, 'linked_structures', None)
    if rows is None:
        rows = experiment.linked_structure
    assert hasattr(rows, 'keys'), 'Linked phases must expose keyed rows, like experiments'
    return rows


def pattern(project):
    project.analysis.calculate()
    values = np.asarray(project.experiments[0].data.intensity_calc, dtype=np.float64).copy()
    assert values.shape == grid().shape, 'A phase sum must retain the declared grid'
    assert np.isfinite(values).all(), 'A phase sum must retain finite values'
    return values


def enable(row, *, value):
    for name, invert in (('enabled', False), ('is_enabled', False), ('disabled', True)):
        if hasattr(row, name):
            setattr(row, name, not value if invert else value)
            return
    message = 'A linked phase needs a persistent enable/disable flag'
    raise AssertionError(message)
