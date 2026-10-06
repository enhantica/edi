# SPDX-License-Identifier: BSD-3-Clause
"""Build the YAP CLI project from the owner's FullProf project.

``pd-neut-cwl_yap-spodi_3k``: YAlO3 and Al2O3 on SPODI (FRM II), two phases in one
constant-wavelength neutron pattern. The model is the one FullProf fits in
``knowledge/fitting/fullprof/pd-neut-cwl_yap-spodi_3k/yap_3k.pcr``: the pseudo-Voigt with
Bérar-Baldinozzi asymmetry (FullProf's Npr 5), shared by both phases, a constant mixing (FullProf's
X slope fixed at 0), AsyLim 160°, the cylinder absorption muR 0.0221, 25 background points and two
excluded regions. Every parameter FullProf refines is free here (56) and starts at the committed
``.pcr`` value, which is FullProf's converged result. Occupancies follow the ``.pcr``'s convention
(Occ = occupancy x site multiplicity / general multiplicity), so every site is fully occupied.

FullProf's Asy1..Asy4 are not the paper's coefficients: they go through the map diffraction-lib
issue 166 inferred, ``(-P1 - 3 P2, -P2, -P3 - 3 P4, -P4)``, as starting values only.

Usage (writes ``docs/user/cli/pd-neut-cwl_yap-spodi_3k/project/``; the directory must not exist)::

    pixi run python tools/cli_projects/build_yap_project.py
"""

from __future__ import annotations

import sys
from pathlib import Path

import edi

ROOT = Path(__file__).resolve().parents[2]
REFERENCE = ROOT / 'knowledge' / 'fitting' / 'fullprof' / 'pd-neut-cwl_yap-spodi_3k'
TARGET = ROOT / 'docs' / 'user' / 'cli' / 'pd-neut-cwl_yap-spodi_3k' / 'project'

# (id, type, Wyckoff letter, (x, y, z), Biso, the free coordinates) from the .pcr.
YALO3_SITES = [
    ('Y', 'Y', 'c', (0.01241, 0.55406, 0.25), 0.11810, 'xy'),
    ('Al', 'Al', 'a', (0.0, 0.0, 0.0), 0.12582, ''),
    ('O1', 'O', 'c', (-0.08385, -0.02195, 0.25), 0.05559, 'xy'),
    ('O2', 'O', 'd', (0.20470, 0.29483, 0.04427), 0.13975, 'xyz'),
]
AL2O3_SITES = [
    ('Al1', 'Al', 'c', (0.0, 0.0, 0.33349), -0.13591, 'z'),
    ('O1', 'O', 'e', (0.34993, 0.0, 0.25), 1.24078, 'x'),
]
ASY = (0.21542, 0.00305, -0.27811, 0.05563)  # the .pcr's Asy1..Asy4, FullProf's convention


def free(value: float) -> str:
    return f'{value}()'


def structure(name: str, group: str, cell: list[str], sites, *, hexagonal: bool = False) -> str:
    lines = [f'data_{name}', '_edi.schema_version 3', *cell]
    lines.append(f'_space_group.name_h_m "{group}"')
    if hexagonal:
        lines.append('_space_group.coord_system_code h')
    lines += [
        'loop_',
        '_atom_site.id',
        '_atom_site.type_symbol',
        '_atom_site.wyckoff_letter',
        '_atom_site.fract_x',
        '_atom_site.fract_y',
        '_atom_site.fract_z',
        '_atom_site.occupancy',
        '_atom_site.adp_iso',
        '_atom_site.adp_type',
    ]
    for site, symbol, letter, xyz, biso, moving in sites:
        coords = [
            free(v) if axis in moving else str(v) for axis, v in zip('xyz', xyz, strict=True)
        ]
        lines.append(f'{site} {symbol} {letter} {" ".join(coords)} 1 {free(biso)} Biso')
    return '\n'.join(lines) + '\n'


def background() -> list[tuple[str, str]]:
    """The .pcr's 25 background points (position, height), all refined there."""
    text = (REFERENCE / 'yap_3k.pcr').read_text()
    block = text.split('Background  for Pattern#  1')[1].split('! Excluded regions')[0]
    rows = [line.split() for line in block.splitlines()[1:] if line.strip() and line[0] != '!']
    return [(row[0], row[1]) for row in rows]


def data() -> list[str]:
    """The points FullProf fits (2theta 4.05 to 151.95; Ins 10, x y sigma).

    FullProf reads from 2.3 but excludes everything below 4, where the counts and their sigmas are
    zero; edi refuses a zero sigma, so those points are left out rather than carried excluded.
    """
    rows = []
    for line in (REFERENCE / 'yap_3k.dat').read_text().splitlines():
        x, y, sigma = line.split()
        if 4.05 <= float(x) <= 151.95:
            rows.append(f'{x} {y} {sigma}')
    return rows


def experiment() -> str:
    p1, p2, p3, p4 = ASY
    lines = [
        'data_spodi',
        '_edi.schema_version 3',
        '_experiment_type.beam_mode "constant wavelength"',
        '_scattering_source.neutron_scattering_length sears1992',
        '_instrument.setup_wavelength 1.54816',
        f'_instrument.calib_twotheta_offset {free(0.00146)}',
        '_peak.type cwl-pseudo-voigt-berar-baldinozzi',
        '_peak.cutoff_fwhm 20',
        f'_peak.broad_gauss_u {free(0.038892)}',
        f'_peak.broad_gauss_v {free(-0.0462)}',
        f'_peak.broad_gauss_w {free(0.10586)}',
        f'_peak.mixing_eta_0 {free(0.12522)}',
        '_peak.mixing_eta_1 0',
        f'_peak.asym_beba_a0 {free(round(-p1 - 3.0 * p2, 6))}',
        f'_peak.asym_beba_b0 {free(-p2)}',
        f'_peak.asym_beba_a1 {free(round(-p3 - 3.0 * p4, 6))}',
        f'_peak.asym_beba_b1 {free(-p4)}',
        '_peak.asym_beba_limit 160',
        '_absorption.type cylinder-hewat',
        '_absorption.mu_r 0.0221',
        'loop_',
        '_linked_structure.structure_id',
        '_linked_structure.scale',
        f'YAlO3 {free(27.89648)}',
        f'Al2O3 {free(0.1887676)}',
        '',
        '_background.type line-segment',
        'loop_',
        '_background.id',
        '_background.position',
        '_background.intensity',
        *(f'{i} {pos} {free(float(height))}' for i, (pos, height) in enumerate(background(), 1)),
        '',
        'loop_',
        '_excluded_region.id',
        '_excluded_region.start',
        '_excluded_region.end',
        '1 0 4',
        '2 153.95 180',
        '',
        'loop_',
        '_data.two_theta',
        '_data.intensity_meas',
        '_data.intensity_meas_su',
        *data(),
    ]
    return '\n'.join(lines) + '\n'


def main() -> int:
    if TARGET.exists():
        print(f'refusing: {TARGET} exists; remove it to rebuild', file=sys.stderr)
        return 1
    (TARGET / 'structures').mkdir(parents=True)
    (TARGET / 'experiments').mkdir()
    (TARGET / 'analysis').mkdir()
    (TARGET / 'project.edi').write_text(
        '_edi.schema_version 3\n_metadata.name pd_neut_cwl_yap_spodi_3k\n'
        '_metadata.title "YAlO3 and Al2O3, SPODI (FRM II), two phases"\n'
    )
    cell = [
        f'_cell.length_a {free(5.172418)}',
        f'_cell.length_b {free(5.32659)}',
        f'_cell.length_c {free(7.360847)}',
        '_cell.angle_alpha 90',
        '_cell.angle_beta 90',
        '_cell.angle_gamma 90',
    ]
    (TARGET / 'structures' / 'YAlO3.edi').write_text(
        structure('YAlO3', 'P b n m', cell, YALO3_SITES)
    )
    cell = [
        f'_cell.length_a {free(4.756614)}',
        '_cell.length_b 4.756614',
        f'_cell.length_c {free(12.973036)}',
        '_cell.angle_alpha 90',
        '_cell.angle_beta 90',
        '_cell.angle_gamma 120',
    ]
    (TARGET / 'structures' / 'Al2O3.edi').write_text(
        structure('Al2O3', 'R -3 c', cell, AL2O3_SITES, hexagonal=True)
    )
    (TARGET / 'experiments' / 'spodi.edi').write_text(experiment())
    (TARGET / 'analysis' / 'analysis.edi').write_text(
        '_edi.schema_version 3\n_minimizer.max_iterations 150\n'
        '_minimizer.chi_square_tolerance 1e-8\n'
    )
    edi.Project.load(str(TARGET))  # the loader's refusals, before anything is kept
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
