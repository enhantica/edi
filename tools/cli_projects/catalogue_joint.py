# SPDX-License-Identifier: BSD-3-Clause
"""The PbSO4 case fitting the D1A neutron and laboratory X-ray patterns jointly."""

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


def pbso4_structure() -> str:
    # Pnma, coordinates of the round-robin structure rounded to two decimals.
    sites = [
        f'Pb Pb {free(0.19)} 0.25 {free(0.17)} c 1 {free(BISO)} Biso',
        f'S S {free(0.07)} 0.25 {free(0.68)} c 1 {free(BISO)} Biso',
        f'O1 O {free(0.91)} 0.25 {free(0.6)} c 1 {free(BISO)} Biso',
        f'O2 O {free(0.19)} 0.25 {free(0.54)} c 1 {free(BISO)} Biso',
        f'O3 O {free(0.08)} {free(0.03)} {free(0.81)} d 1 {free(BISO)} Biso',
    ]
    cell = cell_lines(free(8.47), free(5.39), free(6.95))
    return structure('pbso4', cell, 'P n m a', sites, system='abc')


def pbso4_d1a(rows) -> str:
    level = flat_level(rows)
    positions = [11, 15, 20, 30, 50, 70, 120, 153]
    return text(
        ['data_d1a', '', '_edi.schema_version 3'],
        [
            '_experiment_type.sample_form powder',
            '_experiment_type.beam_mode "constant wavelength"',
            '_experiment_type.radiation_probe neutron',
            '_experiment_type.scattering_type bragg',
        ],
        ['_scattering_source.neutron_scattering_length sears1992'],
        [
            '_peak.type cwl-pseudo-voigt-berar-baldinozzi',
            f'_peak.broad_gauss_u {free(0.2)}',
            f'_peak.broad_gauss_v {free(-0.5)}',
            f'_peak.broad_gauss_w {free(0.4)}',
            f'_peak.mixing_eta_0 {free(0.5)}',
            '_peak.mixing_eta_1 0',
            f'_peak.asym_beba_a0 {free(0)}',
            f'_peak.asym_beba_b0 {free(0)}',
            f'_peak.asym_beba_a1 {free(0)}',
            f'_peak.asym_beba_b1 {free(0)}',
            '_peak.asym_beba_limit 180',
            '_peak.cutoff_fwhm 30',
        ],
        [
            '_instrument.setup_wavelength 1.91',
            f'_instrument.calib_twotheta_offset {free(0)}',
        ],
        loop(
            ['_linked_structure.structure_id', '_linked_structure.scale'], [['pbso4', free(1.5)]]
        ),
        ['_background.type line-segment'],
        loop(
            ['_background.id', '_background.position', '_background.intensity'],
            [[i, x, free(level)] for i, x in enumerate(positions, 1)],
        ),
        data_loop(rows, 'two_theta'),
    )


def pbso4_lab(rows) -> str:
    excluded = [(0, 15), (160, 180)]
    level = flat_level(rows, excluded)
    return text(
        ['data_lab', '', '_edi.schema_version 3'],
        [
            '_experiment_type.sample_form powder',
            '_experiment_type.beam_mode "constant wavelength"',
            '_experiment_type.radiation_probe xray',
            '_experiment_type.scattering_type bragg',
        ],
        [
            '_scattering_source.xray_form_factor it1992',
            '_scattering_source.xray_dispersion sasaki1989',
        ],
        [
            '_peak.type cwl-pseudo-voigt-berar-baldinozzi',
            f'_peak.broad_gauss_u {free(0.02)}',
            f'_peak.broad_gauss_v {free(-0.02)}',
            f'_peak.broad_gauss_w {free(0.008)}',
            f'_peak.mixing_eta_0 {free(0.5)}',
            '_peak.mixing_eta_1 0',
            f'_peak.asym_beba_a0 {free(0)}',
            f'_peak.asym_beba_b0 {free(0)}',
            '_peak.asym_beba_a1 0',
            '_peak.asym_beba_b1 0',
            '_peak.asym_beba_limit 160',
            '_peak.cutoff_fwhm 48',
        ],
        [
            '_instrument.setup_wavelength 1.54056',
            '_instrument.setup_wavelength_2 1.5444',
            '_instrument.setup_wavelength_2_to_1_ratio 0.5',
            '_instrument.setup_polarization_coefficient 0.5',
            '_instrument.setup_monochromator_twotheta 26.5650511771',
            f'_instrument.calib_twotheta_offset {free(0)}',
        ],
        loop(
            ['_excluded_region.id', '_excluded_region.start', '_excluded_region.end'],
            [[i, lo, hi] for i, (lo, hi) in enumerate(excluded, 1)],
        ),
        loop(
            ['_linked_structure.structure_id', '_linked_structure.scale'], [['pbso4', free(0.001)]]
        ),
        ['_background.type chebyshev', '_background.x_min 15', '_background.x_max 160'],
        loop(
            ['_background.id', '_background.order', '_background.coef'],
            [[order + 1, order, free(level if order == 0 else 0)] for order in range(6)],
        ),
        data_loop(rows, 'two_theta'),
    )


def pd_neut_xray_cwl_pbso4_d1a_lab() -> dict[str, str]:
    data = CLI / 'pd-neut-xray-cwl_pbso4-d1a-lab' / 'data'
    return {
        'project.edi': project_record(
            'pd-neut-xray-cwl_pbso4-d1a-lab',
            'PbSO₄ [Pnma] · D1A @ ILL and laboratory X-ray',
            'Rietveld round-robin data · Neutron and X-ray patterns fitted jointly',
            instrument='D1A',
            facility='ILL',
            neutron=False,
        ),
        'analysis/analysis.edi': text(
            ['_edi.schema_version 3'],
            ['_fitting_mode.type joint'],
            ['_minimizer.type crysta', '_minimizer.max_iterations 1000'],
            loop(['_joint_fit.experiment_id', '_joint_fit.weight'], [['d1a', 0.5], ['lab', 0.5]]),
        ),
        'structures/pbso4.edi': pbso4_structure(),
        'experiments/d1a.edi': pbso4_d1a(read_points(data / 'pbso4-d1a.xys')),
        'experiments/lab.edi': pbso4_lab(read_points(data / 'pbso4-xray.xys')),
    }


CASES = {
    'pd-neut-xray-cwl_pbso4-d1a-lab': pd_neut_xray_cwl_pbso4_d1a_lab,
}
