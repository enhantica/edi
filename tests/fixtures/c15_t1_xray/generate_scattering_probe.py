"""Generate the independent analytic  Fe probe, no production import.

Coefficients transcribed from published IT1992 and WK1995/DABAX; provenance
and Sasaki/IT Vol C values are in SCATTERING.md. The cell has six {100}
reflections on this narrow grid and normalized Gaussian FWHM 0.1 degree.
"""

import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parent
MODEL = """data_structure
_cell.length_a 2
_cell.length_b 2
_cell.length_c 2
_cell.angle_alpha 90
_cell.angle_beta 90
_cell.angle_gamma 90
_space_group.name_h_m "P m -3 m"
loop_
_atom_site.id
_atom_site.wyckoff_letter
_atom_site.type_symbol
_atom_site.adp_type
_atom_site.fract_x
_atom_site.fract_y
_atom_site.fract_z
_atom_site.occupancy
_atom_site.adp_iso
X a Fe Biso 0 0 0 0.7 0.8

data_experiment
_experiment_type.sample_form powder
_experiment_type.radiation_probe xray
_experiment_type.scattering_type bragg
_experiment_type.beam_mode "constant wavelength"
_peak.type cwl-tch-pseudo-voigt
_peak.broad_gauss_u 0
_peak.broad_gauss_v 0
_peak.broad_gauss_w 0.01
_peak.broad_lorentz_x 0
_peak.broad_lorentz_y 0
_peak.cutoff_fwhm 10
_instrument.calib_twotheta_offset 0
loop_
_linked_structure.structure_id
_linked_structure.scale
structure 1
"""
(ROOT / 'single_fe.edi').write_text(MODEL)
rows = {}
for source, a, b, c in [
    ('it1992', [11.7695, 7.3573, 3.5222, 2.3045], [4.7611, 0.3072, 15.3535, 76.8805], 1.0369),
    (
        'wk1995',
        [12.311098, 1.876623, 3.066177, 2.070451, 6.975185],
        [5.009415, 0.014461, 18.743040, 82.767876, 0.346506],
        -0.304931,
    ),
]:
    f0 = c + sum(ai * math.exp(-bi / 16) for ai, bi in zip(a, b, strict=True))
    theta = math.asin(1.54 / 4)
    for dispersion, fp, fpp in [
        ('none', 0, 0),
        ('sasaki1989', -1.1755, 3.1957),
        ('it1992', -1.1336, 3.1974),
    ]:
        intensity = (
            6
            * 0.7**2
            * math.exp(-2 * 0.8 / 16)
            * ((f0 + fp) ** 2 + fpp**2)
            / (math.sin(theta) * math.sin(2 * theta))
        )
        y = [
            intensity
            * math.sqrt(4 * math.log(2) / math.pi)
            / 0.1
            * math.exp(-4 * math.log(2) * delta**2 / 0.01)
            for delta in [-0.01, 0, 0.01]
        ]
        rows[source + ':' + dispersion] = y
rows['grid'] = [2 * math.degrees(theta) + delta for delta in [-0.01, 0, 0.01]]
(ROOT / 'single_fe.json').write_text(json.dumps(rows, indent=2) + '\n')
