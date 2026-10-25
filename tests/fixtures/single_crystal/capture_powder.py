"""Capture an explicitly labelled powder regression pin before the new feature."""

from __future__ import annotations

import importlib
import json
import shutil
from pathlib import Path

HERE = Path(__file__).resolve().parent


def main():
    root = HERE / 'powder'
    (root / 'structures').mkdir(parents=True, exist_ok=True)
    (root / 'experiments').mkdir(exist_ok=True)
    shutil.copyfile(
        HERE / 'projects/sc-neut-cwl_pr2nio4_basic/structures/structure.edi',
        root / 'structures/structure.edi',
    )
    text = """data_experiment
_edi.schema_version 3
_experiment_type.sample_form powder
_experiment_type.radiation_probe neutron
_experiment_type.scattering_type bragg
_experiment_type.beam_mode "constant wavelength"
_scattering_source.neutron_scattering_length sears1992
_peak.type cwl-tch-pseudo-voigt
_peak.broad_gauss_u 0.036631
_peak.broad_gauss_v -0.068345
_peak.broad_gauss_w 0.131426
_peak.broad_lorentz_x 0
_peak.broad_lorentz_y 0
_peak.cutoff_fwhm 20
_instrument.setup_wavelength 1.54822
_instrument.calib_twotheta_offset -0.01625
loop_
_linked_structure.structure_id
_linked_structure.scale
structure 0.071
loop_
_data.two_theta
_data.intensity_meas
_data.intensity_meas_su
"""
    text += ''.join(f'{20 + i * 0.8:.8g} 0 1\n' for i in range(81))
    (root / 'experiments/experiment.edi').write_text(text)
    engine = importlib.import_module('crysta')
    project = engine.Project.load(root)
    project.analysis.calculate()
    reference = {
        'kind': 'regression-pin',
        'source_commit': engine.__build_commit__,
        'intensity_calc': list(project.experiments[0].data.intensity_calc),
    }
    (HERE / 'powder-regression.json').write_text(json.dumps(reference, indent=2) + '\n')


if __name__ == '__main__':
    main()
