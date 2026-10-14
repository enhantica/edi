# SPDX-License-Identifier: BSD-3-Clause
"""Build the CLI project ``pd-xray-cwl_pbso4-lab_round-robin`` from its FullProf reference.

Anglesite from the X-ray Rietveld refinement round robin (R. J. Hill, J. Appl. Cryst. 25, 589
(1992)): the round robin's measured Cu K-alpha pattern, fitted with the model of the
``pd-xray-cwl_PbSO4_round-robin`` verification page. FullProf's reference is the TCH pseudo-Voigt
with Bérar-Baldinozzi asymmetry, a pair edi does not carry, so the project fits the pseudo-Voigt
with Bérar-Baldinozzi (FullProf's Npr 5): its widths, mixing, four coefficients and the scale are
free (10 parameters), starting from the Caglioti widths and mixing that best match FullProf's TCH
full width and mixing over the fitted range (the page's starts), FullProf's Asy1..Asy4 through the
map diffraction-lib issue 166 inferred,
``(-P1 - 3·P2, -P2, -P3 - 3·P4, -P4)``, and twice FullProf's scale.

Everything else is FullProf's and fixed: the structure, the zero, the Cu K-alpha doublet, the
monochromator polarization (characteristic radiation: ``K`` 0.5 and ``acos(sqrt(Cthm))``, which is
why the scale starts at twice the ``.pcr``'s), the asymmetry limit angle, the 6-term polynomial
background and the excluded regions. The data's uncertainties are the square roots of the counts.

Usage (writes ``docs/user/cli/pd-xray-cwl_pbso4-lab_round-robin/project/``; the directory must not
exist)::

    pixi run python tools/cli_projects/build_pbso4_round_robin_project.py
"""

from __future__ import annotations

import math
import sys
from pathlib import Path

import edi

ROOT = Path(__file__).resolve().parents[2]
PROJECT_ID = 'pd-xray-cwl_pbso4-lab_round-robin'
TARGET = ROOT / 'docs' / 'user' / 'cli' / PROJECT_ID / 'project'
REFERENCE = ROOT / 'knowledge' / 'verification' / 'fullprof' / PROJECT_ID

FULLPROF_SCALE = 0.0004703142  # the .pcr's Scale
P1, P2, P3, P4 = -0.41356, 0.0, 1.26777, 0.0  # the .pcr's Asy1..Asy4
BACKGROUND = (121.279, 101.781, -95.426, -113.340, 185.296, -55.129)  # the .pcr's B0..B5
BACKGROUND_ORIGIN = 50.0  # the .pcr's Bkpos


def read_data(path: Path) -> tuple[list[float], list[float], list[float]]:
    """FullProf's free-format data (``Ins`` = 0): start, step, end, then the counts."""
    lines = path.read_text(encoding='utf-8').splitlines()
    start, step, _end = (float(field) for field in lines[0].split()[:3])
    counts = [float(field) for line in lines[1:] for field in line.split()]
    two_theta = [round(start + step * index, 6) for index in range(len(counts))]
    return two_theta, counts, [math.sqrt(count) for count in counts]


def structure() -> edi.Structure:
    return edi.StructureFactory.from_dict({
        'name': 'pbso4',
        'space_group': {'name_h_m': 'P n m a'},
        'cell': {'length_a': 8.485900, 'length_b': 5.402259, 'length_c': 6.964587},
        'atom_sites': [
            {
                'id': site_id,
                'type_symbol': type_symbol,
                'wyckoff_letter': wyckoff,
                'fract': fract,
                'occupancy': 1.0,
                'adp_iso': adp_iso,
            }
            for site_id, type_symbol, wyckoff, fract, adp_iso in (
                ('Pb', 'Pb', 'c', (0.18822, 0.25, 0.16711), 1.86290),
                ('S', 'S', 'c', (0.06306, 0.25, 0.68485), 1.34971),
                ('O1', 'O', 'c', (0.90281, 0.25, 0.59724), 1.19713),
                ('O2', 'O', 'c', (0.18443, 0.25, 0.54586), 2.56174),
                ('O3', 'O', 'd', (0.08094, 0.02239, 0.81289), 1.37463),
            )
        ],
    })


def experiment_text() -> str:
    """The experiment as ``.edi`` text; ``()`` marks the free set."""
    terms = '\n'.join(f'{order + 1} {order} {coef}' for order, coef in enumerate(BACKGROUND))
    return f"""data_pbsox
_edi.schema_version 3
_experiment_type.sample_form powder
_experiment_type.radiation_probe xray
_experiment_type.scattering_type bragg
_experiment_type.beam_mode "constant wavelength"
_scattering_source.xray_form_factor it1992
_scattering_source.xray_dispersion sasaki1989
_peak.type cwl-pseudo-voigt-berar-baldinozzi
_peak.cutoff_fwhm 48.0
_peak.broad_gauss_u 0.065374()
_peak.broad_gauss_v -0.102354()
_peak.broad_gauss_w 0.047897()
_peak.mixing_eta_0 0.625()
_peak.mixing_eta_1 0.0()
_peak.asym_beba_a0 {round(-P1 - 3.0 * P2, 6)}()
_peak.asym_beba_b0 {-P2}()
_peak.asym_beba_a1 {round(-P3 - 3.0 * P4, 6)}()
_peak.asym_beba_b1 {-P4}()
_peak.asym_beba_limit 160.0
_instrument.calib_twotheta_offset 0.00363
_instrument.setup_wavelength 1.540560
_instrument.setup_wavelength_2 1.544400
_instrument.setup_wavelength_2_to_1_ratio 0.5
_instrument.setup_polarization_coefficient 0.5
_instrument.setup_monochromator_twotheta 26.5650511771
_background.type polynomial
_background.origin {BACKGROUND_ORIGIN}
loop_
_background.id
_background.order
_background.coef
{terms}
loop_
_excluded_region.id
_excluded_region.start
_excluded_region.end
1 0.0 9.99
2 154.0 180.0
loop_
_linked_structure.structure_id
_linked_structure.scale
pbso4 {2.0 * FULLPROF_SCALE}()
"""


def build() -> edi.Project:
    experiment = edi.ExperimentFactory.from_cif_str(experiment_text())
    two_theta, counts, sigmas = read_data(REFERENCE / 'pbsox.dat')
    experiment.data = edi.PdCwlData(
        two_theta=two_theta, intensity_meas=counts, intensity_meas_su=sigmas
    )
    project = edi.Project()
    project.metadata.name = 'pd_xray_cwl_pbso4_lab_round_robin'
    project.metadata.title = (
        'PbSO4 X-ray round robin, Cu K-alpha doublet, Berar-Baldinozzi asymmetry'
    )
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
