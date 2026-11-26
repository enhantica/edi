"""Invented CW satellites from an orthorhombic reciprocal metric, no engine output."""

import json
import math
from pathlib import Path

from generate_gui import parent


def main():
    root = Path(__file__).parent / 'gui/find-k'
    for directory in ['structures', 'experiments', 'analysis']:
        (root / directory).mkdir(parents=True, exist_ok=True)
    (root / 'project.edi').write_text('_edi.schema_version 3\n_metadata.name search_fixture\n')
    (root / 'structures/parent.edi').write_text(parent())
    (root / 'analysis/analysis.edi').write_text(
        '_edi.schema_version 3\n_fitting_mode.type single\n'
    )
    positions = []
    for h in range(4):
        for k in range(4):
            for ell in range(3):
                reciprocal = (h + 0.5) ** 2 / 36 + k * k / 49 + ell * ell / 64
                angle = 2 * math.degrees(math.asin(1.54 * math.sqrt(reciprocal) / 2))
                if 12 < angle < 78 and all(abs(angle - old) > 0.8 for old in positions):
                    positions.append(angle)
    positions = sorted(positions[:16])
    for name in ['first', 'second']:
        text = f"""data_{name}
_edi.schema_version 3
_experiment_type.sample_form powder
_experiment_type.radiation_probe neutron
_experiment_type.scattering_type bragg
_experiment_type.beam_mode "constant wavelength"
_peak.type cwl-tch-pseudo-voigt
_peak.broad_gauss_u 0
_peak.broad_gauss_v 0
_peak.broad_gauss_w .04
_peak.broad_lorentz_x 0
_peak.broad_lorentz_y 0
_peak.cutoff_fwhm 10
_instrument.setup_wavelength 1.54
_instrument.calib_twotheta_offset 0
_background.type polynomial
_background.origin 40
_background_estimate.mode manual
loop_
_background.id
_background.order
_background.coef
0 0 20()
loop_
_linked_structure.structure_id
_linked_structure.scale
_linked_structure.enabled
parent 0.0000000001 true
loop_
_data.two_theta
_data.intensity_meas
_data.intensity_meas_su
"""
        for i in range(1501):
            x = 10 + i * 0.05
            observed = 30 + sum(
                100 * math.exp(-4 * math.log(2) * (x - position) ** 2 / 0.04)
                for position in positions
            )
            text += f'{x:.8f} {observed:.12g} 1\n'
        (root / 'experiments' / (name + '.edi')).write_text(text)
    (root / 'PROVENANCE.json').write_text(
        json.dumps(
            {
                'source': (
                    'Closed-form orthorhombic d^-2=(h+kx)^2/a^2+k^2/b^2+l^2/c^2; '
                    'Bragg 2theta, unit errors and Gaussian FWHM 0.2 degrees'
                ),
                'k': [0.5, 0, 0],
                'cell': [6, 7, 8],
                'peak_positions': positions,
                'fit': (
                    'Only a constant background is free. The parent is enabled and fixed; '
                    'its tiny scale isolates the invented satellites.'
                ),
            },
            indent=2,
        )
        + '\n'
    )


if __name__ == '__main__':
    main()
