# SPDX-License-Identifier: BSD-3-Clause
"""The time-of-flight cases built from edi's existing projects, each from a user's start.

The measured points come from the source project's `_data` loop; no fitted value is copied. The
start follows the catalogue rule (`build_catalogue_projects.py`), read for time of flight:

- the d-to-TOF zero starts at 0 when the source frees it; the other calibration terms (DIFC, DIFA,
  the bank angle) stay at the values the source declares, and a DIFC the source frees starts at
  the nominal value named here;
- a profile parameter the source frees starts at one significant figure of the source's value; one
  the source keeps fixed is the instrument's resolution and stays as declared;
- a free absorption coefficient starts at 0;
- every site starts at Biso 0.5, free coordinates are rounded to two decimals, and the scale is
  given to one significant figure;
- the background is flat at `flat_level`, on the source's points or with only the constant
  term of a Chebyshev or polynomial set.
"""

from __future__ import annotations

from catalogue_common import (
    BISO,
    CLI,
    cell_lines,
    flat_level,
    free,
    loop,
    project_record,
    structure,
    text,
)


def sig1(value: float) -> str:
    """A value to one significant figure."""
    return f'{float(f"{value:.0e}"):g}'


def maybe_free(value: float | str, *, is_free: bool) -> str:
    return free(value) if is_free else str(value)


def source_rows(pid: str, experiment: str) -> list[tuple[str, str, str, float, float]]:
    """The measured points of a source project's experiment: (x, y, su, x, y) rows."""
    path = CLI / pid / 'project' / 'experiments' / f'{experiment}.edi'
    lines = path.read_text(encoding='utf-8').splitlines()
    start = next(i for i, line in enumerate(lines) if line.startswith('_data.'))
    columns = []
    i = start
    while lines[i].startswith('_data.'):
        columns.append(lines[i].strip()[len('_data.') :])
        i += 1
    axis = 'time_of_flight' if 'time_of_flight' in columns else 'two_theta'
    ix, iy, isu = (columns.index(c) for c in (axis, 'intensity_meas', 'intensity_meas_su'))
    rows = []
    for line in lines[i:]:
        parts = line.split()
        if len(parts) != len(columns) or line.startswith(('_', 'loop_', 'data_')):
            break
        rows.append((parts[ix], parts[iy], parts[isu], float(parts[ix]), float(parts[iy])))
    return rows


def data_loop(rows) -> list[str]:
    lines = ['loop_', '_data.time_of_flight', '_data.intensity_meas', '_data.intensity_meas_su']
    return lines + [f'{x} {y} {su}' for x, y, su, _, _ in rows]


def excluded_loop(regions) -> list[str]:
    return loop(
        ['_excluded_region.id', '_excluded_region.start', '_excluded_region.end'],
        [[i, lo, hi] for i, (lo, hi) in enumerate(regions, 1)],
    )


def line_segment(positions, level: float, fixed=()) -> list[str]:
    """A flat line-segment background; `fixed` lists the 1-based points the source keeps fixed."""
    rows = [[i, x, maybe_free(level, is_free=i not in fixed)] for i, x in enumerate(positions, 1)]
    return [
        '_background.type line-segment',
        '',
        *loop(['_background.id', '_background.position', '_background.intensity'], rows),
    ]


def series(kind: str, level: float, terms: int, free_terms: int, head: list[str]) -> list[str]:
    """A flat Chebyshev or polynomial background: the constant term at `level`, the rest 0."""
    rows = [
        [order + 1, order, maybe_free(level if order == 0 else 0, is_free=order < free_terms)]
        for order in range(terms)
    ]
    return [
        f'_background.type {kind}',
        *head,
        '',
        *loop(['_background.id', '_background.order', '_background.coef'], rows),
    ]


def instrument_lines(
    bank: float, difc: float, *, difc_free: bool = False, difa: float = 0, difa_free: bool = False
) -> list[str]:
    """The bank's calibration; every case frees the zero, from 0."""
    return [
        f'_instrument.setup_twotheta_bank {bank}',
        f'_instrument.calib_d_to_tof_offset {free(0)}',
        f'_instrument.calib_d_to_tof_linear {maybe_free(difc, is_free=difc_free)}',
        f'_instrument.calib_d_to_tof_quadratic {maybe_free(difa, is_free=difa_free)}',
        '_instrument.calib_d_to_tof_reciprocal 0',
    ]


def peak_lines(peak_type: str, cutoff: float, profile: dict) -> list[str]:
    """The `_peak` items; `profile` maps an item to its start text (free or fixed)."""
    if peak_type.startswith('tof-jorgensen'):
        # Jorgensen profiles carry the size and strain terms; these cases leave them at 0.
        sizes = (
            'broad_gauss_size',
            'broad_gauss_strain',
            'broad_lorentz_size',
            'broad_lorentz_strain',
        )
        profile = {**profile, **{item: 0 for item in sizes if item not in profile}}
    return [f'_peak.type {peak_type}', f'_peak.cutoff_fwhm {cutoff}'] + [
        f'_peak.{item} {value}' for item, value in profile.items()
    ]


# Each absorption block starts with a blank line, after the instrument lines.
NO_ABSORPTION = ['', '_absorption.type none']


def cylinder(*, is_free: bool = True) -> list[str]:
    """Cylinder absorption with ABSCOR1 starting at 0."""
    return [
        '',
        '_absorption.type cylinder',
        f'_absorption.abscor1 {maybe_free(0, is_free=is_free)}',
        '_absorption.abscor2 0',
    ]


def tof_experiment(
    name: str,
    rows: list,
    *,
    setup: list[str],
    peak: list[str],
    scales: list[tuple[str, str]],
    excluded: list[tuple[float, float]],
    background: list[str],
) -> str:
    """One TOF experiment; `setup` is its instrument and absorption lines."""
    return text(
        [f'data_{name}', '', '_edi.schema_version 3'],
        [
            '_experiment_type.sample_form powder',
            '_experiment_type.beam_mode "time-of-flight"',
            '_experiment_type.radiation_probe neutron',
            '_experiment_type.scattering_type bragg',
        ],
        ['_scattering_source.neutron_scattering_length sears1992'],
        peak,
        setup,
        excluded_loop(excluded),
        loop(
            ['_linked_structure.structure_id', '_linked_structure.scale'],
            [list(s) for s in scales],
        ),
        background,
        data_loop(rows),
    )


def analysis(mode: str = 'single', *, weights=(), aliases=(), constraints=(), extra=()) -> str:
    blocks = [
        ['_edi.schema_version 3'],
        [f'_fitting_mode.type {mode}'],
        ['_minimizer.type crysta', '_minimizer.max_iterations 1000', *extra],
    ]
    if weights:
        blocks.append(
            loop(['_joint_fit.experiment_id', '_joint_fit.weight'], [list(w) for w in weights])
        )
    if aliases:
        blocks.append(
            loop(['_alias.id', '_alias.parameter_unique_name'], [list(a) for a in aliases])
        )
    if constraints:
        blocks.append(
            loop(
                ['_constraint.id', '_constraint.expression'],
                [[cid, f'"{expr}"'] for cid, expr in constraints],
            )
        )
    return text(*blocks)


# ----------------------------------------------------------------------
#  Si, SEPD
# ----------------------------------------------------------------------


def pd_neut_tof_si_sepd() -> dict[str, str]:
    source = 'pd-neut-tof_si-sepd_start-2'
    rows = source_rows(source, 'sepd')
    positions = [
        2000,
        9035,
        9335,
        11915,
        12315,
        12695,
        13745,
        14410,
        14875,
        15660,
        23075,
        23515,
        28100,
        29995,
    ]
    profile = {
        'rise_alpha_0': 0,
        'rise_alpha_1': 0.5971,
        'decay_beta_0': free(sig1(0.0408)),
        'decay_beta_1': free(sig1(0.0123)),
        'broad_gauss_sigma_0': free(sig1(3.0148)),
        'broad_gauss_sigma_1': free(sig1(33.3451)),
        'broad_gauss_sigma_2': 0,
        'broad_lorentz_gamma_0': 0,
        'broad_lorentz_gamma_1': free(sig1(2.5489)),
        'broad_lorentz_gamma_2': 0,
    }
    return {
        'project.edi': project_record(
            'pd-neut-tof_si-sepd',
            'Silicon [Fd-3m] · SEPD @ Argonne',
            'Silicon standard · Jorgensen\N{EN DASH}Von Dreele profile · '
            'Time-of-flight neutron powder data',
            instrument='SEPD',
            facility='Argonne',
        ),
        'analysis/analysis.edi': analysis(),
        'structures/si.edi': structure(
            'si',
            cell_lines(free(5.431), 5.431, 5.431),
            'F d -3 m',
            [f'Si Si 0.125 0.125 0.125 a 1 {free(BISO)} Biso'],
            system='2',
        ),
        'experiments/sepd.edi': tof_experiment(
            'sepd',
            rows,
            setup=instrument_lines(144.845, 7476.91, difa=-1.54) + NO_ABSORPTION,
            peak=peak_lines('tof-jorgensen-von-dreele', 8.2, profile),
            scales=[('si', free(sig1(600.0)))],
            excluded=[],
            background=line_segment(positions, flat_level(rows)),
        ),
    }


# ----------------------------------------------------------------------
#  NCAF, WISH, five banks
# ----------------------------------------------------------------------

NCAF_SOURCE = 'pd-neut-tof_ncaf-wish-5bank_start-5'

# Per bank (FullProf pattern 1 to 5): 2θ, the DIFC start the source declares (its FullProf
# input), DIFA, the excluded regions, whether ABSCOR1 is free, and the profile as
# (value, free in the source).
NCAF_BANKS = {
    'wish_5_6': {
        'bank': 152.827,
        'difc': 20772.9,
        'difa': -1.08308,
        'excluded': [(0, 9000), (104000, 300000)],
        'absorption_free': True,
        'profile': {
            'rise_alpha_0': (-0.009502, True),
            'rise_alpha_1': (0.110229, True),
            'decay_beta_0': (0.006672, True),
            'decay_beta_1': (0.010073, True),
            'broad_gauss_sigma_1': (0.0, False),
            'broad_gauss_sigma_2': (15.7010, True),
            'broad_lorentz_gamma_1': (0.0019, False),
        },
    },
    'wish_4_7': {
        'bank': 121.66,
        'difc': 18660.1,
        'difa': -0.47488,
        'excluded': [(0, 9000), (108000, 300000)],
        'absorption_free': True,
        'profile': {
            'rise_alpha_0': (-0.011598, True),
            'rise_alpha_1': (0.122764, True),
            'decay_beta_0': (0.006428, True),
            'decay_beta_1': (0.014680, True),
            'broad_gauss_sigma_1': (29.3563, True),
            'broad_gauss_sigma_2': (18.1966, True),
            'broad_lorentz_gamma_1': (0.0, False),
        },
    },
    'wish_3_8': {
        'bank': 90,
        'difc': 15105.5,
        'difa': 1.00785,
        'excluded': [(0, 9000), (116000, 300000)],
        'absorption_free': True,
        'profile': {
            'rise_alpha_0': (-0.012131, True),
            'rise_alpha_1': (0.122897, True),
            'decay_beta_0': (0.005991, True),
            'decay_beta_1': (0.027663, True),
            'broad_gauss_sigma_1': (62.2430, True),
            'broad_gauss_sigma_2': (16.8600, True),
            'broad_lorentz_gamma_1': (0.0002, False),
        },
    },
    'wish_2_9': {
        'bank': 58.33,
        'difc': 10389.9,
        'difa': 1.85233,
        'excluded': [(0, 7000), (134000, 300000)],
        'absorption_free': True,
        'profile': {
            'rise_alpha_0': (0.040554, True),
            'rise_alpha_1': (0.023869, True),
            'decay_beta_0': (0.005322, True),
            'decay_beta_1': (0.083299, True),
            'broad_gauss_sigma_1': (69.8201, True),
            'broad_gauss_sigma_2': (23.0513, True),
            'broad_lorentz_gamma_1': (1.6846, True),
        },
    },
    'wish_1_10': {
        'bank': 27.081,
        'difc': 4985.32,
        'difa': 1.85733,
        'excluded': [(0, 7000), (240000, 300000)],
        'absorption_free': False,
        'profile': {
            'rise_alpha_0': (0.014439, False),
            'rise_alpha_1': (0.055070, False),
            'decay_beta_0': (0.004707, False),
            'decay_beta_1': (0.137368, False),
            'broad_gauss_sigma_1': (0.0, False),
            'broad_gauss_sigma_2': (15.4063, False),
            'broad_lorentz_gamma_1': (8.2904, False),
        },
    },
}


def source_background(pid: str, experiment: str) -> list[tuple[str, bool]]:
    """The source's background points: [(position, free)]."""
    path = CLI / pid / 'project' / 'experiments' / f'{experiment}.edi'
    lines = path.read_text(encoding='utf-8').splitlines()
    i = lines.index('_background.intensity') + 1
    points = []
    while i < len(lines) and len(lines[i].split()) == 3:
        _, position, intensity = lines[i].split()
        points.append((position, '(' in intensity))
        i += 1
    return points


# The owner's NCAF start (2026-10-22): peaks about 30 % narrower than the fitted ones, with the
# Gaussian/Lorentzian balance and the asymmetry moved too. sigma_1 and sigma_2 are terms of the
# Gaussian variance, so 0.7 in width is 0.49 here; the Lorentzian narrows more than the Gaussian
# and the rise and decay edges sharpen.
NCAF_START_FACTORS = {'broad_gauss': 0.49, 'broad_lorentz': 0.6, 'rise': 1.3, 'decay': 1.15}


def sig2(value: float) -> str:
    """A value to two significant figures."""
    return f'{float(f"{value:.1e}"):g}'


def ncaf_start(item: str, value: float) -> str:
    """A free profile term's start: the fitted value moved by its NCAF_START_FACTORS entry."""
    factor = next(f for prefix, f in NCAF_START_FACTORS.items() if item.startswith(prefix))
    return free(sig2(value * factor))


def ncaf_bank(name: str, spec: dict) -> str:
    rows = source_rows(NCAF_SOURCE, name)
    points = source_background(NCAF_SOURCE, name)
    level = flat_level(rows, spec['excluded'])
    profile = {'broad_gauss_sigma_0': 0, 'broad_lorentz_gamma_0': 0, 'broad_lorentz_gamma_2': 0}
    for item, (value, is_free) in spec['profile'].items():
        profile[item] = ncaf_start(item, value) if is_free else value
    return tof_experiment(
        name,
        rows,
        setup=instrument_lines(spec['bank'], spec['difc'], difc_free=True, difa=spec['difa'])
        + cylinder(is_free=spec['absorption_free']),
        peak=peak_lines('tof-jorgensen-von-dreele', 8, dict(sorted(profile.items()))),
        scales=[('ncaf', free(sig1(37.0)))],
        excluded=spec['excluded'],
        background=line_segment(
            [p for p, _ in points],
            level,
            fixed={i for i, (_, is_free) in enumerate(points, 1) if not is_free},
        ),
    )


def pd_neut_tof_ncaf_wish() -> dict[str, str]:
    # I 21 3, the positions of the source's structure rounded to two decimals.
    sites = [
        f'Ca1 Ca {free(0.47)} 0 0.25 b 1 {free(BISO)} Biso',
        f'Al1 Al {free(0.25)} 0.25 0.25 a 1 {free(BISO)} Biso',
        f'Na1 Na {free(0.09)} 0.09 0.09 a 1 {free(BISO)} Biso',
        f'F1 F {free(0.14)} {free(0.31)} {free(0.12)} c 1 {free(BISO)} Biso',
        f'F2 F {free(0.36)} {free(0.36)} {free(0.19)} c 1 {free(BISO)} Biso',
        f'F3 F {free(0.46)} 0.46 0.46 a 1 {free(BISO)} Biso',
    ]
    files = {
        'project.edi': project_record(
            'pd-neut-tof_ncaf-wish',
            'Na₂Ca₃Al₂F₁₄ [I2₁3] · WISH @ ISIS',
            'All five detector bank pairs fitted jointly · '
            'Jorgensen\N{EN DASH}Von Dreele profile · '
            'Per-bank calibration',
            instrument='WISH',
            facility='ISIS',
        ),
        'analysis/analysis.edi': analysis(
            'joint',
            weights=[(name, 1.0) for name in NCAF_BANKS],
            extra=['_minimizer.chi_square_tolerance 1e-4'],
        ),
        'structures/ncaf.edi': structure(
            'ncaf', cell_lines(10.250256, 10.250256, 10.250256), 'I 21 3', sites, system='1'
        ),
    }
    for name, spec in NCAF_BANKS.items():
        files[f'experiments/{name}.edi'] = ncaf_bank(name, spec)
    return files


# ----------------------------------------------------------------------
#  Diamond, DREAM
# ----------------------------------------------------------------------


def diamond_dream() -> dict[str, str]:
    rows = source_rows('pd-neut-tof_diamond-dream_basic', 'dream')
    excluded = [(0, 9999), (66503.6875, 200000)]
    profile = {
        'rise_alpha_0': 0,
        'rise_alpha_1': free(sig1(0.022544)),
        'decay_beta_0': free(sig1(0.01433)),
        'decay_beta_1': 0,
        'broad_gauss_sigma_0': free(sig1(46937.7188)),
        'broad_gauss_sigma_1': free(sig1(4887.918)),
        'broad_gauss_sigma_2': 0,
        'broad_lorentz_gamma_0': 0,
        'broad_lorentz_gamma_1': 0,
        'broad_lorentz_gamma_2': 0,
    }
    return {
        'project.edi': project_record(
            'pd_neut_tof_diamond_dream_mcstas',
            'Diamond [Fd-3m] · DREAM @ ESS',
            'McStas-simulated 90° bank · Jorgensen profile · Structure and profile fit',
            instrument='DREAM',
            facility='ESS',
        ),
        'analysis/analysis.edi': analysis(),
        'structures/diamond.edi': structure(
            'diamond',
            cell_lines(free(3.57), 3.57, 3.57),
            'F d -3 m',
            [f'C C 0.125 0.125 0.125 c 1 {free(BISO)} Biso'],
            system='1',
        ),
        'experiments/dream.edi': tof_experiment(
            'dream',
            rows,
            setup=instrument_lines(90, 28385.86133) + NO_ABSORPTION,
            peak=peak_lines('tof-jorgensen', 30, profile),
            scales=[('diamond', free(sig1(14.569629)))],
            excluded=excluded,
            background=line_segment(
                [10000, 14000, 21000, 27500, 40000, 50000, 61000, 70000],
                flat_level(rows, excluded),
            ),
        ),
    }


# ----------------------------------------------------------------------
#  CeCoAl3, POLARIS
# ----------------------------------------------------------------------


def pd_neut_tof_cecoal_polaris() -> dict[str, str]:
    rows = source_rows('pd-neut-tof_cecoal-polaris_chebyshev', 'polaris')
    excluded = [(2000.1, 3000.0), (19000.0, 20000.0)]
    profile = {
        'rise_alpha_0': 0,
        'rise_alpha_1': 0.2971,
        'decay_beta_0': 0.043085,
        'decay_beta_1': 0.002867,
        'broad_gauss_sigma_0': 0,
        'broad_gauss_sigma_1': free(sig1(39.4615)),
        'broad_gauss_sigma_2': 0,
        'broad_lorentz_gamma_0': 0,
        'broad_lorentz_gamma_1': free(sig1(4.7781)),
        'broad_lorentz_gamma_2': 0,
    }
    # P m m a, the source's positions rounded to two decimals.
    sites = [
        f'Ce Ce 0.25 0 {free(0.38)} e 1 {free(BISO)} Biso',
        f'Co Co 0.25 0 {free(0.81)} e 1 {free(BISO)} Biso',
        f'Al1 Al 0 0 0 a 1 {free(BISO)} Biso',
        f'Al2 Al 0.25 0.5 {free(0.04)} f 1 {free(BISO)} Biso',
        f'Al3 Al {free(0.07)} 0.5 {free(0.7)} j {free(1)} {free(BISO)} Biso',
    ]
    return {
        'project.edi': project_record(
            'pd-neut-tof_cecoal-polaris',
            'CeCoAl₃ [Pmma] · POLARIS @ ISIS',
            'Structure and time-of-flight profile fit · 24-term Chebyshev background',
            instrument='POLARIS',
            facility='ISIS',
        ),
        'analysis/analysis.edi': analysis(extra=['_minimizer.chi_square_tolerance 1e-4']),
        'structures/cecoal.edi': structure(
            'cecoal', cell_lines(free(7.65), free(4.05), free(6.91)), 'P m m a', sites
        ),
        'experiments/polaris.edi': tof_experiment(
            'polaris',
            rows,
            setup=instrument_lines(145.0, 6176.03076, difa=-1.92194, difa_free=True) + cylinder(),
            peak=peak_lines('tof-jorgensen-von-dreele', 4.2, profile),
            scales=[('cecoal', free(sig1(16658.97)))],
            excluded=excluded,
            background=series(
                'chebyshev',
                flat_level(rows, excluded),
                24,
                12,
                ['_background.x_min 3001.5891', '_background.x_max 19004.6582'],
            ),
        ),
    }


# ----------------------------------------------------------------------
#  CeO2, PEARL
# ----------------------------------------------------------------------


def pd_neut_tof_ceo2_pearl() -> dict[str, str]:
    rows = source_rows('pd-neut-tof_ceo2-pearl_polynomial', 'pearl')
    excluded = [(1000.1, 2000.0), (18700.0, 20000.0)]
    profile = {
        'rise_alpha_0': 0,
        'rise_alpha_1': free(sig1(0.251559)),
        'decay_beta_0': free(sig1(0.025455)),
        'decay_beta_1': free(sig1(0.029005)),
        'broad_gauss_sigma_0': 0,
        'broad_gauss_sigma_1': free(sig1(83.8088)),
        'broad_gauss_sigma_2': free(sig1(3.5751)),
        'broad_lorentz_gamma_0': 0,
        'broad_lorentz_gamma_1': free(sig1(4.8407)),
        'broad_lorentz_gamma_2': 0,
    }
    return {
        'project.edi': project_record(
            'pd-neut-tof_ceo2-pearl',
            'CeO₂ [Fm-3m] · PEARL @ ISIS',
            'NBS SRM 674a standard · Calibration and profile fit · 6-term polynomial background',
            instrument='PEARL',
            facility='ISIS',
        ),
        'analysis/analysis.edi': analysis(extra=['_minimizer.chi_square_tolerance 1e-4']),
        # The standard's cell stays fixed: it is what calibrates DIFC.
        'structures/ceo2.edi': structure(
            'ceo2',
            cell_lines(5.410495, 5.410495, 5.410495),
            'F m -3 m',
            [f'Ce Ce 0 0 0 a 1 {free(BISO)} Biso', f'O O 0.25 0.25 0.25 c 1 {free(BISO)} Biso'],
        ),
        'experiments/pearl.edi': tof_experiment(
            'pearl',
            rows,
            setup=instrument_lines(90.0, 4680, difc_free=True, difa=1.7621, difa_free=True)
            + cylinder(),
            peak=peak_lines('tof-jorgensen-von-dreele', 8.0, profile),
            scales=[('ceo2', free(sig1(2115.274)))],
            excluded=excluded,
            background=series(
                'polynomial', flat_level(rows, excluded), 6, 6, ['_background.origin 7000.0']
            ),
        ),
    }


# ----------------------------------------------------------------------
#  Ferrite and austenite, BEER: the two banks' zero and resolution
# ----------------------------------------------------------------------

BEER_SOURCE = 'pd-neut-tof_ferrite-austenite-beer_joint'


def beer_bank(name: str, difc: float, *, scales_free: bool) -> str:
    rows = source_rows(BEER_SOURCE, name)
    excluded = [(20000.00, 40158.2305), (130000.00, 180000.00)]
    points = source_background(BEER_SOURCE, name)
    profile = {
        'broad_gauss_sigma_0': free(sig1(893.6397)),
        'broad_gauss_sigma_1': free(sig1(1283.6387)),
        'broad_gauss_sigma_2': free(sig1(311.7041)),
        'broad_lorentz_gamma_0': free(sig1(5.0330)),
        'broad_lorentz_gamma_1': 0,
        'broad_lorentz_gamma_2': 0,
    }
    return tof_experiment(
        name,
        rows,
        setup=instrument_lines(90.0, difc) + NO_ABSORPTION,
        peak=peak_lines('tof-pseudo-voigt', 12, profile),
        # The N2 bank's phase scales follow the S2 bank's (constraints in analysis.edi).
        scales=[
            ('ferrite', maybe_free(sig1(401.4629), is_free=scales_free)),
            ('austenite', maybe_free(sig1(96.17031), is_free=scales_free)),
        ],
        excluded=excluded,
        background=line_segment(
            [p for p, _ in points],
            flat_level(rows, excluded),
            fixed={i for i, (_, is_free) in enumerate(points, 1) if not is_free},
        ),
    )


def beer_difc(name: str) -> float:
    path = CLI / BEER_SOURCE / 'project' / 'experiments' / f'{name}.edi'
    for line in path.read_text(encoding='utf-8').splitlines():
        if line.startswith('_instrument.calib_d_to_tof_linear'):
            return float(line.split()[1])
    raise ValueError(f'{path}: no DIFC')


def pd_neut_tof_ferrite_austenite_beer() -> dict[str, str]:
    def iron(name: str, a: float, group: str, biso: str) -> str:
        return structure(
            name, cell_lines(a, a, a), group, [f'Fe Fe 0 0 0 a 1 {biso} Biso'], system='1'
        )

    return {
        'project.edi': project_record(
            'pd-neut-tof_ferrite-austenite-beer',
            'Ferrite [Im-3m] / Austenite [Fm-3m] · BEER @ ESS',
            'Instrument calibration · 2 McStas-simulated banks fitted jointly · '
            'Per-bank zero and resolution',
            instrument='BEER',
            facility='ESS',
        ),
        'analysis/analysis.edi': analysis(
            'joint',
            weights=[('expt_s2', 0.5), ('expt_n2', 0.5)],
            aliases=[
                ('biso_ferrite', 'ferrite.atom_site.Fe.adp_iso'),
                ('biso_austenite', 'austenite.atom_site.Fe.adp_iso'),
                ('s2_ferrite_scale', 'expt_s2.linked_structure.ferrite.scale'),
                ('s2_austenite_scale', 'expt_s2.linked_structure.austenite.scale'),
                ('n2_ferrite_scale', 'expt_n2.linked_structure.ferrite.scale'),
                ('n2_austenite_scale', 'expt_n2.linked_structure.austenite.scale'),
            ],
            constraints=[
                ('1', 'biso_austenite = biso_ferrite'),
                ('2', 'n2_ferrite_scale = s2_ferrite_scale'),
                ('3', 'n2_austenite_scale = s2_austenite_scale'),
            ],
        ),
        # The two phases' cells are known; the calibration finds each bank's zero and resolution.
        'structures/ferrite.edi': iron('ferrite', 2.886, 'I m -3 m', free(BISO)),
        'structures/austenite.edi': iron('austenite', 3.6468, 'F m -3 m', str(BISO)),
        'experiments/expt_s2.edi': beer_bank('expt_s2', beer_difc('expt_s2'), scales_free=True),
        'experiments/expt_n2.edi': beer_bank('expt_n2', beer_difc('expt_n2'), scales_free=False),
    }


CASES = {
    'pd-neut-tof_si-sepd': pd_neut_tof_si_sepd,
    'pd-neut-tof_ncaf-wish': pd_neut_tof_ncaf_wish,
    'pd-neut-tof_diamond-dream_mcstas': diamond_dream,
    'pd-neut-tof_cecoal-polaris': pd_neut_tof_cecoal_polaris,
    'pd-neut-tof_ceo2-pearl': pd_neut_tof_ceo2_pearl,
    'pd-neut-tof_ferrite-austenite-beer': pd_neut_tof_ferrite_austenite_beer,
}
