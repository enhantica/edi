# SPDX-License-Identifier: BSD-3-Clause
"""Four cases new to edi, from diffraction-lib tutorials.

HS on HRPT, LMO on ECHIDNA, LaM(7)O3 on P02.1, and LBCO with a Si impurity in a McStas TOF
simulation.
"""

from __future__ import annotations

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


def experiment_type(beam_mode: str, probe: str) -> list[str]:
    return [
        '_experiment_type.sample_form powder',
        f'_experiment_type.beam_mode "{beam_mode}"',
        f'_experiment_type.radiation_probe {probe}',
        '_experiment_type.scattering_type bragg',
    ]


def excluded_loop(regions) -> list[str]:
    return loop(
        ['_excluded_region.id', '_excluded_region.start', '_excluded_region.end'],
        [[i, lo, hi] for i, (lo, hi) in enumerate(regions, 1)],
    )


def flat_points(positions, level) -> list[str]:
    return loop(
        ['_background.id', '_background.position', '_background.intensity'],
        [[i, x, free(level)] for i, x in enumerate(positions, 1)],
    )


def aliases_and_constraints(aliases, constraints) -> list[str]:
    return [
        *loop(['_alias.id', '_alias.parameter_unique_name'], [list(a) for a in aliases]),
        '',
        *loop(
            ['_constraint.id', '_constraint.expression'],
            [[i, f'"{expression}"'] for i, expression in enumerate(constraints, 1)],
        ),
    ]


# ----------------------------------------------------------------------
#  HS (herbertsmithite) on HRPT
# ----------------------------------------------------------------------


def pd_neut_cwl_hs_hrpt_basic() -> dict[str, str]:
    pid = 'pd-neut-cwl_hs-hrpt_basic'
    rows = read_points(CLI / pid / 'data' / 'hs-hrpt.xye')
    level = flat_level(rows)
    # R-3m, hexagonal axes; O and H on 18h (x, -x, z), Cl on 6c (0, 0, z).
    sites = [
        f'Zn Zn 0 0 0.5 b 1 {free(BISO)} Biso',
        f'Cu Cu 0.5 0 0 e 1 {free(BISO)} Biso',
        f'O O {free(0.21)} -0.21 {free(0.06)} h 1 {free(BISO)} Biso',
        f'Cl Cl 0 0 {free(0.2)} c 1 {free(BISO)} Biso',
        f'H 2H {free(0.13)} -0.13 {free(0.08)} h 1 {free(BISO)} Biso',
    ]
    cell = cell_lines(free(6.85), 6.85, free(14.1), gamma=120)
    background = [4, 20, 40, 60, 80, 100, 120, 140, 160, 165]
    hrpt = text(
        ['data_hrpt', '', '_edi.schema_version 3'],
        experiment_type('constant wavelength', 'neutron'),
        ['_scattering_source.neutron_scattering_length sears1992'],
        [
            '_peak.type cwl-pseudo-voigt-berar-baldinozzi',
            f'_peak.broad_gauss_u {free(0.1)}',
            f'_peak.broad_gauss_v {free(-0.2)}',
            f'_peak.broad_gauss_w {free(0.2)}',
            f'_peak.mixing_eta_0 {free(0.5)}',
            '_peak.mixing_eta_1 0',
            f'_peak.asym_beba_a0 {free(0)}',
            f'_peak.asym_beba_b0 {free(0)}',
            f'_peak.asym_beba_a1 {free(0)}',
            f'_peak.asym_beba_b1 {free(0)}',
            '_peak.asym_beba_limit 180',
            '_peak.cutoff_fwhm 8',
        ],
        ['_instrument.setup_wavelength 1.89', f'_instrument.calib_twotheta_offset {free(0)}'],
        loop(['_linked_structure.structure_id', '_linked_structure.scale'], [['hs', free(0.5)]]),
        ['_background.type line-segment'],
        flat_points(background, level),
        data_loop(rows, 'two_theta'),
    )
    return {
        'project.edi': project_record(
            'pd_neut_cwl_hs_hrpt_basic',
            'ZnCu₃(OD)₆Cl₂ [R-3m] · HRPT @ PSI',
            'Herbertsmithite · Deuterated kagome antiferromagnet · Bérar-Baldinozzi asymmetry',
            instrument='HRPT',
            facility='PSI',
        ),
        'analysis/analysis.edi': text(
            ['_edi.schema_version 3'],
            ['_fitting_mode.type single'],
            ['_minimizer.type crysta', '_minimizer.max_iterations 1000'],
        ),
        'structures/hs.edi': structure('hs', cell, 'R -3 m', sites, system='h'),
        'experiments/hrpt.edi': hrpt,
    }


# ----------------------------------------------------------------------
#  LMO on ECHIDNA: Li/Ni site mixing
# ----------------------------------------------------------------------


def pd_neut_cwl_lmo_echidna_site_mixing() -> dict[str, str]:
    pid = 'pd-neut-cwl_lmo-echidna_site-mixing'
    rows = read_points(CLI / pid / 'data' / 'ech_lmo.dat')
    excluded = [(0, 12), (162, 180)]
    level = flat_level(rows, excluded)
    # R-3m, hexagonal axes: the Li layer at 3b (0, 0, 1/2) and the metal layer at 3a (0, 0, 0),
    # each holding some of the other cation. The start is the fully ordered structure.
    sites = [
        f'O O 0 0 {free(0.26)} c 1 {free(BISO)} Biso',
        f'Ni1 Ni 0 0 0.5 b 0 {BISO} Biso',
        f'Li1 Li 0 0 0.5 b {free(1)} {free(BISO)} Biso',
        f'Li2 Li 0 0 0 a 0 {BISO} Biso',
        f'Ni2 Ni 0 0 0 a 1 {free(BISO)} Biso',
    ]
    cell = cell_lines(free(2.88), 2.88, free(14.18), gamma=120)
    background = [12, 30, 50, 70, 90, 110, 130, 150, 162]
    echidna = text(
        ['data_echidna', '', '_edi.schema_version 3'],
        experiment_type('constant wavelength', 'neutron'),
        ['_scattering_source.neutron_scattering_length sears1992'],
        [
            '_peak.type cwl-tch-pseudo-voigt-fcj',
            f'_peak.broad_gauss_u {free(0.1)}',
            f'_peak.broad_gauss_v {free(-0.3)}',
            f'_peak.broad_gauss_w {free(0.4)}',
            '_peak.broad_lorentz_x 0',
            f'_peak.broad_lorentz_y {free(0.1)}',
            # The axial-divergence geometry (S/L, H/L) is the instrument's, fixed as in the
            # tutorial: started at 0 and free, no trial step from it can be evaluated.
            '_peak.asym_fcj_1 0.08',
            '_peak.asym_fcj_2 0.08',
            '_peak.cutoff_fwhm 12',
        ],
        [
            '_instrument.setup_wavelength 1.6215',
            f'_instrument.calib_twotheta_offset {free(0)}',
            f'_instrument.calib_sample_displacement {free(0)}',
            f'_instrument.calib_sample_transparency {free(0)}',
        ],
        ['_absorption.type cylinder-hewat', '_absorption.mu_r 0.3'],
        excluded_loop(excluded),
        loop(['_linked_structure.structure_id', '_linked_structure.scale'], [['lmo', free(10)]]),
        ['_background.type line-segment'],
        flat_points(background, level),
        data_loop(rows, 'two_theta'),
    )
    analysis = text(
        ['_edi.schema_version 3'],
        ['_fitting_mode.type single'],
        ['_minimizer.type crysta', '_minimizer.max_iterations 1000'],
        aliases_and_constraints(
            [
                ('biso_Li1', 'lmo.atom_site.Li1.adp_iso'),
                ('biso_Li2', 'lmo.atom_site.Li2.adp_iso'),
                ('biso_Ni1', 'lmo.atom_site.Ni1.adp_iso'),
                ('biso_Ni2', 'lmo.atom_site.Ni2.adp_iso'),
                ('occ_Li1', 'lmo.atom_site.Li1.occupancy'),
                ('occ_Li2', 'lmo.atom_site.Li2.occupancy'),
                ('occ_Ni1', 'lmo.atom_site.Ni1.occupancy'),
                ('occ_Ni2', 'lmo.atom_site.Ni2.occupancy'),
            ],
            [
                'biso_Ni1 = biso_Li1',
                'biso_Li2 = biso_Ni2',
                'occ_Ni1 = 1 - occ_Li1',
                'occ_Li2 = 1 - occ_Li1',
                'occ_Ni2 = occ_Li1',
            ],
        ),
    )
    return {
        'project.edi': project_record(
            'pd_neut_cwl_lmo_echidna_site_mixing',
            'LiNiO₂ [R-3m] · ECHIDNA @ ANSTO',
            'Layered oxide · Li/Ni site mixing · Occupancy constraints · '
            'TCH \N{MULTIPLICATION SIGN} FCJ asymmetry',
            instrument='ECHIDNA',
            facility='ANSTO',
        ),
        'analysis/analysis.edi': analysis,
        'structures/lmo.edi': structure('lmo', cell, 'R -3 m', sites, system='h'),
        'experiments/echidna.edi': echidna,
    }


# ----------------------------------------------------------------------
#  LaM(7)O3 on P02.1: seven B-site cations sharing one site
# ----------------------------------------------------------------------

B_CATIONS = ['Ti', 'Cr', 'Mn', 'Fe', 'Co', 'Ni', 'Cu']


def pd_xray_cwl_lam7o3_p021_basic() -> dict[str, str]:
    pid = 'pd-xray-cwl_lam7o3-p021_basic'
    rows = read_points(CLI / pid / 'data' / 'hep7c-xray-synchrotron.dat')
    excluded = [(0, 2), (15, 20)]
    level = flat_level(rows, excluded)
    # Pnma: La and O1 on 4c (x, 1/4, z), the B site on 4a (0, 0, 0), O2 on 8d. Only Ti's
    # displacement is free on the B site; the other six follow it.
    sites = [
        f'La La {free(0.48)} 0.25 {free(0.0)} c 1 {free(BISO)} Biso',
        *(f'{m} {m} 0 0 0 a 0.14286 {free(BISO) if m == "Ti" else BISO} Biso' for m in B_CATIONS),
        f'O1 O {free(0.51)} 0.25 {free(0.57)} c 1 {free(BISO)} Biso',
        f'O2 O {free(0.22)} {free(0.03)} {free(0.27)} d 1 {BISO} Biso',
    ]
    cell = cell_lines(free(5.5), free(7.7), free(5.5))
    # A point every 0.25°, as dense as diffraction-lib's estimated background: the capillary and air
    # scattering under the first peaks is not a smooth curve.
    background = [round(2 + 0.25 * i, 2) for i in range(53)]
    p021 = text(
        ['data_p021', '', '_edi.schema_version 3'],
        experiment_type('constant wavelength', 'xray'),
        [
            '_scattering_source.xray_form_factor it1992',
            '_scattering_source.xray_dispersion sasaki1989',
        ],
        [
            '_peak.type cwl-tch-pseudo-voigt',
            f'_peak.broad_gauss_u {free(0.04)}',
            f'_peak.broad_gauss_v {free(-0.01)}',
            f'_peak.broad_gauss_w {free(0.001)}',
            f'_peak.broad_lorentz_x {free(0.1)}',
            '_peak.broad_lorentz_y 0',
            '_peak.cutoff_fwhm 30',
        ],
        ['_instrument.setup_wavelength 0.207109', f'_instrument.calib_twotheta_offset {free(0)}'],
        excluded_loop(excluded),
        loop(
            ['_linked_structure.structure_id', '_linked_structure.scale'],
            [['lam7o3', free('0.000005')]],
        ),
        ['_background.type line-segment'],
        flat_points(background, level),
        data_loop(rows, 'two_theta'),
    )
    aliases = [(f'biso_{m}', f'lam7o3.atom_site.{m}.adp_iso') for m in B_CATIONS]
    aliases += [
        ('biso_O1', 'lam7o3.atom_site.O1.adp_iso'),
        ('biso_O2', 'lam7o3.atom_site.O2.adp_iso'),
    ]
    constraints = [f'biso_{m} = biso_Ti' for m in B_CATIONS[1:]] + ['biso_O2 = biso_O1']
    return {
        'project.edi': project_record(
            'pd_xray_cwl_lam7o3_p021_basic',
            'La(Ti,Cr,Mn,Fe,Co,Ni,Cu)O₃ [Pnma] · P02.1 @ PETRA III',
            'High-entropy perovskite · Seven cations on one site · Synchrotron X-ray',
            instrument='P02.1',
            facility='PETRA III',
            neutron=False,
        ),
        'analysis/analysis.edi': text(
            ['_edi.schema_version 3'],
            ['_fitting_mode.type single'],
            ['_minimizer.type crysta', '_minimizer.max_iterations 1000'],
            aliases_and_constraints(aliases, constraints),
        ),
        'structures/lam7o3.edi': structure('lam7o3', cell, 'P n m a', sites, system='abc'),
        'experiments/p021.edi': p021,
    }


# ----------------------------------------------------------------------
#  LBCO with a Si impurity: a McStas TOF simulation
# ----------------------------------------------------------------------


def pd_neut_tof_lbco_si_mcstas_two_phase() -> dict[str, str]:
    pid = 'pd-neut-tof_lbco-si-mcstas_two-phase'
    rows = read_points(CLI / pid / 'data' / 'lbco-si-mcstas.xye')
    excluded = [(0, 40000), (108000, 200000)]
    level = flat_level(rows, excluded)
    # The A-site and the minor Si phase keep their displacement fixed, as the tutorial has them:
    # freed with Co's, they trade off against it and the fit lands far from the minimum.
    lbco_sites = [
        f'La La 0 0 0 a 0.5 {BISO} Biso',
        f'Ba Ba 0 0 0 a 0.5 {BISO} Biso',
        f'Co Co 0.5 0.5 0.5 b 1 {free(BISO)} Biso',
        f'O O 0 0.5 0.5 c 1 {free(BISO)} Biso',
    ]
    si_sites = [f'Si Si 0 0 0 a 1 {BISO} Biso']
    background = [45000, 50000, 55000, *range(65000, 110001, 5000)]
    mcstas = text(
        ['data_mcstas', '', '_edi.schema_version 3'],
        experiment_type('time-of-flight', 'neutron'),
        ['_scattering_source.neutron_scattering_length sears1992'],
        [
            '_peak.type tof-jorgensen',
            f'_peak.broad_gauss_sigma_0 {free(50000)}',
            f'_peak.broad_gauss_sigma_1 {free(-50000)}',
            f'_peak.broad_gauss_sigma_2 {free(20000)}',
            '_peak.rise_alpha_0 0',
            f'_peak.rise_alpha_1 {free(0.01)}',
            f'_peak.decay_beta_0 {free(0.006)}',
            f'_peak.decay_beta_1 {free(0.004)}',
            '_peak.broad_gauss_size 0',
            '_peak.broad_gauss_strain 0',
            '_peak.broad_lorentz_gamma_0 0',
            '_peak.broad_lorentz_gamma_1 0',
            '_peak.broad_lorentz_gamma_2 0',
            '_peak.broad_lorentz_size 0',
            '_peak.broad_lorentz_strain 0',
            '_peak.cutoff_fwhm 30',
        ],
        [
            '_instrument.setup_twotheta_bank 94.90931761529106',
            '_instrument.calib_d_to_tof_offset 0',
            '_instrument.calib_d_to_tof_linear 58724.76869981215',
            '_instrument.calib_d_to_tof_quadratic 0',
            '_instrument.calib_d_to_tof_reciprocal 0',
        ],
        excluded_loop(excluded),
        loop(
            ['_linked_structure.structure_id', '_linked_structure.scale'],
            [['lbco', free(4)], ['si', free(0.2)]],
        ),
        ['_background.type line-segment'],
        flat_points(background, level),
        data_loop(rows, 'time_of_flight'),
    )
    return {
        'project.edi': project_record(
            'pd_neut_tof_lbco_si_mcstas_two_phase',
            'La₀.₅Ba₀.₅CoO₃ [Pm-3m] / Silicon [Fd-3m] · McStas simulation',
            'Two phases · Simulated TOF pattern · Jorgensen profile',
            instrument='McStas',
        ),
        'analysis/analysis.edi': text(
            ['_edi.schema_version 3'],
            ['_fitting_mode.type single'],
            ['_minimizer.type crysta', '_minimizer.max_iterations 1000'],
        ),
        'structures/lbco.edi': structure(
            'lbco', cell_lines(free(3.8909), 3.8909, 3.8909), 'P m -3 m', lbco_sites, system='1'
        ),
        'structures/si.edi': structure(
            'si', cell_lines(free(5.43), 5.43, 5.43), 'F d -3 m', si_sites, system='1'
        ),
        'experiments/mcstas.edi': mcstas,
    }


CASES = {
    'pd-neut-cwl_hs-hrpt_basic': pd_neut_cwl_hs_hrpt_basic,
    'pd-neut-cwl_lmo-echidna_site-mixing': pd_neut_cwl_lmo_echidna_site_mixing,
    'pd-xray-cwl_lam7o3-p021_basic': pd_xray_cwl_lam7o3_p021_basic,
    'pd-neut-tof_lbco-si-mcstas_two-phase': pd_neut_tof_lbco_si_mcstas_two_phase,
}
