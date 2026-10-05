import argparse
import hashlib
import json
import shlex
import shutil
import zipfile
from pathlib import Path

import numpy as np

parser = argparse.ArgumentParser(
    description='Freeze an external BEER run; no calculator is executed.'
)
parser.add_argument('--run-root', type=Path, required=True)
parser.add_argument('--commands', type=Path, required=True)
parser.add_argument('--unconstrained-run', action='store_true')
parser.add_argument('--output-home', type=Path)
args = parser.parse_args()
home = args.output_home or Path(__file__).with_name('beer')
run = args.run_root
record = json.loads((run / 'reference.json').read_text())
record['raw_capture_sha256'] = hashlib.sha256((run / 'reference.json').read_bytes()).hexdigest()
record['data_source'] = {
    'dataset': 'meas-ferrite-austenite-beer',
    'ref': '35af7e9bf469a1ee4ecc889aff2279440b020c8a',
    'url': (
        'https://raw.githubusercontent.com/easyscience/diffraction/'
        '35af7e9bf469a1ee4ecc889aff2279440b020c8a/data/measured/'
        'ferrite-austenite-beer.zip'
    ),
}
# Publish reproducible coordinates relative to an edi checkout, rather than
# the author's home directory. The external checkout and run directory are
# siblings of edi; all options and the two-stage recovery remain explicit.
line = -1 if args.unconstrained_run else -2
command = shlex.split(args.commands.read_text().splitlines()[line])
command[0] = '../diffraction-lib/.pixi/envs/default/bin/python'
command[command.index('-u') + 1] = 'tests/fixtures/multiphase/author_beer.py'
for option, relative in {
    '--tutorial': '../diffraction-lib/docs/docs/tutorials/calibrate-beer-ess.py',
    '--archive': 'tests/fixtures/multiphase/beer/data/ferrite-austenite-beer.zip',
    '--output': '../beer-authoring/record',
    '--resume-first-stage': '../beer-authoring/projects/calibrate-beer-ess',
}.items():
    if option in command:
        command[command.index(option) + 1] = relative
if args.unconstrained_run:
    if record['reference_variant'] != 'unconstrained-independent-bank-scales':
        message = 'The unconstrained capture must identify its independent-bank variant'
        raise ValueError(message)
    record['commands'] = [shlex.join(command)]
    record['capture_recovery'] = (
        'One authoring invocation executed both tutorial fit stages in memory. '
        'Only the two named cross-bank scale constraints were omitted; each bank '
        'phase scale remained free. No saved-stage recovery or repeat optimizer '
        'execution occurred. Rendering was omitted and the verified local archive '
        'replaced downloading inside the tutorial.'
    )
else:
    first_command = command.copy()
    resume_index = first_command.index('--resume-first-stage')
    del first_command[resume_index : resume_index + 2]
    record['commands'] = [shlex.join(first_command), shlex.join(command)]
    record['capture_recovery'] = (
        'The first fit succeeded and auto-saved before the extractor '
        'rejected a string-valued space-group parameter. The second '
        'invocation recovered that saved result, with rounded persisted '
        'first-stage values and reversed bank ordering, and ran only the '
        'tutorial second fit. No optimizer run was repeated. Rendering '
        'calls were omitted, and the verified local archive replaced '
        'downloading inside the tutorial.'
    )
for index, stage in enumerate(record['stages'], 1):
    numerator = denominator = 0.0
    for p in (run / f'stage-{index}' / 'experiments').glob('*.edi'):
        rows = [
            line.split()
            for line in p.read_text().split('_data.calc_status\n')[1].splitlines()
            if line.strip()
        ]
        a = np.array([
            [float(value) for value in row[:7]]
            for row in rows
            if len(row) == 8 and row[7] == 'incl'
        ])
        numerator += float(np.sum(((a[:, 3] - a[:, 5]) / a[:, 4]) ** 2))
        denominator += float(np.sum((a[:, 3] / a[:, 4]) ** 2))
    stage['active_rwp'] = float(np.sqrt(numerator / denominator))
    stage['active_rwp_derivation'] = (
        'sqrt(sum(((intensity_meas-intensity_calc)/intensity_meas_su)'
        '^2)/sum((intensity_meas/intensity_meas_su)^2)) over '
        'calc_status=incl in saved external Edi outputs; computed by '
        'capture_beer.py.'
    )
    stage['all_parameters'] = {
        k: v
        for k, v in stage['all_parameters'].items()
        if '.data.' not in k and '.refln.' not in k
    }
for name in ('initial', 'stage-1', 'stage-2'):
    for p in (run / name).rglob('*.edi'):
        dest = home / 'reference-run' / name / p.relative_to(run / name)
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(p, dest)
record['initial_sha256'] = {
    k: v for k, v in record['initial_sha256'].items() if k.endswith('.edi')
}
record['output_sha256'] = {k: v for k, v in record['output_sha256'].items() if k.endswith('.edi')}
with zipfile.ZipFile(home / 'data/ferrite-austenite-beer.zip') as z:
    for name in z.namelist():
        data = z.read(name)
        (home / 'data' / name).write_bytes(data)
record['data_sha256'] = {
    p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted((home / 'data').glob('*'))
}
(home / 'reference.json').write_text(json.dumps(record, indent=2) + '\n')
print(
    'Committed reference candidate',
    (home / 'reference.json').stat().st_size,
    'bytes; final parameters',
    len(record['stages'][-1]['parameters']),
)
