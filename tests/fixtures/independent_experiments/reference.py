"""One-atom Sears Ni inputs and independent weighted normal equations.

The 10.3 fm Ni length and the Biso convention are also frozen by the external
single-crystal corpus. Here |F|² = (1.03 * occupancy)² exp(-2 B s²), in
(10^-12 cm)². No fitted or calculated engine output supplies these observations.
"""

import math
from pathlib import Path

CELL = (5.1, 6.2, 7.3)
BANKS = {
    'amber': {
        'phase': 'phase_z',
        'occupancy': 0.79,
        'scale': 0.8,
        'sigma': 0.003,
        'noise': 0.3,
        'n': 5,
    },
    'copper': {
        'phase': 'phase_m',
        'occupancy': 0.57,
        'scale': 1.6,
        'sigma': 0.009,
        'noise': 1.2,
        'n': 7,
    },
    'violet': {
        'phase': 'phase_a',
        'occupancy': 0.38,
        'scale': 2.4,
        'sigma': 0.015,
        'noise': 2.4,
        'n': 9,
    },
}
MARKERS = {'phase_z': 0.13, 'phase_m': 0.23, 'phase_a': 0.37, 'shared': 0.41}
START = 0.47
NOISE = (-0.7, 1.1, -0.4, 0.8, -1.2, 0.3, -0.2, 1.5, -1.0)


def observations(name):
    bank = BANKS[name]
    rows = []
    for i in range(bank['n']):
        hkl = (i + 1, i % 2 + 1, (i * 2) % 3 + 1)
        s2 = sum((h / a) ** 2 for h, a in zip(hkl, CELL, strict=True)) / 4
        basis = bank['scale'] * 1.03**2 * math.exp(-2 * 0.41 * s2)
        sigma = bank['sigma'] * (1 + 0.5 * (i % 3))
        measured = basis * bank['occupancy'] ** 2 + sigma * bank['noise'] * NOISE[i]
        rows.append((hkl, basis, measured, sigma))
    return rows


def optimum(names):
    rows = [row for name in names for row in observations(name)]
    gram = sum((basis / su) ** 2 for _hkl, basis, _y, su in rows)
    q = sum(basis * y / su**2 for _hkl, basis, y, su in rows) / gram
    occupancy = math.sqrt(q)
    chi = sum(((y - basis * q) / su) ** 2 for _hkl, basis, y, su in rows)
    reduced = chi / (len(rows) - 1)
    uncertainty = math.sqrt(reduced / (4 * q * gram))
    norm = sum((y / su) ** 2 for _hkl, _basis, y, su in rows)
    return {
        'value': occupancy,
        'su': uncertainty,
        'chi': chi,
        'reduced': reduced,
        'rwp': math.sqrt(chi / norm),
        'n': len(rows),
        'gram': gram,
    }


def structure_text(name):
    text = f'data_{name}\n_edi.schema_version 3\n_space_group.name_h_m "P 1"\n'
    text += ''.join(f'_cell.length_{axis} {v}\n' for axis, v in zip('abc', CELL, strict=True))
    return (
        text
        + """_cell.angle_alpha 90
_cell.angle_beta 90
_cell.angle_gamma 90
loop_
_atom_site.id
_atom_site.type_symbol
_atom_site.wyckoff_letter
_atom_site.fract_x
_atom_site.fract_y
_atom_site.fract_z
_atom_site.occupancy
_atom_site.adp_type
_atom_site.adp_iso
Ni Ni a MARKER .27 .39 .47() Biso .41
"""
    ).replace('MARKER', str(MARKERS.get(name, 0.13)))


def project_files(destination, *, mode='independent', selected=None, shared=False):
    destination = Path(destination)
    for folder in ('structures', 'experiments', 'analysis'):
        (destination / folder).mkdir(parents=True, exist_ok=True)
    names = [selected] if selected else list(BANKS)
    phases = {'shared'} if shared else {BANKS[name]['phase'] for name in names}
    for phase in phases:
        (destination / 'structures' / (phase + '.edi')).write_text(structure_text(phase))
    for name in names:
        bank = BANKS[name]
        phase = 'shared' if shared else bank['phase']
        text = f"""data_{name}
_edi.schema_version 3
_experiment_type.sample_form "single crystal"
_experiment_type.radiation_probe neutron
_experiment_type.scattering_type bragg
_experiment_type.beam_mode "constant wavelength"
_scattering_source.neutron_scattering_length sears1992
_instrument.setup_wavelength .8
_extinction.type none
loop_
_linked_structure.structure_id
_linked_structure.scale
{phase} {bank['scale']}
loop_
_refln.index_h
_refln.index_k
_refln.index_l
_refln.intensity_meas
_refln.intensity_meas_su
"""
        text += ''.join(
            ' '.join(map(str, [*hkl, y, su])) + '\n' for hkl, _basis, y, su in observations(name)
        )
        (destination / 'experiments' / (name + '.edi')).write_text(text)
    (destination / 'analysis/analysis.edi').write_text(
        f'_edi.schema_version 3\n_fitting_mode.type {mode}\n'
        '_minimizer.max_iterations 100\n_minimizer.chi_square_tolerance 1e-12\n'
    )
    (destination / 'project.edi').write_text(
        '_edi.schema_version 3\n_metadata.name "Independent crystals"\n'
    )
    return destination


def scan_files(destination, mode='independent'):
    destination = Path(destination)
    for folder in ('structures', 'experiments/scan', 'analysis'):
        (destination / folder).mkdir(parents=True, exist_ok=True)
    (destination / 'structures/phase.edi').write_text(
        structure_text('phase').replace('.47()', '.47')
    )
    x = [40 + 4 * i for i in range(7)]
    records = {}
    for i, target in enumerate((3.2, 9.1, 5.5)):
        measured = [target + 0.13 * NOISE[j] for j in range(len(x))]
        sigma = [0.2 + 0.1 * (j % 3) for j in range(len(x))]
        rows = ''.join(f'{a} {b} {c}\n' for a, b, c in zip(x, measured, sigma, strict=True))
        (destination / 'experiments/scan' / f'{i}.xy').write_text(rows)
        weights = [1 / su**2 for su in sigma]
        mean = sum(w * y for w, y in zip(weights, measured, strict=True)) / sum(weights)
        chi = sum(((y - mean) / su) ** 2 for y, su in zip(measured, sigma, strict=True))
        records[f'{i}.xy'] = {
            'value': mean,
            'su': math.sqrt(chi / (len(x) - 1) / sum(weights)),
            'reduced': chi / (len(x) - 1),
        }
    text = """data_bank
_edi.schema_version 3
_experiment_type.sample_form powder
_experiment_type.radiation_probe neutron
_experiment_type.scattering_type bragg
_experiment_type.beam_mode "constant wavelength"
_peak.type cwl-tch-pseudo-voigt
_peak.broad_gauss_u 0
_peak.broad_gauss_v 0
_peak.broad_gauss_w .15
_peak.broad_lorentz_x 0
_peak.broad_lorentz_y 0
_peak.cutoff_fwhm 5
_instrument.setup_wavelength 1.54
_instrument.calib_twotheta_offset 0
loop_
_linked_structure.structure_id
_linked_structure.scale
phase 0
_background.type polynomial
_background.origin 40
loop_
_background.id
_background.order
_background.coef
base 0 4()
loop_
_data.two_theta
_data.intensity_meas
_data.intensity_meas_su
"""
    text += (destination / 'experiments/scan/0.xy').read_text()
    (destination / 'experiments/bank.edi').write_text(text)
    (destination / 'analysis/analysis.edi').write_text(
        f'_edi.schema_version 3\n_fitting_mode.type {mode}\n'
        '_minimizer.max_iterations 100\n_minimizer.chi_square_tolerance 1e-12\n'
        '_sequential_fit.data_dir experiments/scan\n_sequential_fit.file_pattern *.xy\n'
    )
    (destination / 'project.edi').write_text(
        '_edi.schema_version 3\n_metadata.name "Scan control"\n'
    )
    return destination, records


if __name__ == '__main__':
    project_files(Path(__file__).parent / 'project')
