"""Copy the external-reference three-file scan into a portable fixture."""

import shutil
import sys
from pathlib import Path

target = Path(__file__).resolve().parent / 'project'
if sys.argv[1:] == ['--update-profile']:
    # The frozen U/V/W/X/Y coefficients belong to the Thompson-Cox-Hastings shape.
    # Only its declaration changes; every measured point and parameter stays frozen.
    experiment = target / 'experiments/d20.edi'
    text = experiment.read_text()
    old = '_peak.type cwl-pseudo-voigt\n'
    new = '_peak.type cwl-tch-pseudo-voigt\n'
    if (
        text.count(old) != 1
        or '_peak.broad_lorentz_x ' not in text
        or '_peak.broad_lorentz_y ' not in text
    ):
        message = 'Profile migration requires the frozen five-coefficient shape'
        raise ValueError(message)
    experiment.write_text(text.replace(old, new, 1))
else:
    source = Path(sys.argv[1]) / 'tests/fitting/cosio-d20-scan-3f/project'
    shutil.copytree(source, target)
