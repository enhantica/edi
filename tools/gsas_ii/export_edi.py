"""Export the supported Edi powder models for reconstruction in GSAS-II."""

import argparse
import json
import math
from pathlib import Path

import edi
import numpy as np

from tools.gsas_ii.bundle import FORMAT, POWDER_FORMAT, require


def _fixed(value, field: str) -> float:
    require(not value.free, f'{field} must be fixed')
    return value.value


def _phase(structure) -> tuple[dict, float]:
    require(
        not structure.scattering_lengths_fm,
        'Custom neutron lengths are not supported',
    )
    cell_parameters = [
        getattr(structure.cell, name)
        for name in (
            'length_a',
            'length_b',
            'length_c',
            'angle_alpha',
            'angle_beta',
            'angle_gamma',
        )
    ]
    cell = [parameter.value for parameter in cell_parameters]
    require(min(cell[:3]) > 0 and all(0 < angle < 180 for angle in cell[3:]), 'Invalid cell')
    ca, cb, cg = (math.cos(math.radians(angle)) for angle in cell[3:])
    determinant = 1 - ca**2 - cb**2 - cg**2 + 2 * ca * cb * cg
    require(determinant > 0, 'Invalid unit-cell metric')
    atom_flags = []
    atoms = []
    for atom in structure.atom_sites:
        require(
            atom.adp_type in {'Uiso', 'Biso', 'Uani', 'Bani'},
            f'Unsupported ADP type for {atom.id}',
        )
        uiso = atom.adp_iso.value
        flags = 'X' if any(getattr(atom, f'fract_{axis}').free for axis in 'xyz') else ''
        flags += 'U' if atom.adp_iso.free else ''
        flags += 'F' if atom.occupancy.free else ''
        if atom.adp_type == 'Biso':
            uiso /= 8 * math.pi**2
        row = [
            atom.id,
            atom.type_symbol,
            atom.fract_x.value,
            atom.fract_y.value,
            atom.fract_z.value,
            atom.occupancy.value,
            uiso,
        ]
        if atom.adp_type in {'Uani', 'Bani'}:
            tensor = structure.atom_site_aniso[atom.id]
            components = [
                getattr(tensor, f'adp_{key}') for key in ('11', '22', '33', '12', '13', '23')
            ]
            flags += 'U' if any(component.free for component in components) else ''
            factor = 1 / (8 * math.pi**2) if atom.adp_type == 'Bani' else 1
            row.extend(component.value * factor for component in components)
        atoms.append(row)
        atom_flags.append(flags)
    require(atoms, 'Expected at least one atom')
    phase = {
        'name': structure.name,
        'space_group': structure.space_group.name_h_m,
        'cell_refine': any(parameter.free for parameter in cell_parameters),
        'atom_flags': atom_flags,
        'cell': cell,
        'atoms': atoms,
    }
    if structure.atom_site_moment:
        phase['magnetic'] = _magnetic(structure)
    return phase, math.prod(cell[:3]) * math.sqrt(determinant)


def _magnetic(structure) -> dict:
    centerings = [xyz for _, xyz in structure.space_group_symop_magn_centering]
    require(set(centerings) <= {'x,y,z,+1'}, 'Expected directly enumerated magnetic symmetry')
    factors = {factor.id: factor for factor in structure.magnetic_form_factor}
    moments = []
    for moment in structure.atom_site_moment:
        symbol = structure.atom_sites[moment.id].type_symbol
        factor = factors.get(symbol)
        require(factor is None or factor.approximation == 'j0', 'GSAS-II needs a j0 form factor')
        ion = symbol if factor is None else factor.ion or symbol
        axes = [getattr(moment, f'crystalaxis_{axis}') for axis in 'xyz']
        moments.append([
            moment.id,
            ion,
            *(axis.value for axis in axes),
            [axis.free for axis in axes],
        ])
    return {
        'group': structure.space_group_magn['name_bns'],
        'operations': [xyz for _, xyz in structure.space_group_symop_magn_operation],
        'moments': moments,
    }


def _cw_settings(experiment, *, coupled_apertures: bool) -> tuple[dict, dict]:
    peak = experiment.peak
    instrument = experiment.instrument
    require(
        peak.type == edi.PeakProfileTypeEnum.CWL_TCH_PSEUDO_VOIGT_FCJ,
        'Expected the CW TCH profile with axial asymmetry',
    )
    wavelength = _fixed(instrument.setup_wavelength, 'wavelength')
    a = peak.asym_fcj_1.value
    b = _fixed(peak.asym_fcj_2, 'detector aperture')
    require(
        wavelength > 0
        and a == b
        and a + b >= 0.002
        and (not peak.asym_fcj_1.free or coupled_apertures),
        'Expected equal FCJ apertures with a single shared refine flag',
    )
    # The merged Edi widths do not identify the original GSAS-II components.
    size, microstrain = 1.0, 0.0
    values = {
        'Lam': [wavelength, False],
        'Zero': [instrument.calib_twotheta_offset.value, instrument.calib_twotheta_offset.free],
        'SH/L': [a + b, peak.asym_fcj_1.free],
        'X': [
            100 * peak.broad_lorentz_y.value - 1.8 * wavelength / (math.pi * size),
            peak.broad_lorentz_y.free,
        ],
        'Y': [100 * peak.broad_lorentz_x.value, peak.broad_lorentz_x.free],
    }
    for axis in 'UVW':
        entry = getattr(peak, f'broad_gauss_{axis.lower()}')
        values[axis] = [entry.value * 10_000 / (8 * math.log(2)), entry.free]
    radius = 200.0
    microns = -(math.pi * radius / 0.18)
    displacements = {}
    for key, parameter in zip(
        ('displace_x', 'displace_y'),
        (instrument.calib_sample_displacement, instrument.calib_sample_transparency),
        strict=True,
    ):
        displacements[key] = (
            [0.0, False] if parameter is None else [microns * parameter.value, parameter.free]
        )
    if _mode(experiment) == 'PXC':
        coefficient = instrument.setup_polarization_coefficient
        takeoff = _fixed(instrument.setup_monochromator_twotheta, 'monochromator angle')
        require(takeoff == 0, 'Cannot represent a nonzero monochromator angle in GSAS-II')
        values['polarization'] = [1 - coefficient.value, coefficient.free]
        values['azimuth'] = [0.0, False]
        if instrument.setup_wavelength_2_to_1_ratio is not None:
            ratio = instrument.setup_wavelength_2_to_1_ratio
            values['ratio'] = [ratio.value, ratio.free]
            values['Lam2'] = [_fixed(instrument.setup_wavelength_2, 'second wavelength'), False]
    return values, {
        'radius_mm': radius,
        **displacements,
        'size_um': size,
        'microstrain_ppm': microstrain,
    }


def _mode(experiment) -> str:
    require(
        experiment.experiment_type.sample_form == edi.SampleFormEnum.POWDER,
        'Expected a powder experiment',
    )
    if experiment.experiment_type.beam_mode == edi.BeamModeEnum.TIME_OF_FLIGHT:
        return 'PNT'
    return (
        'PXC'
        if experiment.experiment_type.radiation_probe == edi.RadiationProbeEnum.XRAY
        else 'PNC'
    )


def _tof_settings(experiment) -> tuple[dict, dict]:
    instrument = experiment.instrument
    peak = experiment.peak
    require(
        peak.type == edi.PeakProfileTypeEnum.TOF_JORGENSEN_VON_DREELE,
        'Expected the Jorgensen-Von Dreele TOF profile',
    )
    for parameter in (
        instrument.calib_d_to_tof_reciprocal,
        peak.rise_alpha_0,
        peak.broad_gauss_size,
        peak.broad_gauss_strain,
    ):
        require(_fixed(parameter, 'TOF profile term') == 0, 'Unexpected active TOF profile term')
    linear = instrument.calib_d_to_tof_linear.value
    values = {
        key: [p.value, p.free]
        for key, p in {
            'Zero': instrument.calib_d_to_tof_offset,
            'difC': instrument.calib_d_to_tof_linear,
            'difA': instrument.calib_d_to_tof_quadratic,
            '2-theta': instrument.setup_twotheta_bank,
            'alpha': peak.rise_alpha_1,
            'beta-0': peak.decay_beta_0,
            'beta-1': peak.decay_beta_1,
            'sig-0': peak.broad_gauss_sigma_0,
            'sig-1': peak.broad_gauss_sigma_1,
            'sig-2': peak.broad_gauss_sigma_2,
            'Z': peak.broad_lorentz_gamma_0,
            'X': peak.broad_lorentz_gamma_1,
            'Y': peak.broad_lorentz_gamma_2,
        }.items()
    }
    # Keep automatic TOF size and strain terms zero in strain and canonical in size.
    # Their d and d² bases are already shared with the instrument coefficients.
    size = _fixed(peak.broad_lorentz_size, 'Lorentzian size')
    strain = _fixed(peak.broad_lorentz_strain, 'Lorentzian strain')
    values['X'][0] += strain
    values['Y'][0] += size - 1e-4 * linear
    return values, {'size_um': 1.0, 'microstrain_ppm': 0.0}


def _histogram(experiment, indices: dict, volumes: list, coupled: set) -> dict:
    mode = _mode(experiment)
    require(
        (mode == 'PXC' or experiment.neutron_scattering_length == 'sears1992')
        and experiment.absorption.type == 'none'
        and not experiment.preferred_orientation
        and experiment.dataset_weight == 1,
        'Expected the supported powder model without absorption and texture',
    )
    instrument, settings = (
        _tof_settings(experiment)
        if mode == 'PNT'
        else _cw_settings(experiment, coupled_apertures=experiment.name in coupled)
    )
    sample = {
        key: value
        for key, value in settings.items()
        if key in {'radius_mm', 'displace_x', 'displace_y'}
    }
    sample['scale'] = [1.0, False]
    links = []
    for link in experiment.linked_structures:
        if not link.enabled:
            continue
        index = indices[link.structure_id]
        scale = (1 if mode == 'PNT' else 100) * volumes[index] * link.scale.value
        links.append({
            'phase_index': index,
            'phase_scale': [scale, link.scale.free],
            'size_um': settings['size_um'],
            'microstrain_ppm': settings['microstrain_ppm'],
        })
    observations, background, limits = _measurement(experiment)
    return {
        'name': experiment.name,
        'type': mode,
        'instrument': instrument,
        'sample': sample,
        'links': links,
        'background': background,
        'observations': observations,
        'fit_limits': limits,
    }


def _measurement(experiment) -> tuple[list, dict, list]:
    data = experiment.data
    require(isinstance(data, (edi.PdCwlData, edi.PdTofData)), 'Expected measured powder data')
    x = np.asarray(data.two_theta if isinstance(data, edi.PdCwlData) else data.time_of_flight)
    y = np.asarray(experiment.data.intensity_meas)
    sigma = np.asarray(experiment.data.intensity_meas_su)
    require(
        len(x) >= 2 and np.all(np.diff(x) > 0) and np.isfinite(y).all() and np.all(sigma > 0),
        'Expected ascending observations with finite intensities and positive uncertainties',
    )
    low, high = experiment.background_x_min, experiment.background_x_max
    require(
        experiment.background_type == 'chebyshev'
        and low is not None
        and high is not None
        and x[0] <= low < high <= x[-1],
        'Expected a Chebyshev background normalized over the active measured range',
    )
    limits = [[low, high]]
    weights = 1 / sigma**2
    masked = np.zeros(len(x), dtype=bool)
    for identifier, (start, end) in zip(
        experiment.excluded_region_ids, experiment.excluded_regions, strict=True
    ):
        if identifier.startswith('gsas-zero-weight-'):
            weights[(x >= start) & (x <= end)] = 0
        elif identifier.startswith('gsas-mask-'):
            masked |= (x >= start) & (x <= end)
        elif not ((start == x[0] and end < low) or (end == x[-1] and start > high)):
            limits.append([start, end])
    terms = sorted(experiment.background_terms, key=lambda term: term.order)
    require(1 <= len(terms) <= 24, 'Unsupported Chebyshev order')
    flags = {term.coef.free for term in terms}
    require(len(flags) == 1, 'GSAS-II needs one refine flag for the background coefficients')
    coefficients = [0.0] * (terms[-1].order + 1)
    for term in terms:
        coefficients[term.order] = term.coef.value
    rows = np.column_stack((x, y, weights))
    observed = rows.tolist()
    if masked.any():
        observed = [row + [bool(mask)] for row, mask in zip(observed, masked, strict=True)]
    return observed, {'coefficients': coefficients, 'refine': flags.pop()}, limits


def _constraints(analysis, indices: dict) -> tuple[list, set]:
    aliases = {alias.id: alias.parameter_unique_name for alias in analysis.aliases}
    groups = {}
    used = set()
    for constraint in analysis.constraints:
        text = constraint.expression.split('=')
        require(constraint.enabled and len(text) == 2, 'Expected an enabled ADP equality')
        dependent, leader = map(str.strip, text)
        require(dependent in aliases and leader in aliases, 'Expected an ADP alias equality')
        require(dependent not in used, 'Repeated ADP tie dependent')
        used.add(dependent)
        groups.setdefault(leader, []).append(dependent)
    require(not used.intersection(groups), 'Chained ADP ties cannot be exported')
    require(set(aliases) == used.union(groups), 'Unused aliases cannot be exported to GPX')
    ties = []
    coupled = set()
    for leader, members in groups.items():
        bank = aliases[leader].removesuffix('.peak.asym_fcj_1')
        if (
            bank != aliases[leader]
            and len(members) == 1
            and aliases[members[0]] == bank + '.peak.asym_fcj_2'
        ):
            coupled.add(bank)
            continue
        targets = []
        for alias in [leader, *members]:
            structure, separator, parameter = aliases[alias].partition('.atom_site.')
            atom, _, field = parameter.rpartition('.')
            require(
                separator and field == 'adp_iso' and structure in indices and atom,
                'Only equalities between isotropic ADPs can be exported',
            )
            targets.append([indices[structure], atom])
        ties.append(targets)
    return ties, coupled


def export_edi(source: Path, output: Path) -> None:
    """Write the phases and powder histograms from a saved Edi project as ASCII."""
    p = edi.Project.load(source)
    require(
        p.structures and p.experiments and p.analysis.fitting_mode in {'single', 'joint'},
        'Expected a single or joint fit',
    )
    phases, volumes = zip(*(_phase(structure) for structure in p.structures), strict=True)
    indices = {phase['name']: index for index, phase in enumerate(phases)}
    ties, coupled = _constraints(p.analysis, indices)
    histograms = [
        _histogram(experiment, indices, volumes, coupled) for experiment in p.experiments
    ]
    if (
        len(phases) == len(histograms) == 1
        and histograms[0]['type'] == 'PNC'
        and histograms[0]['links']
        and not ties
        and 'magnetic' not in phases[0]
    ):
        histogram = histograms[0]
        link = histogram.pop('links')[0]
        sample = histogram['sample']
        sample.update(
            size_um=link['size_um'],
            microstrain_ppm=link['microstrain_ppm'],
            phase_scale=[1.0, False],
            scale=link['phase_scale'],
        )
        bundle = {
            'format': FORMAT,
            'source': {'filename': source.name},
            'phase': phases[0],
            'histogram': histogram,
        }
    else:
        bundle = {
            'format': POWDER_FORMAT,
            'source': {'filename': source.name},
            'phases': phases,
            'histograms': histograms,
            'adp_ties': ties,
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
