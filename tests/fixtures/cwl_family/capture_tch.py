"""Capture pre-rename calculation bytes as explicit regression pins."""

import argparse
import base64
import json
import platform
import shutil
import subprocess
from pathlib import Path

import edi as crysta
import edi.verification
import numpy as np

from tests.fixtures.cwl_family import profiles

parser = argparse.ArgumentParser()
parser.add_argument('--work', type=Path, required=True)
parser.add_argument('--output', type=Path, required=True)
args = parser.parse_args()
root = Path(__file__).resolve().parents[3]
source = subprocess.check_output(
    [shutil.which('git'), 'rev-parse', 'HEAD'], cwd=root, text=True
).strip()
if source != '7a8eabf53084332a10b90991907d2040e5365b6a':
    message = 'Capture requires the merged pre-rename edi checkout'
    raise ValueError(message)
if crysta.__build_commit__ != source:
    message = 'Capture requires the native edi module built from this baseline'
    raise ValueError(message)
if crysta.verification._crysta_display_pin() is None:
    message = 'Capture requires proven linked engine provenance'
    raise ValueError(message)
pins = {}
for name, token in [('tch', 'cwl-pseudo-voigt'), ('fcj', profiles.RETIRED[0])]:
    extra = '_peak.broad_lorentz_x .023\n_peak.broad_lorentz_y .047\n'
    directory = profiles.write_project(args.work / name, token, extra=extra)
    experiment = directory / 'experiments/bank.edi'
    text = experiment.read_text()
    if name == 'fcj':
        text = text.replace('_peak.broad_lorentz_x 0\n_peak.broad_lorentz_y 0\n', '')
    experiment.write_text(text)
    project = crysta.Project.load(directory)
    project.analysis.calculate()
    pins[name] = base64.b64encode(
        np.asarray(project.experiments[0].data.intensity_calc, dtype='<f8').tobytes()
    ).decode()
args.output.write_text(
    json.dumps(
        {
            'source': source,
            'engine_source': crysta.verification._crysta_provenance_path().read_text().strip(),
            'kind': 'regression-pin',
            'platform': platform.system(),
            'pins': pins,
        },
        indent=2,
    )
    + '\n'
)
