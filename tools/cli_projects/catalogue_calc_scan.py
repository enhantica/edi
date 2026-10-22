# SPDX-License-Identifier: BSD-3-Clause
"""The calculation-only cases (a model and an instrument, no data) and the Co2SiO4 scan."""

from __future__ import annotations

import shutil

from catalogue_common import (
    BISO,
    CLI,
    cell_lines,
    data_loop,
    flat_level,
    free,
    loop,
    project_record,
    read_points,
    structure,
    text,
)

PEAK_CW = [
    '_peak.type cwl-tch-pseudo-voigt',
    '_peak.broad_gauss_u 0.1',
    '_peak.broad_gauss_v -0.1',
    '_peak.broad_gauss_w 0.1',
    '_peak.broad_lorentz_x 0',
]


def calculation_analysis() -> str:
    return text(
        ['_edi.schema_version 3'], ['_fitting_mode.type single'], ['_minimizer.type crysta']
    )


def experiment_type(beam_mode: str, probe: str) -> list[str]:
    return [
        '_experiment_type.sample_form powder',
        f'_experiment_type.beam_mode "{beam_mode}"',
        f'_experiment_type.radiation_probe {probe}',
        '_experiment_type.scattering_type bragg',
    ]


def linked(structure_id: str, scale: float) -> list[str]:
    return loop(
        ['_linked_structure.structure_id', '_linked_structure.scale'], [[structure_id, scale]]
    )


def line_background(points: list[tuple[float, float]]) -> list[str]:
    return [
        '_background.type line-segment',
        '',
        *loop(
            ['_background.id', '_background.position', '_background.intensity'],
            [[i, x, y] for i, (x, y) in enumerate(points, 1)],
        ),
    ]


def pd_neut_cwl_lbco_simulation() -> dict[str, str]:
    # diffraction-lib's struct-lbco CIF on the HRPT instrument of the fitted case.
    sites = [
        'La La 0 0 0 a 0.5 0.5 Biso',
        'Ba Ba 0 0 0 a 0.5 0.5 Biso',
        'Co Co 0.5 0.5 0.5 b 1 0.5 Biso',
        'O O 0 0.5 0.5 c 1 0.5 Biso',
    ]
    return {
        'project.edi': project_record(
            'pd-neut-cwl_lbco_simulation',
            'La₀.₅Ba₀.₅CoO₃ [Pm-3m] · HRPT @ PSI',
            'Cubic perovskite · Simulated pattern without measured data',
            purpose='simulation',
            instrument='HRPT',
            facility='PSI',
        ),
        'analysis/analysis.edi': calculation_analysis(),
        'structures/lbco.edi': structure(
            'lbco', cell_lines(3.88, 3.88, 3.88), 'P m -3 m', sites, system=1
        ),
        'experiments/hrpt.edi': text(
            ['data_hrpt', '', '_edi.schema_version 3'],
            experiment_type('constant wavelength', 'neutron'),
            ['_instrument.setup_wavelength 1.494', '_instrument.calib_twotheta_offset 0'],
            [*PEAK_CW, '_peak.broad_lorentz_y 0.1', '_peak.cutoff_fwhm 30'],
            [
                '_data_range.two_theta_min 10',
                '_data_range.two_theta_max 160',
                '_data_range.two_theta_step 0.05',
            ],
            linked('lbco', 10.0),
            line_background([(10, 20), (160, 20)]),
        ),
    }


def pd_neut_tof_si_simulation() -> dict[str, str]:
    # Silicon on the SEPD bank of the fitted Si case: diffraction-lib's simulate-si-tof settings.
    return {
        'project.edi': project_record(
            'pd-neut-tof_si_simulation',
            'Silicon [Fd-3m] · SEPD @ Argonne',
            'Silicon standard · Simulated time-of-flight pattern without measured data',
            purpose='simulation',
            instrument='SEPD',
            facility='Argonne',
        ),
        'analysis/analysis.edi': calculation_analysis(),
        'structures/si.edi': structure(
            'si',
            cell_lines(5.431, 5.431, 5.431),
            'F d -3 m',
            ['Si Si 0.125 0.125 0.125 a 1 0.5 Biso'],
            system=2,
        ),
        'experiments/sepd.edi': text(
            ['data_sepd', '', '_edi.schema_version 3'],
            experiment_type('time-of-flight', 'neutron'),
            [
                '_instrument.setup_twotheta_bank 144.845',
                '_instrument.calib_d_to_tof_offset 0',
                '_instrument.calib_d_to_tof_linear 7476.91',
                '_instrument.calib_d_to_tof_quadratic -1.54',
            ],
            [
                '_peak.type tof-jorgensen',
                '_peak.broad_gauss_sigma_0 3',
                '_peak.broad_gauss_sigma_1 40',
                '_peak.broad_gauss_sigma_2 2',
                '_peak.broad_gauss_size 0',
                '_peak.broad_gauss_strain 0',
                '_peak.decay_beta_0 0.04221',
                '_peak.decay_beta_1 0.00946',
                '_peak.rise_alpha_0 0',
                '_peak.rise_alpha_1 0.5971',
                '_peak.cutoff_fwhm 12',
            ],
            [
                '_data_range.time_of_flight_min 5000',
                '_data_range.time_of_flight_max 15000',
                '_data_range.time_of_flight_step 2',
            ],
            linked('si', 10.0),
            line_background([(10000, 500), (40000, 500)]),
        ),
    }


def pd_xray_cwl_nacl_simulation() -> dict[str, str]:
    # Rock salt with a laboratory Cu K-alpha1 source and a graphite monochromator's polarization.
    sites = ['Na Na 0 0 0 a 1 0.5 Biso', 'Cl Cl 0.5 0.5 0.5 b 1 0.5 Biso']
    return {
        'project.edi': project_record(
            'pd-xray-cwl_nacl_simulation',
            'NaCl [Fm-3m] · Laboratory X-ray',
            'Rock salt · Simulated Cu Kα₁ pattern without measured data'  # noqa: RUF001
            ' · Monochromator polarization',
            purpose='simulation',
            neutron=False,
        ),
        'analysis/analysis.edi': calculation_analysis(),
        'structures/nacl.edi': structure(
            'nacl', cell_lines(5.62, 5.62, 5.62), 'F m -3 m', sites, system=1
        ),
        'experiments/lab.edi': text(
            ['data_lab', '', '_edi.schema_version 3'],
            experiment_type('constant wavelength', 'xray'),
            [
                '_scattering_source.xray_form_factor it1992',
                '_scattering_source.xray_dispersion sasaki1989',
            ],
            [
                '_instrument.setup_wavelength 1.5406',
                '_instrument.calib_twotheta_offset 0',
                '_instrument.setup_polarization_coefficient 0.5',
                '_instrument.setup_monochromator_twotheta 26.5650511771',
            ],
            [*PEAK_CW, '_peak.broad_lorentz_y 0', '_peak.cutoff_fwhm 48'],
            [
                '_data_range.two_theta_min 10',
                '_data_range.two_theta_max 150',
                '_data_range.two_theta_step 0.02',
            ],
            linked('nacl', 1.0),
        ),
    }


SCAN_SOURCE = CLI / 'pd-neut-cwl_cosio-d20_scan-162f' / 'project' / 'experiments' / 'd20_scan'
SCAN_ID = 'pd-neut-cwl_cosio-d20_scan'
# The last seven frames of the cooling run (51.86 K down to 50.41 K) carry Co2SiO4's magnetic
# peaks: (100) and (001) stand 3 to 60 standard deviations above their level in the paramagnetic
# frames. The nuclear model cannot fit them, so the case keeps the 155 frames down to 52.34 K.
SCAN_FRAMES = 155


def scan_frames() -> list:
    frames = sorted(SCAN_SOURCE.glob('*.dat'))
    if len(frames) != 162:
        raise SystemExit(f'{SCAN_SOURCE}: expected the 162 frames of the cooling run')
    return frames[:SCAN_FRAMES]


def pd_neut_cwl_cosio_d20_scan() -> dict[str, str]:
    template = scan_frames()[0]
    rows = read_points(template)
    excluded = [(0, 8), (150, 180)]
    level = flat_level(rows, excluded)
    positions = [8, 9, 10, 11, 12, 15, 25, 30, 50, 70, 90, 110, 130, 150]
    sites = [
        f'Co1 Co 0 0 0 a 1 {free(BISO)} Biso',
        f'Co2 Co {free(0.28)} 0.25 {free(0.98)} c 1 {BISO} Biso',
        f'Si Si {free(0.09)} 0.25 {free(0.43)} c 1 {free(BISO)} Biso',
        f'O1 O {free(0.09)} 0.25 {free(0.77)} c 1 {free(BISO)} Biso',
        f'O2 O {free(0.45)} 0.25 {free(0.22)} c 1 {free(BISO)} Biso',
        f'O3 O {free(0.16)} {free(0.03)} {free(0.28)} d 1 {free(BISO)} Biso',
    ]
    return {
        'project.edi': project_record(
            'pd-neut-cwl_cosio-d20_scan',
            'Co₂SiO₄ [Pnma] · D20 @ ILL',
            'Cooling scan · 155 patterns from 497.4 to 52.3 K · Magnetic frames left out',
            instrument='D20',
            facility='ILL',
        ),
        'analysis/analysis.edi': text(
            ['_edi.schema_version 3'],
            ['_fitting_mode.type sequential'],
            ['_minimizer.type crysta', '_minimizer.max_iterations 1000'],
            loop(
                ['_alias.id', '_alias.parameter_unique_name'],
                [
                    ['biso_Co1', 'cosio.atom_site.Co1.adp_iso'],
                    ['biso_Co2', 'cosio.atom_site.Co2.adp_iso'],
                ],
            ),
            loop(
                ['_constraint.id', '_constraint.expression'],
                [['biso_Co2', '"biso_Co2 = biso_Co1"']],
            ),
            [
                '_sequential_fit.data_dir experiments/d20_scan',
                '_sequential_fit.file_pattern *.dat',
                '_sequential_fit.reverse false',
                f'_sequential_fit.template_file {template.name}',
            ],
            loop(
                [
                    '_sequential_fit_extract.id',
                    '_sequential_fit_extract.target',
                    '_sequential_fit_extract.pattern',
                    '_sequential_fit_extract.required',
                ],
                [['temperature', 'diffrn.ambient_temperature', r'^TEMP\s+([0-9.]+)', 'true']],
            ),
        ),
        'structures/cosio.edi': structure(
            'cosio', cell_lines(free(10.31), free(6.0), free(4.79)), 'P n m a', sites, system='abc'
        ),
        'experiments/d20.edi': text(
            ['data_d20', '', '_edi.schema_version 3'],
            experiment_type('constant wavelength', 'neutron'),
            [f'_data_source.file_name {template.name}'],
            [
                '_peak.type cwl-tch-pseudo-voigt',
                f'_peak.broad_gauss_u {free(0.2)}',
                f'_peak.broad_gauss_v {free(-0.5)}',
                f'_peak.broad_gauss_w {free(0.4)}',
                '_peak.broad_lorentz_x 0',
                f'_peak.broad_lorentz_y {free(0.01)}',
                '_peak.cutoff_fwhm 8',
            ],
            ['_instrument.setup_wavelength 1.87', f'_instrument.calib_twotheta_offset {free(0)}'],
            loop(
                ['_excluded_region.id', '_excluded_region.start', '_excluded_region.end'],
                [[i, lo, hi] for i, (lo, hi) in enumerate(excluded, 1)],
            ),
            linked('cosio', free(1)),
            line_background([(x, free(level)) for x in positions]),
            data_loop(rows, 'two_theta'),
        ),
    }


def copy_scan_frames(project) -> None:
    """The scan's data files, copied byte for byte after the builder writes the project."""
    target = project / 'experiments' / 'd20_scan'
    target.mkdir(parents=True, exist_ok=True)
    for frame in scan_frames():
        shutil.copyfile(frame, target / frame.name)


CASES = {
    'pd-neut-cwl_lbco_simulation': pd_neut_cwl_lbco_simulation,
    'pd-neut-tof_si_simulation': pd_neut_tof_si_simulation,
    'pd-xray-cwl_nacl_simulation': pd_xray_cwl_nacl_simulation,
    SCAN_ID: pd_neut_cwl_cosio_d20_scan,
}

# Files a case adds after its project files are written.
AFTER = {SCAN_ID: copy_scan_frames}
