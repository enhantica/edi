# SPDX-License-Identifier: BSD-3-Clause
"""Build the CLI project ``pd-xray-cwl_lif_single`` from its FullProf reference.

The project carries the model of the ``pd-xray-cwl_LiF_single_polarization`` verification page:
LiF, Cu K-alpha1, FullProf's fixed profile and structure, the scattering sources FullProf's are
comparable to (``it1992`` f0, ``sasaki1989`` dispersion), and the X-ray polarization factor.
Its measured pattern is FullProf's CALCULATED polarized
profile (``lif_single_polarized.prf`` minus its ``.bac``, on FullProf's grid, unit uncertainties)
because the reference's own "observed" data are a dummy pattern.

The two polarization parameters are the free set, and they start away from FullProf's values:
``setup_polarization_coefficient`` (FullProf ``Rpolarz`` 0.5) and
``setup_monochromator_twotheta`` (``acos(sqrt(Cthm))``, ``Cthm`` 0.8). The scale is FIXED at twice
the ``.pcr`` scale -- FullProf's characteristic-radiation factor ``1 + Cthm cos^2(2theta)`` is
twice the polarization factor at K = 0.5 -- because scale, K and the monochromator angle together
carry only two independent numbers, so a third free one would make the fit singular. FullProf's
own two inputs are then independent references for ``python -m edi fit`` (``expected.json``).

Usage (writes ``docs/user/cli/pd-xray-cwl_lif_single/project/``; the directory must not exist)::

    pixi run python tools/cli_projects/build_c15_t2_project.py
"""

from __future__ import annotations

import sys
from pathlib import Path

import edi
from edi import verification as verify

ROOT = Path(__file__).resolve().parents[2]
PROJECT_ID = 'pd-xray-cwl_lif_single'
TARGET = ROOT / 'docs' / 'user' / 'cli' / PROJECT_ID / 'project'

FULLPROF_PROJECT_DIR = 'pd-xray-cwl_lif_single-polarization'
FULLPROF_PRF_FILE = 'lif_single_polarized.prf'
FULLPROF_BAC_FILE = 'lif_single_polarized.bac'

FULLPROF_SPACE_GROUP = 'F m -3 m'
FULLPROF_CELL_LENGTH_A = 4.026700
FULLPROF_ATOM_SITES = [
    # FullProf Atom, Typ, Wyckoff, (X, Y, Z), Occ (chemical), Biso
    ('Li1', 'Li', 'a', (0.0, 0.0, 0.0), 1.0, 1.20000),
    ('F1', 'F', 'b', (0.5, 0.5, 0.5), 1.0, 0.80000),
]
FULLPROF_ZERO = 0.0
FULLPROF_SCALE = 0.01
FULLPROF_WAVELENGTH = 1.540560
FULLPROF_U = 0.048457
FULLPROF_V = -0.083053
FULLPROF_W = 0.040000
FULLPROF_X = 0.0
FULLPROF_Y = 0.049268
FULLPROF_WDT = 48.0
# FullProf's characteristic-radiation factor 1 + Cthm cos^2(2theta) is 2 P at K = 0.5.
FULLPROF_CHARACTERISTIC_FACTOR = 2.0

# Where the two free parameters start: away from FullProf's Rpolarz 0.5 and 26.5650511771 deg.
START_POLARIZATION_COEFFICIENT = 0.4
START_MONOCHROMATOR_TWOTHETA = 20.0


def structure() -> edi.Structure:
    return edi.StructureFactory.from_dict({
        'name': 'lif',
        'space_group': {'name_h_m': FULLPROF_SPACE_GROUP},
        'cell': {'length_a': FULLPROF_CELL_LENGTH_A},
        'atom_sites': [
            {
                'id': site_id,
                'type_symbol': type_symbol,
                'wyckoff_letter': wyckoff,
                'fract': fract,
                'occupancy': occupancy,
                'adp_iso': adp_iso,
            }
            for site_id, type_symbol, wyckoff, fract, occupancy, adp_iso in FULLPROF_ATOM_SITES
        ],
    })


def experiment_text() -> str:
    """The experiment's scalars as ``.edi`` text; ``()`` marks the two free parameters."""
    return f"""data_cu_ka
_edi.schema_version 3
_experiment_type.sample_form powder
_experiment_type.radiation_probe xray
_experiment_type.scattering_type bragg
_experiment_type.beam_mode "constant wavelength"
_scattering_source.xray_form_factor it1992
_scattering_source.xray_dispersion sasaki1989
_peak.type cwl-pseudo-voigt
_peak.broad_gauss_u {FULLPROF_U}
_peak.broad_gauss_v {FULLPROF_V}
_peak.broad_gauss_w {FULLPROF_W}
_peak.broad_lorentz_x {FULLPROF_X}
_peak.broad_lorentz_y {FULLPROF_Y}
_peak.cutoff_fwhm {FULLPROF_WDT}
_instrument.calib_twotheta_offset {FULLPROF_ZERO}
_instrument.setup_wavelength {FULLPROF_WAVELENGTH}
_instrument.setup_polarization_coefficient {START_POLARIZATION_COEFFICIENT}()
_instrument.setup_monochromator_twotheta {START_MONOCHROMATOR_TWOTHETA}()
loop_
_linked_structure.structure_id
_linked_structure.scale
lif {FULLPROF_CHARACTERISTIC_FACTOR * FULLPROF_SCALE}
"""


def build() -> edi.Project:
    experiment = edi.ExperimentFactory.from_cif_str(experiment_text())
    x, calc_fullprof = verify.load_fullprof_calc_profile(
        FULLPROF_PROJECT_DIR, FULLPROF_PRF_FILE, FULLPROF_BAC_FILE, FULLPROF_ZERO
    )
    verify.set_reference_as_measured(experiment, x, calc_fullprof)
    project = edi.Project()
    project.metadata.name = 'pd_xray_cwl_lif_single'
    project.metadata.title = 'LiF, Cu K-alpha1 X-ray, polarization against FullProf'
    project.structure = structure()
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
