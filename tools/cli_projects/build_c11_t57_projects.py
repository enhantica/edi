# SPDX-License-Identifier: BSD-3-Clause
"""Build the three CLI projects from their vendored FullProf references.

- ``pd-neut-cwl_lab6-echidna_fcj-asymmetry`` — TCH pseudo-Voigt with Finger-Cox-Jephcoat asymmetry;
- ``pd-neut-cwl_pbso4_beba-asymmetry`` — pseudo-Voigt with Bérar-Baldinozzi asymmetry;
- ``pd-neut-tof_fe_pseudo-voigt`` — the non-convoluted TOF pseudo-Voigt.

Each project carries the model FullProf computes in
``knowledge/verification/fullprof/<id>/``: the values its verification page seeds, FullProf's
background, and its data, fitted points and excluded regions. The overall scale is the ONE free
parameter, as in FullProf's authoring-time ``scale-fit`` run, so FullProf's scale and point
count are independent references for ``python -m edi fit`` (each project's
``expected.json``). Every experiment declares Sears (1992) as its neutron scattering-length source
: its real parts are FullProf's own values for these elements. The source selector is project-file
text (edi ADR-0014 §5), so each experiment's scalars are written as ``.edi`` text and its
background and data are set on the built object. Two translations are forced, and each project's
``PROVENANCE.md`` states them:

- LaB6's 6th-degree polynomial background, which edi cannot express, becomes a line-segment
  background with one anchor per FullProf ``.bac`` point;
- PbSO4's Bérar-Baldinozzi coefficients go through the map diffraction-lib issue 166 inferred
  from FullProf's output, because FullProf's P1..P4 are not the paper's coefficients.

Usage (writes ``docs/user/cli/<id>/project/``; the directory must not exist)::

    pixi run python tools/cli_projects/build_c11_t57_projects.py
"""

from __future__ import annotations

import math
import sys
from pathlib import Path

import edi

ROOT = Path(__file__).resolve().parents[2]
FULLPROF = ROOT / 'knowledge' / 'verification' / 'fullprof'
CLI = ROOT / 'docs' / 'user' / 'cli'


def read_columns(path: Path, skip: int) -> list[tuple[float, ...]]:
    """Whitespace columns after ``skip`` lines, ignoring blank lines."""
    lines = path.read_text(encoding='utf-8').splitlines()[skip:]
    return [tuple(float(field) for field in line.split()) for line in lines if line.strip()]


def pcr_background(path: Path) -> list[tuple[float, float]]:
    """The ``.pcr``'s linear-interpolation background points ``(position, height)``."""
    lines = path.read_text(encoding='latin-1').splitlines()
    first = next(i for i, line in enumerate(lines) if 'Background  for Pattern' in line) + 1
    points = []
    for line in lines[first:]:
        fields = line.split()
        if len(fields) != 3:
            break
        points.append((float(fields[0]), float(fields[1])))
    return points


def read_d1a(path: Path) -> tuple[list[float], list[float], list[float]]:
    """FullProf's D1A format (``Ins`` = 6): ten fixed-width ``(i2, f6.0)`` counter/count pairs.

    The count is the mean over its counters, so its variance is ``count / counters`` (this
    reproduces FullProf's own Rexp, 1.95, on the PbSO4 data).
    """
    lines = path.read_text(encoding='utf-8').splitlines()
    start, step = float(lines[2].split()[0]), float(lines[1].split()[2])
    counts, sigmas = [], []
    for line in lines[4:]:
        if line.strip().startswith('-'):
            break
        for column in range(0, len(line), 8):
            field = line[column : column + 8]
            if field.strip():
                counters, count = int(field[:2]), float(field[2:])
                counts.append(count)
                sigmas.append(math.sqrt(count / counters))
    two_theta = [round(start + step * index, 6) for index in range(len(counts))]
    return two_theta, counts, sigmas


def experiment_edi(
    name: str, lines: list[str], excluded, structure: str, scale: float
) -> edi.BraggPdExperiment:
    """An experiment from ``.edi`` text declaring Sears (1992) as its neutron source.

    The scalar ``lines``, the excluded regions and the linked structure with its free scale (the
    one free parameter).
    """
    rows = [f'{index} {start} {end}' for index, (start, end) in enumerate(excluded, start=1)]
    text = '\n'.join([
        f'data_{name}',
        '_edi.schema_version 3',
        '_scattering_source.neutron_scattering_length sears1992',
        *lines,
        'loop_',
        '_excluded_region.id',
        '_excluded_region.start',
        '_excluded_region.end',
        *rows,
        'loop_',
        '_linked_structure.structure_id',
        '_linked_structure.scale',
        f'{structure} {scale}()',
        '',
    ])
    return edi.ExperimentFactory.from_cif_str(text)


def line_background(points) -> list:
    """Line-segment background anchors ``(position, height)``, fixed."""
    anchors = []
    for position, height in points:
        anchor = edi.LineSegment()
        anchor.position = float(position)
        anchor.intensity = edi.Parameter(float(height))
        anchors.append(anchor)
    return anchors


def pbso4_structure() -> edi.Structure:
    return edi.StructureFactory.from_dict({
        'name': 'pbso4',
        'space_group': {'name_h_m': 'P n m a'},
        'cell': {'length_a': 8.479506, 'length_b': 5.397256, 'length_c': 6.958973},
        'atom_sites': [
            {
                'id': site,
                'type_symbol': symbol,
                'wyckoff_letter': wyckoff,
                'fract': fract,
                'occupancy': 1.0,
                'adp_iso': adp,
            }
            for site, symbol, wyckoff, fract, adp in (
                ('Pb', 'Pb', 'c', (0.18752, 0.25, 0.16705), 1.39017),
                ('S', 'S', 'c', (0.06549, 0.25, 0.68373), 0.39270),
                ('O1', 'O', 'c', (0.90816, 0.25, 0.59544), 1.99307),
                ('O2', 'O', 'c', (0.19355, 0.25, 0.54331), 1.47771),
                ('O3', 'O', 'd', (0.08109, 0.02727, 0.80869), 1.30007),
            )
        ],
    })


def lab6() -> edi.Project:
    reference = FULLPROF / 'pd-neut-cwl_lab6-echidna_fcj-asymmetry'
    zero = -0.45778
    structure = edi.StructureFactory.from_dict({
        'name': 'lab6',
        'space_group': {'name_h_m': 'P m -3 m'},
        'cell': {'length_a': 4.156885},
        'atom_sites': [
            {
                'id': 'La',
                'type_symbol': 'La',
                'wyckoff_letter': 'a',
                'fract': (0.0, 0.0, 0.0),
                'adp_iso': 0.25812,
            },
            {
                'id': 'B',
                'type_symbol': 'B',
                'wyckoff_letter': 'f',
                'fract': (0.19972, 0.5, 0.5),
                'adp_iso': 0.11925,
            },
        ],
    })
    # The .bac is on FullProf's zero-corrected axis; the anchors sit on the native one.
    background = [
        (round(x + zero, 6), y)
        for x, y in read_columns(reference / 'ECH0030684_LaB6_1p622A_fcj.bac', skip=1)
    ]
    experiment = experiment_edi(
        'echidna',
        [
            '_experiment_type.beam_mode "constant wavelength"',
            '_peak.type cwl-tch-pseudo-voigt-fcj',
            '_peak.cutoff_fwhm 12.0',
            '_peak.broad_gauss_u 0.143431',
            '_peak.broad_gauss_v -0.523140',
            '_peak.broad_gauss_w 0.590412',
            '_peak.broad_lorentz_x 0.0',
            '_peak.broad_lorentz_y 0.054515',
            '_peak.asym_fcj_1 0.08',
            '_peak.asym_fcj_2 0.08',
            '_instrument.setup_wavelength 1.623899',
            f'_instrument.calib_twotheta_offset {zero}',
        ],
        # The .pcr excluded regions, the upper one from its 2Thmax 163.756378: edi has no range,
        # and the file's last point (163.75638) lies just above it, so FullProf does not fit it.
        # FullProf also reads the first six rows as comments, all of them below 10 deg.
        [(0.0, 10.0), (163.756378, 180.0)],
        'lab6',
        42.98374,
    )
    experiment.background = line_background(background)
    rows = read_columns(reference / 'ECH0030684_LaB6_1p622A_fcj.dat', skip=0)
    experiment.data = edi.PdCwlData(
        two_theta=[row[0] for row in rows],
        intensity_meas=[row[1] for row in rows],
        intensity_meas_su=[row[2] for row in rows],
    )
    return project(
        'pd_neut_cwl_lab6_echidna_fcj',
        'LaB6, Echidna (ANSTO), FCJ asymmetry',
        structure,
        experiment,
    )


def pbso4() -> edi.Project:
    reference = FULLPROF / 'pd-neut-cwl_pbso4_beba-asymmetry'
    p1, p2, p3, p4 = 0.29465, 0.02261, -0.10961, 0.04941  # the .pcr's Asy1..Asy4
    experiment = experiment_edi(
        'd1a',
        [
            '_experiment_type.beam_mode "constant wavelength"',
            '_peak.type cwl-pseudo-voigt-berar-baldinozzi-asymmetry',
            '_peak.cutoff_fwhm 30.0',
            '_peak.broad_gauss_u 0.153402',
            '_peak.broad_gauss_v -0.453103',
            '_peak.broad_gauss_w 0.419409',
            '_peak.broad_lorentz_x 0.0',
            '_peak.broad_lorentz_y 0.086818',
            # diffraction-lib issue 166's inferred map from FullProf's P1..P4.
            f'_peak.asym_beba_a0 {round(-p1 - 3.0 * p2, 6)}',
            f'_peak.asym_beba_b0 {-p2}',
            f'_peak.asym_beba_a1 {round(-p3 - 3.0 * p4, 6)}',
            f'_peak.asym_beba_b1 {-p4}',
            '_peak.asym_beba_limit 180.0',
            '_instrument.setup_wavelength 1.912',
            '_instrument.calib_twotheta_offset -0.08424',
        ],
        # The .pcr excluded regions 0-10 and 155.45-180; FullProf fits 10.00 deg, which edi's
        # inclusive bound would drop, so the lower one stops just short of it.
        [(0.0, 9.99), (155.45, 180.0)],
        'pbso4',
        1.463815,
    )
    experiment.background = line_background(pcr_background(reference / 'pbso4.pcr'))
    two_theta, counts, sigmas = read_d1a(reference / 'pbso4.dat')
    experiment.data = edi.PdCwlData(
        two_theta=two_theta, intensity_meas=counts, intensity_meas_su=sigmas
    )
    return project(
        'pd_neut_cwl_pbso4_beba',
        'PbSO4, D1A (ILL), Berar-Baldinozzi asymmetry',
        pbso4_structure(),
        experiment,
    )


def fe() -> edi.Project:
    reference = FULLPROF / 'pd-neut-tof_fe_pseudo-voigt'
    structure = edi.StructureFactory.from_dict({
        'name': 'fe',
        'space_group': {'name_h_m': 'I m -3 m'},
        'cell': {'length_a': 2.886},
        'atom_sites': [
            {
                'id': 'Fe',
                'type_symbol': 'Fe',
                'wyckoff_letter': 'a',
                'fract': (0.0, 0.0, 0.0),
                'adp_iso': 1.71513,
            },
        ],
    })
    experiment = experiment_edi(
        'beer',
        [
            '_peak.type tof-pseudo-voigt',
            '_peak.cutoff_fwhm 12.0',
            '_peak.broad_gauss_sigma_0 893.6397',
            '_peak.broad_gauss_sigma_1 1283.6387',
            '_peak.broad_gauss_sigma_2 311.7041',
            '_peak.broad_lorentz_gamma_0 5.033',
            '_peak.broad_lorentz_gamma_1 0.0',
            '_peak.broad_lorentz_gamma_2 0.0',
            '_instrument.calib_d_to_tof_offset -10.29183',
            '_instrument.calib_d_to_tof_linear 54902.1875',
            '_instrument.calib_d_to_tof_quadratic 0.0',
            '_instrument.setup_twotheta_bank 90.0',
        ],
        # The .pcr excluded regions; its TOF range starts at the first row FullProf reads.
        [(20000.0, 40000.0), (130000.0, 180000.0)],
        'fe',
        401.4629,
    )
    experiment.background = line_background(pcr_background(reference / 'fe.pcr'))
    # FullProf reads the first six lines as comments: the four '#' lines and two data rows, so
    # the set starts at its TOF-min. One excluded row (134955 us) has zero sigma, which edi
    # refuses; it takes edi's own loader rule (ExperimentFactory.from_data_path: below 1e-4 -> 1).
    rows = read_columns(reference / 'fe.dat', skip=6)
    experiment.data = edi.PdTofData(
        time_of_flight=[row[0] for row in rows],
        intensity_meas=[row[1] for row in rows],
        intensity_meas_su=[row[2] if row[2] >= 1e-4 else 1.0 for row in rows],
    )
    return project(
        'pd_neut_tof_fe_pseudo_voigt',
        'Fe (ferrite), BEER (ESS), TOF pseudo-Voigt',
        structure,
        experiment,
    )


def project(name: str, title: str, structure, experiment) -> edi.Project:
    result = edi.Project()
    result.metadata.name = name
    result.metadata.title = title
    result.structure = structure
    result.experiment = experiment
    return result


BUILDERS = {
    'pd-neut-cwl_lab6-echidna_fcj-asymmetry': lab6,
    'pd-neut-cwl_pbso4_beba-asymmetry': pbso4,
    'pd-neut-tof_fe_pseudo-voigt': fe,
}


def main() -> int:
    for project_id, build in BUILDERS.items():
        target = CLI / project_id / 'project'
        if target.exists():
            print(f'refusing: {target} exists; remove it to rebuild', file=sys.stderr)
            return 1
        build().save_as(str(target))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
