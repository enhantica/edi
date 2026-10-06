# SPDX-License-Identifier: BSD-3-Clause
"""Build the `pd-neut-cwl_y2o3_beta-adp` CLI project from its vendored FullProf reference.

The project carries the model of ``knowledge/verification/fullprof/pd-neut-cwl_y2o3_beta-adp/``,
the values the ``pd-neut-cwl_Y2O3_beta-adp`` verification page seeds: Y2O3 in ``I a -3`` with
every site's displacement given as FullProf's dimensionless beta tensor (``adp_type beta``), the
``.pcr``'s background points and excluded regions, and FullProf's data (``y2o3.dat``). The overall
scale is the ONE free parameter, as in FullProf's authoring-time scale fit
(``fullprof/scale-fit.inp`` beside the project), so FullProf's fitted scale and point count are
independent references for ``python -m edi fit`` (the project's ``expected.json``).

Usage (the first writes ``docs/user/cli/pd-neut-cwl_y2o3_beta-adp/project/`` and refuses an
existing directory; the second writes ``expected.json`` from ``<record>``, the machine record of
``python -m edi fit <project> --dry --report machine --verbosity full``)::

    pixi run python tools/cli_projects/build_pd_neut_cwl_y2o3_beta_adp.py
    pixi run python tools/cli_projects/build_pd_neut_cwl_y2o3_beta_adp.py --expected <record>
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import edi

ROOT = Path(__file__).resolve().parents[2]
REFERENCE = ROOT / 'knowledge' / 'verification' / 'fullprof' / 'pd-neut-cwl_y2o3_beta-adp'
HOME = ROOT / 'docs' / 'user' / 'cli' / 'pd-neut-cwl_y2o3_beta-adp'
TARGET = HOME / 'project'

# fullprof/scale-fit.out: the converged overall scale and its standard uncertainty, and the
# points FullProf fitted (N-P+C 2508 plus the one free parameter).
FULLPROF_SCALE = (0.12779339, 0.65268698e-03)
FULLPROF_POINTS = 2509

# y2o3.pcr: Atom, Typ, Wyckoff, (X, Y, Z); every site fully occupied (the .pcr's Occ 0.5, 0.16667
# and 1.0 are site occupancy x site multiplicity / general multiplicity).
SITES = [
    ('Y1', 'Y', 'd', (-0.03236, 0.0, 0.25)),
    ('Y2', 'Y', 'b', (0.25, 0.25, 0.25)),
    ('O1', 'O', 'e', (0.39072, 0.15204, 0.38030)),
]
# y2o3.pcr: beta11, beta22, beta33, beta12, beta13, beta23.
BETAS = {
    'Y1': (0.00303, 0.00272, 0.00295, 0.0, 0.0, -0.00025),
    'Y2': (0.00304, 0.00304, 0.00304, -0.00013, -0.00013, -0.00013),
    'O1': (0.00299, 0.00310, 0.00273, -0.00007, -0.00020, -0.00001),
}
COMPONENTS = ('adp_11', 'adp_22', 'adp_33', 'adp_12', 'adp_13', 'adp_23')

# The experiment as project-file text (the scattering-length source is file text, edi ADR-0014
# section 5). The .pcr's excluded regions; edi's bounds are inclusive and FullProf fits neither
# 12.00 nor 137.50 deg, so the two regions keep exactly FullProf's points.
EXPERIMENT = """data_y2o3
_edi.schema_version 3
_experiment_type.beam_mode "constant wavelength"
_scattering_source.neutron_scattering_length sears1992
_peak.type cwl-pseudo-voigt
_peak.cutoff_fwhm 20.0
_peak.broad_gauss_u 0.036631
_peak.broad_gauss_v -0.068345
_peak.broad_gauss_w 0.131426
_peak.broad_lorentz_x 0.0
_peak.broad_lorentz_y 0.0
_instrument.setup_wavelength 1.54822
_instrument.calib_twotheta_offset -0.01625
loop_
_excluded_region.id
_excluded_region.start
_excluded_region.end
1 0.0 12.0
2 137.5 180.0
loop_
_linked_structure.structure_id
_linked_structure.scale
y2o3 1.0602()
"""


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


def build() -> edi.Project:
    structure = edi.StructureFactory.from_dict({
        'name': 'y2o3',
        'space_group': {'name_h_m': 'I a -3'},
        'cell': {'length_a': 10.605744},
        'atom_sites': [
            {
                'id': site,
                'type_symbol': symbol,
                'wyckoff_letter': wyckoff,
                'fract': fract,
                'occupancy': 1.0,
                'adp_type': 'beta',
            }
            for site, symbol, wyckoff, fract in SITES
        ],
        'atom_site_aniso': [
            {'id': site, **dict(zip(COMPONENTS, betas, strict=True))}
            for site, betas in BETAS.items()
        ],
    })
    experiment = edi.ExperimentFactory.from_cif_str(EXPERIMENT)
    anchors = []
    for position, height in pcr_background(REFERENCE / 'y2o3.pcr'):
        anchor = edi.LineSegment()
        anchor.position = position
        anchor.intensity = edi.Parameter(height)
        anchors.append(anchor)
    experiment.background = anchors
    # FullProf reads the six '#' lines as comments: 2theta, count and its sigma.
    rows = [
        [float(field) for field in line.split()]
        for line in (REFERENCE / 'y2o3.dat').read_text(encoding='utf-8').splitlines()
        if line.strip() and not line.startswith('#')
    ]
    experiment.data = edi.PdCwlData(
        two_theta=[row[0] for row in rows],
        intensity_meas=[row[1] for row in rows],
        intensity_meas_su=[row[2] for row in rows],
    )
    project = edi.Project()
    project.metadata.name = 'pd_neut_cwl_y2o3_beta_adp'
    project.metadata.title = 'Y2O3, beta ADPs, scale against FullProf'
    project.structure = structure
    project.experiment = experiment
    return project


def write_expected(record: Path) -> Path:
    """``expected.json``: FullProf's references and the regression pins of ``record``."""
    machine = dict(
        line.strip().split('=', 1)
        for line in record.read_text(encoding='utf-8').splitlines()
        if '=' in line
    )
    value, sigma = FULLPROF_SCALE
    quantities = {
        'n_free': {'value': 1.0, 'kind': 'reference', 'tol_abs': 0.0, 'tol_rel': None},
        'n_points_fitted': {
            'value': float(FULLPROF_POINTS),
            'kind': 'reference',
            'tol_abs': 0.0,
            'tol_rel': None,
        },
        'param.scale.value': {
            'value': value,
            'kind': 'reference',
            'tol_abs': sigma,
            'tol_rel': None,
        },
    }
    for key, tol in (('iterations', 0.0), ('reduced_chi_square', 1e-6), ('rwp', 1e-9)):
        quantities[key] = {
            'value': float(machine[key]),
            'kind': 'regression-pin',
            'tol_abs': tol,
            'tol_rel': None,
        }
    document = {
        'schema': 1,
        'source': {
            'engine': 'FullProf 8.40 (references); edi (regression pins)',
            'artifact': 'fullprof/scale-fit.out',
            'provenance': 'PROVENANCE.md',
        },
        'quantities': quantities,
    }
    out = HOME / 'expected.json'
    out.write_text(json.dumps(document, indent=2) + '\n', encoding='utf-8')
    return out


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        '--expected', type=Path, help='write expected.json from this machine record'
    )
    args = parser.parse_args()
    if args.expected is not None:
        print(write_expected(args.expected))
        return 0
    if TARGET.exists():
        print(f'refusing: {TARGET} exists; remove it to rebuild', file=sys.stderr)
        return 1
    build().save_as(str(TARGET))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
