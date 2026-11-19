"""Export the supported Edi PNC model for reconstruction in GSAS-II."""

import argparse
import json
import math
from pathlib import Path

import edi
import numpy as np

from tools.gsas_ii.bundle import FORMAT, require


def _fixed(value, field: str) -> float:
    require(not value.free, f'{field} must be fixed')
    return value.value


def _neutral(value) -> bool:
    return value is None or (value.value == 0 and not value.free)


def _phase(structure) -> tuple[dict, float]:
    require(
        structure.space_group.name_h_m == 'P n m a'
        and structure.space_group.coord_system_code in {'', 'abc', None}
        and not structure.space_group_symop_magn_operation
        and not structure.atom_site_moment
        and not structure.atom_site_aniso
        and not structure.scattering_lengths_fm,
        'Expected standard P n m a symmetry with isotropic nuclear sites',
    )
    cell = [
        _fixed(getattr(structure.cell, name), name)
        for name in (
            'length_a',
            'length_b',
            'length_c',
            'angle_alpha',
            'angle_beta',
            'angle_gamma',
        )
    ]
    require(min(cell[:3]) > 0 and cell[3:] == [90] * 3, 'Invalid orthorhombic cell')
    atoms = []
    for atom in structure.atom_sites:
        require(atom.type_symbol in {'Pb', 'S', 'O'}, f'Unsupported atom type {atom.type_symbol}')
        require(atom.adp_type in {'Uiso', 'Biso'}, f'Unsupported ADP type for {atom.id}')
        uiso = _fixed(atom.adp_iso, 'ADP')
        if atom.adp_type == 'Biso':
            uiso /= 8 * math.pi**2
        atoms.append([
            atom.id,
            atom.type_symbol,
            _fixed(atom.fract_x, 'fract_x'),
            _fixed(atom.fract_y, 'fract_y'),
            _fixed(atom.fract_z, 'fract_z'),
            _fixed(atom.occupancy, 'occupancy'),
            uiso,
        ])
    require(atoms, 'Expected at least one atom')
    return {
        'name': structure.name,
        'space_group': 'P n m a',
        'cell': cell,
        'atoms': atoms,
    }, math.prod(cell[:3])


def _settings(experiment, cell_volume: float) -> tuple[dict, dict]:
    peak = experiment.peak
    instrument = experiment.instrument
    require(
        peak.type == edi.PeakProfileTypeEnum.CWL_TCH_PSEUDO_VOIGT_FCJ
        and experiment.neutron_scattering_length == 'sears1992'
        and experiment.absorption.type == 'none'
        and not experiment.preferred_orientation
        and not experiment.excluded_regions
        and experiment.dataset_weight == 1
        and _neutral(instrument.calib_sample_displacement)
        and _neutral(instrument.calib_sample_transparency),
        'Expected the supported CW neutron model without absorption, displacement or exclusions',
    )
    require(len(experiment.linked_structures) == 1, 'Expected one linked structure')
    link = experiment.linked_structure
    require(link.enabled, 'Expected an enabled phase link')
    wavelength = _fixed(instrument.setup_wavelength, 'wavelength')
    a = _fixed(peak.asym_fcj_1, 'sample aperture')
    b = _fixed(peak.asym_fcj_2, 'detector aperture')
    require(wavelength > 0 and a == b and a + b >= 0.002, 'Expected equal fixed FCJ apertures')
    # The merged Edi widths do not identify the original GSAS-II components.
    size, microstrain = 1.0, 0.0
    values = {
        'Lam': [wavelength, False],
        'Zero': [instrument.calib_twotheta_offset.value, instrument.calib_twotheta_offset.free],
        'SH/L': [a + b, False],
        'X': [
            100 * peak.broad_lorentz_y.value - 1.8 * wavelength / (math.pi * size),
            peak.broad_lorentz_y.free,
        ],
        'Y': [100 * peak.broad_lorentz_x.value, peak.broad_lorentz_x.free],
    }
    for axis in 'UVW':
        entry = getattr(peak, f'broad_gauss_{axis.lower()}')
        values[axis] = [entry.value * 10_000 / (8 * math.log(2)), entry.free]
    return values, {
        'size_um': size,
        'microstrain_ppm': microstrain,
        'phase_scale': [1.0, False],
        'scale': [100 * cell_volume * link.scale.value, link.scale.free],
    }


def _measurement(experiment) -> tuple[list, dict]:
    require(isinstance(experiment.data, edi.PdCwlData), 'Expected measured CW powder data')
    x = np.asarray(experiment.data.two_theta)
    y = np.asarray(experiment.data.intensity_meas)
    sigma = np.asarray(experiment.data.intensity_meas_su)
    require(
        len(x) >= 2 and np.all(np.diff(x) > 0) and np.all(y > 0) and np.all(sigma > 0),
        'Expected ascending observations with positive intensities and uncertainties',
    )
    require(
        experiment.background_type == 'chebyshev'
        and experiment.background_x_min == x[0]
        and experiment.background_x_max == x[-1],
        'Expected a Chebyshev background normalized over the full measured range',
    )
    terms = sorted(experiment.background_terms, key=lambda term: term.order)
    require(1 <= len(terms) <= 24, 'Unsupported Chebyshev order')
    flags = {term.coef.free for term in terms}
    require(len(flags) == 1, 'GSAS-II needs one refine flag for the background coefficients')
    coefficients = [0.0] * (terms[-1].order + 1)
    for term in terms:
        coefficients[term.order] = term.coef.value
    rows = np.column_stack((x, y, 1 / sigma**2))
    return rows.tolist(), {'coefficients': coefficients, 'refine': flags.pop()}


def export_edi(source: Path, output: Path) -> None:
    """Write one saved PNC model and its measured observations as ASCII."""
    project = edi.Project.load(source)
    require(
        len(project.structures) == len(project.experiments) == 1
        and project.analysis.fitting_mode == 'single'
        and not project.analysis.aliases
        and not project.analysis.constraints,
        'Expected one structure and experiment without aliases, constraints or sequential fitting',
    )
    structure, experiment = next(iter(project.structures)), next(iter(project.experiments))
    phase, volume = _phase(structure)
    instrument, sample = _settings(experiment, volume)
    observations, background = _measurement(experiment)
    bundle = {
        'format': FORMAT,
        'source': {'filename': source.name},
        'phase': phase,
        'histogram': {
            'name': experiment.name,
            'type': 'PNC',
            'instrument': instrument,
            'sample': sample,
            'background': background,
            'observations': observations,
        },
    }
    payload = json.dumps(bundle, ensure_ascii=True, allow_nan=False, separators=(',', ':'))
    with output.open('x', encoding='ascii') as stream:
        stream.write(payload + '\n')


def main() -> None:
    """Write a GSAS-II reconstruction bundle from a saved Edi project."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source', type=Path, help='Saved Edi project')
    parser.add_argument('output', type=Path, help='New .gsas.json bundle')
    args = parser.parse_args()
    try:
        export_edi(args.source, args.output)
    except (KeyError, OSError, TypeError, ValueError, edi.IoError) as error:
        parser.exit(1, f'Edi export: {error}\n')


if __name__ == '__main__':
    main()
