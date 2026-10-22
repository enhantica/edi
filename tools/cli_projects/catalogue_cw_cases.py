# SPDX-License-Identifier: BSD-3-Clause
"""Constant-wavelength cases built from edi's existing projects, which stay as they are.

Each case reads the measured pattern from its source project's `_data` loop and nothing else from
it; the model and the start follow the rule in `build_catalogue_projects.py`. The start values
below are the source's or the diffraction-lib tutorial's, rounded as that rule says.
"""

from __future__ import annotations

from catalogue_common import (
    BISO,
    CLI,
    Row,
    cell_lines,
    data_loop,
    flat_level,
    free,
    loop,
    project_record,
    structure,
    text,
)
from catalogue_joint import pbso4_lab, pbso4_structure


def source_rows(pid: str, experiment: str) -> list[Row]:
    """The measured points of a source project's experiment, as `read_points` gives them."""
    path = CLI / pid / 'project' / 'experiments' / f'{experiment}.edi'
    lines = path.read_text(encoding='utf-8').splitlines()
    start = next(i for i, line in enumerate(lines) if line.startswith('_data.'))
    names = []
    for line in lines[start:]:
        if not line.startswith('_data.'):
            break
        names.append(line.strip())
    axis = next(n for n in names if n in {'_data.two_theta', '_data.time_of_flight'})
    ix, iy, isu = (
        names.index(n) for n in (axis, '_data.intensity_meas', '_data.intensity_meas_su')
    )
    rows = []
    for line in lines[start + len(names) :]:
        parts = line.split()
        if len(parts) != len(names):
            break
        rows.append((parts[ix], parts[iy], parts[isu], float(parts[ix]), float(parts[iy])))
    return rows


def flat_background(positions, level) -> list[str]:
    return [
        '_background.type line-segment',
        '',
        *loop(
            ['_background.id', '_background.position', '_background.intensity'],
            [[i, x, free(level)] for i, x in enumerate(positions, 1)],
        ),
    ]


def excluded_loop(regions) -> list[str]:
    return loop(
        ['_excluded_region.id', '_excluded_region.start', '_excluded_region.end'],
        [[i, lo, hi] for i, (lo, hi) in enumerate(regions, 1)],
    )


def neutron_type() -> list[str]:
    return [
        '_experiment_type.sample_form powder',
        '_experiment_type.beam_mode "constant wavelength"',
        '_experiment_type.radiation_probe neutron',
        '_experiment_type.scattering_type bragg',
    ]


def analysis(*blocks: list[str], descent: str | None = None) -> str:
    minimizer = ['_minimizer.type crysta', '_minimizer.max_iterations 1000']
    if descent is not None:
        minimizer.append(f'_minimizer.descent {descent}')
    return text(['_edi.schema_version 3'], ['_fitting_mode.type single'], minimizer, *blocks)


def biso_tie(structure_id: str, first: str, second: str) -> list[list[str]]:
    """Aliases and a constraint making `second`'s Biso (not free itself) equal to `first`'s."""
    a, b = f'biso_{first}', f'biso_{second}'
    return [
        loop(
            ['_alias.id', '_alias.parameter_unique_name'],
            [
                [a, f'{structure_id}.atom_site.{first}.adp_iso'],
                [b, f'{structure_id}.atom_site.{second}.adp_iso'],
            ],
        ),
        loop(['_constraint.id', '_constraint.expression'], [[b, f'"{b} = {a}"']]),
    ]


# ----------------------------------------------------------------------
#  La0.5Ba0.5CoO3 on HRPT
# ----------------------------------------------------------------------


def lbco_hrpt_basic() -> dict[str, str]:
    rows = source_rows('pd-neut-cwl_lbco-hrpt_start-4', 'hrpt')
    excluded = [(0, 5), (165, 180)]
    level = flat_level(rows, excluded)
    sites = [
        f'La La 0 0 0 a 0.5 {free(BISO)} Biso',
        f'Ba Ba 0 0 0 a 0.5 {BISO} Biso',
        f'Co Co 0.5 0.5 0.5 b 1 {free(BISO)} Biso',
        f'O O 0 0.5 0.5 c 1 {free(BISO)} Biso',
    ]
    experiment = text(
        ['data_hrpt', '', '_edi.schema_version 3'],
        neutron_type(),
        [
            '_peak.type cwl-tch-pseudo-voigt',
            f'_peak.broad_gauss_u {free(0.08)}',
            f'_peak.broad_gauss_v {free(-0.1)}',
            f'_peak.broad_gauss_w {free(0.1)}',
            '_peak.broad_lorentz_x 0',
            f'_peak.broad_lorentz_y {free(0.08)}',
            '_peak.cutoff_fwhm 30',
        ],
        ['_instrument.setup_wavelength 1.494', f'_instrument.calib_twotheta_offset {free(0)}'],
        excluded_loop(excluded),
        loop(['_linked_structure.structure_id', '_linked_structure.scale'], [['lbco', free(9)]]),
        flat_background([10, 30, 50, 110, 165], level),
        data_loop(rows, 'two_theta'),
    )
    return {
        'project.edi': project_record(
            'pd_neut_cwl_lbco_hrpt_basic',
            'La₀.₅Ba₀.₅CoO₃ [Pm-3m] · HRPT @ PSI',
            'Cubic perovskite · La and Ba sharing one site · Profile, background, displacements',
            instrument='HRPT',
            facility='PSI',
        ),
        'analysis/analysis.edi': analysis(*biso_tie('lbco', 'La', 'Ba')),
        'structures/lbco.edi': structure(
            'lbco', cell_lines(free(3.88), 3.88, 3.88), 'P m -3 m', sites, system='1'
        ),
        'experiments/hrpt.edi': experiment,
    }


# ----------------------------------------------------------------------
#  Co2SiO4 on D20
# ----------------------------------------------------------------------


def cosio_d20_basic() -> dict[str, str]:
    rows = source_rows('pd-neut-cwl_cosio-d20_start-4', 'd20')
    level = flat_level(rows)
    sites = [
        f'Co1 Co 0 0 0 a 1 {free(BISO)} Biso',
        f'Co2 Co {free(0.28)} 0.25 {free(0.98)} c 1 {BISO} Biso',
        f'Si Si {free(0.09)} 0.25 {free(0.43)} c 1 {free(BISO)} Biso',
        f'O1 O {free(0.09)} 0.25 {free(0.77)} c {free(1)} {free(BISO)} Biso',
        f'O2 O {free(0.45)} 0.25 {free(0.22)} c {free(1)} {free(BISO)} Biso',
        f'O3 O {free(0.16)} {free(0.03)} {free(0.28)} d {free(1)} {free(BISO)} Biso',
    ]
    experiment = text(
        ['data_d20', '', '_edi.schema_version 3'],
        neutron_type(),
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
        loop(['_linked_structure.structure_id', '_linked_structure.scale'], [['cosio', free(1)]]),
        flat_background([8, 9, 10, 11, 12, 15, 25, 30, 50, 70, 90, 110, 130, 150], level),
        data_loop(rows, 'two_theta'),
    )
    return {
        'project.edi': project_record(
            'pd_neut_cwl_cosio_d20_basic',
            'Co₂SiO₄ [Pnma] · D20 @ ILL',
            'Olivine · Coordinates, displacements and oxygen occupancies',
            instrument='D20',
            facility='ILL',
        ),
        # The default descent stops in a shallower minimum from this start (Rwp 5.4 %).
        'analysis/analysis.edi': analysis(
            *biso_tie('cosio', 'Co1', 'Co2'), descent='fast_descent'
        ),
        'structures/cosio.edi': structure(
            'cosio', cell_lines(free(10.3), free(6.0), free(4.8)), 'P n m a', sites, system='abc'
        ),
        'experiments/d20.edi': experiment,
    }


# ----------------------------------------------------------------------
#  PbSO4, laboratory X-ray
# ----------------------------------------------------------------------


def pbso4_lab_basic() -> dict[str, str]:
    rows = source_rows('pd-xray-cwl_pbso4-lab_round-robin', 'pbsox')
    return {
        'project.edi': project_record(
            'pd_xray_cwl_pbso4_lab_basic',
            'PbSO₄ [Pnma] · Laboratory X-ray',
            'Rietveld round-robin data · Cu Kα doublet · Bérar-Baldinozzi asymmetry',  # noqa: RUF001
            neutron=False,
        ),
        'analysis/analysis.edi': analysis(),
        'structures/pbso4.edi': pbso4_structure(),
        'experiments/lab.edi': pbso4_lab(rows),
    }


# ----------------------------------------------------------------------
#  YAlO3 + Al2O3 on SPODI, 3 K
# ----------------------------------------------------------------------


def yap_spodi_two_phase() -> dict[str, str]:
    source = 'pd-neut-cwl_yap-spodi_3k'
    rows = source_rows(source, 'spodi')
    excluded = [(0, 4), (153.95, 180)]
    level = flat_level(rows, excluded)
    positions = background_positions(source, 'spodi')
    yap_sites = [
        f'Y Y {free(0.01)} {free(0.55)} 0.25 c 1 {free(BISO)} Biso',
        f'Al Al 0 0 0 a 1 {free(BISO)} Biso',
        f'O1 O {free(-0.08)} {free(-0.02)} 0.25 c 1 {free(BISO)} Biso',
        f'O2 O {free(0.2)} {free(0.29)} {free(0.04)} d 1 {free(BISO)} Biso',
    ]
    alumina_sites = [
        f'Al1 Al 0 0 {free(0.33)} c 1 {free(BISO)} Biso',
        f'O1 O {free(0.35)} 0 0.25 e 1 {free(BISO)} Biso',
    ]
    experiment = text(
        ['data_spodi', '', '_edi.schema_version 3'],
        neutron_type(),
        ['_scattering_source.neutron_scattering_length sears1992'],
        [
            '_peak.type cwl-pseudo-voigt-berar-baldinozzi',
            f'_peak.broad_gauss_u {free(0.04)}',
            f'_peak.broad_gauss_v {free(-0.05)}',
            f'_peak.broad_gauss_w {free(0.1)}',
            f'_peak.mixing_eta_0 {free(0.1)}',
            '_peak.mixing_eta_1 0',
            f'_peak.asym_beba_a0 {free(0)}',
            f'_peak.asym_beba_b0 {free(0)}',
            f'_peak.asym_beba_a1 {free(0)}',
            f'_peak.asym_beba_b1 {free(0)}',
            '_peak.asym_beba_limit 160',
            '_peak.cutoff_fwhm 20',
        ],
        ['_instrument.setup_wavelength 1.54816', f'_instrument.calib_twotheta_offset {free(0)}'],
        ['_absorption.type cylinder-hewat', '_absorption.mu_r 0.0221'],
        excluded_loop(excluded),
        loop(
            ['_linked_structure.structure_id', '_linked_structure.scale'],
            [['YAlO3', free(30)], ['Al2O3', free(0.2)]],
        ),
        flat_background(positions, level),
        data_loop(rows, 'two_theta'),
    )
    return {
        'project.edi': project_record(
            'pd_neut_cwl_yap_spodi_two_phase',
            'YAlO₃ [Pbnm] / Al₂O₃ [R-3c] · SPODI @ FRM II',
            '2 phases at 3 K · Shared Bérar-Baldinozzi profile · Cylinder absorption',
            instrument='SPODI',
            facility='FRM II',
        ),
        'analysis/analysis.edi': analysis(),
        'structures/YAlO3.edi': structure(
            'YAlO3', cell_lines(free(5.17), free(5.33), free(7.36)), 'P b n m', yap_sites
        ),
        'structures/Al2O3.edi': structure(
            'Al2O3',
            cell_lines(free(4.76), 4.76, free(12.97), gamma=120),
            'R -3 c',
            alumina_sites,
            system='h',
        ),
        'experiments/spodi.edi': experiment,
    }


def background_positions(pid: str, experiment: str) -> list[str]:
    """The background point positions of a source project's line-segment background."""
    path = CLI / pid / 'project' / 'experiments' / f'{experiment}.edi'
    lines = path.read_text(encoding='utf-8').splitlines()
    start = lines.index('_background.intensity') + 1
    positions = []
    for line in lines[start:]:
        parts = line.split()
        if len(parts) != 3:
            break
        positions.append(parts[1])
    return positions


# ----------------------------------------------------------------------
#  LaB6 (11B) on ECHIDNA
# ----------------------------------------------------------------------


def lab6_echidna_basic() -> dict[str, str]:
    rows = source_rows('pd-neut-cwl_lab6-11b-echidna_tch-fcj', 'echidna')
    excluded = [(0, 10), (164, 180)]
    level = flat_level(rows, excluded)
    sites = [
        f'La La 0 0 0 a 1 {free(BISO)} Biso',
        f'B B {free(0.2)} 0.5 0.5 f 1 {free(BISO)} Biso',
    ]
    lengths = loop(
        ['_scattering_length.type_symbol', '_scattering_length.length_fm'],
        [['B', 6.65], ['La', 8.24]],
    )
    experiment = text(
        ['data_echidna', '', '_edi.schema_version 3'],
        neutron_type(),
        [
            '_peak.type cwl-tch-pseudo-voigt-fcj',
            f'_peak.broad_gauss_u {free(0.09)}',
            f'_peak.broad_gauss_v {free(-0.4)}',
            f'_peak.broad_gauss_w {free(0.5)}',
            '_peak.broad_lorentz_x 0',
            f'_peak.broad_lorentz_y {free(0.05)}',
            '_peak.asym_fcj_1 0.08',
            '_peak.asym_fcj_2 0.08',
            '_peak.cutoff_fwhm 12',
        ],
        [
            f'_instrument.setup_wavelength {free(1.622)}',
            f'_instrument.calib_twotheta_offset {free(0)}',
            f'_instrument.calib_sample_displacement {free(0)}',
            f'_instrument.calib_sample_transparency {free(0)}',
        ],
        ['_absorption.type cylinder-hewat', '_absorption.mu_r 0.7'],
        excluded_loop(excluded),
        loop(['_linked_structure.structure_id', '_linked_structure.scale'], [['lab6', free(100)]]),
        ['_background.type polynomial', '_background.origin 80'],
        loop(
            ['_background.id', '_background.order', '_background.coef'],
            [[order + 1, order, free(level if order == 0 else 0)] for order in range(5)],
        ),
        data_loop(rows, 'two_theta'),
    )
    return {
        'project.edi': project_record(
            'pd_neut_cwl_lab6_11b_echidna_basic',
            'LaB₆ [Pm-3m] · ECHIDNA @ ANSTO',
            '¹¹B-enriched standard · TCH × FCJ · Wavelength and sample position from a standard',  # noqa: RUF001
            instrument='ECHIDNA',
            facility='ANSTO',
        ),
        'analysis/analysis.edi': analysis(),
        'structures/lab6.edi': structure(
            'lab6', cell_lines(4.156885, 4.156885, 4.156885), 'P m -3 m', sites, extra=lengths
        ),
        'experiments/echidna.edi': experiment,
    }


# ----------------------------------------------------------------------
#  Y2O3 with anisotropic beta tensors
# ----------------------------------------------------------------------

Y2O3_A = 10.61
# Each site's independent beta components; the rest follow from the site symmetry.
Y2O3_FREE_BETAS = {
    'Y1': ('adp_11', 'adp_22', 'adp_33', 'adp_23'),
    'Y2': ('adp_11', 'adp_12'),
    'O1': ('adp_11', 'adp_22', 'adp_33', 'adp_12', 'adp_13', 'adp_23'),
}


def y2o3_aniso_adp() -> dict[str, str]:
    source = 'pd-neut-cwl_y2o3_beta-adp'
    rows = source_rows(source, 'y2o3')
    excluded = [(0, 12), (137.5, 180)]
    level = flat_level(rows, excluded)
    # The beta tensor of an isotropic Biso on a cubic cell: beta_ii = B a*^2 / 4.
    beta = round(BISO / (4 * Y2O3_A**2), 6)
    components = ('adp_11', 'adp_22', 'adp_33', 'adp_12', 'adp_13', 'adp_23')
    aniso = []
    for site, independent in Y2O3_FREE_BETAS.items():
        values = [beta, beta, beta, 0, 0, 0]
        aniso.append([
            site,
            *(free(v) if c in independent else v for c, v in zip(components, values, strict=True)),
        ])
    sites = [
        f'Y1 Y {free(-0.03)} 0 0.25 d 1 {BISO} beta',
        f'Y2 Y 0.25 0.25 0.25 b 1 {BISO} beta',
        f'O1 O {free(0.39)} {free(0.15)} {free(0.38)} e 1 {BISO} beta',
    ]
    aniso_loop = loop(
        ['_atom_site_aniso.id', *(f'_atom_site_aniso.{c}' for c in components)], aniso
    )
    experiment = text(
        ['data_y2o3', '', '_edi.schema_version 3'],
        neutron_type(),
        ['_scattering_source.neutron_scattering_length sears1992'],
        [
            '_peak.type cwl-tch-pseudo-voigt',
            f'_peak.broad_gauss_u {free(0.04)}',
            f'_peak.broad_gauss_v {free(-0.07)}',
            f'_peak.broad_gauss_w {free(0.1)}',
            '_peak.broad_lorentz_x 0',
            '_peak.broad_lorentz_y 0',
            '_peak.cutoff_fwhm 20',
        ],
        ['_instrument.setup_wavelength 1.54822', f'_instrument.calib_twotheta_offset {free(0)}'],
        excluded_loop(excluded),
        loop(['_linked_structure.structure_id', '_linked_structure.scale'], [['y2o3', free(0.1)]]),
        flat_background(background_positions(source, 'y2o3'), level),
        data_loop(rows, 'two_theta'),
    )
    return {
        'project.edi': project_record(
            'pd_neut_cwl_y2o3_aniso_adp',
            'Y₂O₃ [Ia-3] · Unknown instrument',
            'Anisotropic β tensors tied by site symmetry · Coordinates, profile and background',
        ),
        'analysis/analysis.edi': analysis(),
        'structures/y2o3.edi': structure(
            'y2o3',
            cell_lines(free(Y2O3_A), Y2O3_A, Y2O3_A),
            'I a -3',
            sites,
            system='1',
            extra=aniso_loop,
        ),
        'experiments/y2o3.edi': experiment,
    }


CASES = {
    'pd-neut-cwl_lbco-hrpt_basic': lbco_hrpt_basic,
    'pd-neut-cwl_cosio-d20_basic': cosio_d20_basic,
    'pd-xray-cwl_pbso4-lab_basic': pbso4_lab_basic,
    'pd-neut-cwl_yap-spodi_two-phase': yap_spodi_two_phase,
    'pd-neut-cwl_lab6-11b-echidna_basic': lab6_echidna_basic,
    'pd-neut-cwl_y2o3_aniso-adp': y2o3_aniso_adp,
}
