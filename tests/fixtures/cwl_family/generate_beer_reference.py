import argparse
import hashlib
import json
import re
from pathlib import Path

parser = argparse.ArgumentParser()
parser.add_argument('--fullprof-home', type=Path, required=True)
parser.add_argument('--output', type=Path, required=True)
args = parser.parse_args()
home = args.fullprof_home
text = (home / 'duplex_mode6-IRF.sum').read_text()
number = r'[-+]?(?:\d+\.?\d*|\.\d+)(?:[Ee][-+]?\d+)?'
pair = r'(' + number + r')\s+(' + number + r')'
parameters = {}
phases = re.split(r'=> Phase No\.\s+\d+', text)[1:]
for name, phase in zip(('ferrite', 'austenite'), phases, strict=True):
    atom = re.search(r'Fe\s+(.*)', phase)[1]
    row = re.findall(r'(' + number + r')\(\s*(\d+)\)', atom)
    value, su = row[3]
    parameters[f'{name}.atom_site.Fe.adp_iso'] = [
        float(value),
        int(su) * 10 ** -len(value.split('.')[1]),
    ]
    patterns = phase.split('==> PROFILE PARAMETERS FOR PATTERN#')[1:]
    for bank, part in zip(('expt_s2', 'expt_n2'), patterns, strict=True):
        scale = re.search(r'Overall scale factor\s*:\s*' + pair, part)
        parameters[f'{bank}.linked_structure.{name}.scale'] = list(map(float, scale.groups()))
        if name == 'ferrite':
            for heading, fields in [
                (
                    'Gaussian variances Sig-2, Sig-1, Sig-0:',
                    ('broad_gauss_sigma_2', 'broad_gauss_sigma_1', 'broad_gauss_sigma_0'),
                ),
                (
                    'Lorentzian FWHM Gam-2, Gam-1, Gam-0:',
                    ('broad_lorentz_gamma_2', 'broad_lorentz_gamma_1', 'broad_lorentz_gamma_0'),
                ),
            ]:
                values = re.findall(pair, part.split(heading)[1].split('=>')[0])
                for key, (value, su) in zip(fields, values, strict=True):
                    if float(su):
                        parameters[f'{bank}.peak.{key}'] = [float(value), float(su)]
for bank, part in zip(
    ('expt_s2', 'expt_n2'), text.split('==> GLOBAL PARAMETERS FOR PATTERN#')[1:], strict=True
):
    parameters[f'{bank}.instrument.calib_d_to_tof_offset'] = list(
        map(float, re.search(r'Zero-point:\s*' + pair, part).groups())
    )
    bg = part.split('Background Parameters (linear interpolation)  ==>')[1]
    bg = bg.split('=> T.O.F.')[0]
    for i, (value, su) in enumerate(re.findall(pair, bg), 1):
        if float(su):
            parameters[f'{bank}.background.{i}.intensity'] = [float(value), float(su)]
reference = {
    'source': (
        'Owner-supplied FullProf.2k 8.40 run, unchanged summary and code-81 cross-phase Biso'
    ),
    'summary_sha256': hashlib.sha256((home / 'duplex_mode6-IRF.sum').read_bytes()).hexdigest(),
    'n_free': 75,
    'parameters': parameters,
    'rwp': {'expt_s2': 0.072, 'expt_n2': 0.0706},
}
print('BEER mapped values', len(parameters), 'independent', len(parameters) - 1)
args.output.write_text(json.dumps(reference, indent=2) + '\n')
