"""One P1 Friedel orbit: Bragg centers and integrated-share identities."""

import math

import numpy as np

WAVELENGTHS = (1.54056, 1.5444)
CASES = (
    'second-only',
    'first-only',
    'both-centred',
    'both-unequal',
    'inactive-ratio',
    'inactive-wavelength',
    'outside-tail',
    'unreachable-equal',
    'unreachable-beyond',
    'shifted-centre',
)
BOUNDARY_CASES = ('unreachable-equal', 'unreachable-beyond', 'shifted-centre')


def centers(reverse):
    wavelengths = WAVELENGTHS[::-1] if reverse else WAVELENGTHS
    return wavelengths, tuple(2 * math.degrees(math.asin(value / 4)) for value in wavelengths)


def shifted_boundary(case, reverse):
    d_spacing = 0.7722
    second = (
        2 * d_spacing * math.sin(math.radians(179.995 / 2))
        if case == 'shifted-centre'
        else WAVELENGTHS[1]
        if case == 'unreachable-equal'
        else WAVELENGTHS[1] * 1.001
    )
    wavelengths = (WAVELENGTHS[0], second)
    if reverse:
        wavelengths = wavelengths[::-1]
    positions = []
    for wavelength in wavelengths:
        sine = wavelength / (2 * d_spacing)
        if sine >= 1:
            positions.append(None)
        else:
            bragg = 2 * math.degrees(math.asin(sine))
            positions.append(bragg + math.cos(math.radians(bragg)))
    grid = np.linspace(178.99, 179.01, 21)
    eligible = any(
        position is not None and grid[0] <= position <= grid[-1] for position in positions
    )
    return wavelengths, tuple(positions), grid, eligible


def geometry(case, reverse):
    if case in BOUNDARY_CASES:
        return shifted_boundary(case, reverse)
    wavelengths, positions = centers(reverse)
    if case == 'second-only':
        lo, hi = (45.24, 45.35) if reverse else (45.36, 45.50)
    elif case == 'first-only':
        lo, hi = (45.36, 45.50) if reverse else (45.24, 45.35)
    elif case in {'outside-tail', 'inactive-ratio', 'inactive-wavelength'}:
        lo, hi = (45.445, 45.46) if reverse else (45.265, 45.28)
    else:
        lo, hi = 45.24, 45.50
    grid = np.linspace(lo, hi, round((hi - lo) / 0.001) + 1)
    active = case not in {'inactive-ratio', 'inactive-wavelength'}
    eligible = lo <= positions[0] <= hi or (active and lo <= positions[1] <= hi)
    return wavelengths, positions, grid, eligible


def component_weights(grid, positions):
    result = []
    for index, position in enumerate(positions):
        theta = math.radians(position / 2)
        delta = np.abs(grid - position)
        extent = 0.05
        taper = np.where(
            delta <= 0.8 * extent,
            1,
            np.where(
                delta >= extent,
                0,
                0.5 * (1 + np.cos(math.pi * (delta - 0.8 * extent) / (0.2 * extent))),
            ),
        )
        gaussian = np.exp(-4 * math.log(2) * (delta / 0.01) ** 2) * taper
        result.append(
            (1 if index == 0 else 0.5) * gaussian / (math.sin(theta) * math.sin(2 * theta))
        )
    return result


def rows(grid, intensity, sigma):
    return ''.join(
        f'{x:.17g} {y:.17g} {s:.17g}\n' for x, y, s in zip(grid, intensity, sigma, strict=True)
    )


def write(root, case, reverse, mode):
    wavelengths, positions, grid, eligible = geometry(case, reverse)
    for directory in ('structures', 'experiments', 'analysis'):
        (root / directory).mkdir(parents=True, exist_ok=True)
    (root / 'project.edi').write_text('_edi.schema_version 3\n_metadata.name doublet\n')
    (root / 'structures/phase.edi').write_text("""data_phase
_edi.schema_version 3
_cell.length_a 2
_cell.length_b 0.5
_cell.length_c 0.5
_cell.angle_alpha 90
_cell.angle_beta 90
_cell.angle_gamma 90
_space_group.name_h_m "P 1"
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
X La a Biso 0() 0 0 1 0
""")
    if case in BOUNDARY_CASES:
        structure = root / 'structures/phase.edi'
        structure.write_text(
            structure
            .read_text()
            .replace('_cell.length_a 2', '_cell.length_a 0.7722')
            .replace('_cell.length_b 0.5', '_cell.length_b 0.2')
            .replace('_cell.length_c 0.5', '_cell.length_c 0.2')
        )
    ratio = 0 if case in {'inactive-ratio', 'inactive-wavelength'} else 0.5
    header = f"""data_bank
_edi.schema_version 3
_experiment_type.sample_form powder
_experiment_type.radiation_probe xray
_experiment_type.scattering_type bragg
_experiment_type.beam_mode "constant wavelength"
_scattering_source.xray_form_factor it1992
_scattering_source.xray_dispersion none
_peak.type cwl-tch-pseudo-voigt
_peak.broad_gauss_u 0
_peak.broad_gauss_v 0
_peak.broad_gauss_w 0.0001
_peak.broad_lorentz_x 0
_peak.broad_lorentz_y 0
_peak.cutoff_fwhm 5
_instrument.calib_twotheta_offset 0
_instrument.setup_wavelength {wavelengths[0]}
_instrument.setup_wavelength_2 {0 if case == 'inactive-wavelength' else wavelengths[1]}
_instrument.setup_wavelength_2_to_1_ratio {ratio}
loop_
_linked_structure.structure_id
_linked_structure.scale
phase 1
_background.type polynomial
_background.origin 45
loop_
_background.id
_background.order
_background.coef
1 0 0
loop_
_data.two_theta
_data.intensity_meas
_data.intensity_meas_su
"""
    if case in BOUNDARY_CASES:
        header = header.replace('_peak.broad_gauss_w 0.0001', '_peak.broad_gauss_w 16')
        header = header.replace(
            '_instrument.calib_twotheta_offset 0',
            '_instrument.calib_twotheta_offset 0\n_instrument.calib_sample_displacement 1',
        )
    banks = ('bank', 'other') if mode == 'joint' else ('bank',)
    for bank in banks:
        (root / f'experiments/{bank}.edi').write_text(
            header.replace('data_bank', f'data_{bank}')
            + rows(grid, np.ones_like(grid), np.ones_like(grid))
        )
    analysis = f'_edi.schema_version 3\n_fitting_mode.type {mode}\n_minimizer.max_iterations 1\n'
    if mode == 'joint':
        analysis += 'loop_\n_joint_fit.experiment_id\n_joint_fit.weight\nbank 1\nother 1\n'
    elif mode in {'sequential', 'independent'}:
        analysis += (
            '_sequential_fit.data_dir experiments/scan\n_sequential_fit.file_pattern *.dat\n'
            '_sequential_fit.template_file 1.dat\n'
        )
    if mode in {'sequential', 'independent'}:
        scan = root / 'experiments/scan'
        scan.mkdir()
        for index in range(3):
            (scan / f'{index}.dat').write_text(
                'XYDATA\n' + rows(grid, np.ones_like(grid), np.ones_like(grid))
            )
    (root / 'analysis/analysis.edi').write_text(analysis)
    return grid, positions, eligible
