# SPDX-License-Identifier: BSD-3-Clause
"""Build the `pd-neut-tof_diamond-dream_basic` CLI project from its vendored FullProf reference.

.

The project reproduces the model FullProf fitted in diffraction-lib ``0d9f10e``'s
``pd-neut-tof_diamond_dream/`` (restated by as
``knowledge/verification/fullprof/pd-neut-tof_diamond-dream_basic/``) — the same values the
``pd-neut-tof_diamond_dream`` verification page seeds — against the DREAM data FullProf fitted
(``diamond.dat``), with FullProf's fitted linear-interpolation background (``diamond.sum``) and
the overall scale as the ONE free parameter. FullProf's converged scale, Rwp and point count are
then independent references for ``python -m edi fit`` (see the project's ``expected.json``).

Usage (writes ``docs/user/cli/pd-neut-tof_diamond-dream_basic/project/``; the directory must
not exist)::

    pixi run python tools/cli_projects/build_pd_neut_tof_diamond_dream.py
"""

from __future__ import annotations

import sys
from pathlib import Path

import edi

ROOT = Path(__file__).resolve().parents[2]
REFERENCE = ROOT / 'knowledge' / 'verification' / 'fullprof' / 'pd-neut-tof_diamond-dream_basic'
TARGET = ROOT / 'docs' / 'user' / 'cli' / 'pd-neut-tof_diamond-dream_basic' / 'project'

# Occupancy convention of the 0d9f10e .pcr these values come from: C on 16c of F d -3 m:1 with
# Occ = 1.0 per GENERAL position, so its scale absorbs (192 / 16) ** 2 = 144.
OCCUPANCY_SCALE_FACTOR = 144
FULLPROF_SCALE = 0.101177976  # diamond.sum overall scale factor

# diamond.pcr background points (TOF) and the fitted heights diamond.sum reports for them.
FULLPROF_BACKGROUND = [
    (10000.0, -0.228404),
    (14000.0, 0.391510),
    (21000.0, 0.695746),
    (27500.0, 0.569209),
    (40000.0, 0.302807),
    (50000.0, 0.613633),
    (61000.0, 0.737472),
    (70000.0, 0.614094),
]


def read_dat(path: Path) -> tuple[list[float], list[float], list[float]]:
    """Read FullProf's free-format TOF data: one title line, then ``tof intensity sigma`` rows."""
    tof, intensity, sigma = [], [], []
    for line in path.read_text(encoding='utf-8').splitlines()[1:]:
        fields = line.split()
        if not fields:
            continue
        tof.append(float(fields[0]))
        intensity.append(float(fields[1]))
        sigma.append(float(fields[2]))
    return tof, intensity, sigma


def build() -> edi.Project:
    structure = edi.StructureFactory.from_dict({
        'name': 'diamond',
        'space_group': {'name_h_m': 'F d -3 m', 'coord_system_code': '1'},
        'cell': {'length_a': 3.567},
        'atom_sites': [
            {
                'id': 'C',
                'type_symbol': 'C',
                'wyckoff_letter': 'c',
                'fract': (0.125, 0.125, 0.125),
                'adp_iso': 0.89263,
            },
        ],
    })
    experiment = edi.ExperimentFactory.from_dict({
        'name': 'dream',
        'peak': {
            'type': 'tof-jorgensen',
            'cutoff_fwhm': 30.0,
            'broad_gauss_sigma_0': 46937.7188,
            'broad_gauss_sigma_1': 4887.9180,
            'broad_gauss_sigma_2': 0.0,
            'rise_alpha_0': 0.0,
            'rise_alpha_1': 0.022544,
            'decay_beta_0': 0.014330,
            'decay_beta_1': 0.0,
        },
        'instrument': {
            'calib_d_to_tof_offset': 0.0,
            'calib_d_to_tof_linear': 28385.86133,
            'calib_d_to_tof_quadratic': 0.0,
            'setup_twotheta_bank': 90.0,
        },
        'linked_structure': {
            'scale': {
                'value': round(FULLPROF_SCALE * OCCUPANCY_SCALE_FACTOR, 6),
                'uncertainty': None,
                'free': True,
            },
        },
        'background': FULLPROF_BACKGROUND,
        # diamond.pcr excluded regions (LowT HighT) 0-9999 and 70001-200000, and its fitted range
        # TOF-min 8675.1074 .. TOF-max 66503.6875: edi has no range, so the range limit is an
        # exclusion — it drops the last .dat point (66503.6911), which FullProf does not fit.
        'excluded_regions': [(0, 9999), (66503.6875, 200000)],
    })
    tof, intensity, sigma = read_dat(REFERENCE / 'diamond.dat')
    experiment.data = edi.PdTofData(
        time_of_flight=tof, intensity_meas=intensity, intensity_meas_su=sigma
    )

    project = edi.Project()
    project.metadata.name = 'pd_neut_tof_diamond_dream'
    project.metadata.title = 'Diamond, DREAM (ESS) McStas-simulated TOF data'
    project.structure = structure
    project.experiment = experiment
    return project


def main() -> int:
    if TARGET.exists():
        print(f'refusing: {TARGET} exists; remove it to rebuild', file=sys.stderr)
        return 1
    build().save_as(str(TARGET))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
