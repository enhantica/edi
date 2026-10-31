"""Crash-isolated public save consumer for measured and axis-only powder banks."""

import importlib
import json
import sys
from pathlib import Path

sys.path[:0] = json.loads(sys.argv[1])
package, source, destination, operation = sys.argv[2:]
engine = importlib.import_module(package)
if package == 'edi':
    # The public edi loader accepts a measured bank beside a calculation grid.
    file = Path(source) / 'experiments/due.edi'
    prefix = file.read_text().split('loop_\n_data.two_theta\n', 1)[0]
    file.write_text(
        prefix + '_data_range.two_theta_min 20\n'
        '_data_range.two_theta_max 50\n_data_range.two_theta_step 10\n'
    )
project = engine.Project.load(source)
if package == 'crysta':
    # Its legacy directory reader selects measured/range for the whole project;
    # construct the mixed live project through the supported public data API.
    axis = list(project.experiments['due'].data.two_theta)
    project.experiments['due'].data = engine.PdCwlData(two_theta=axis)
print('Reached Save with measured and axis-only banks', file=sys.stderr, flush=True)
if operation == 'save':
    project.save()
elif operation == 'save-as':
    project.save_as(destination)
elif operation == 'cli-output':
    cli = importlib.import_module('edi.__main__')
    project = cli._open(cli.build_parser().parse_args(['calc', source, '--output', destination]))
else:
    message = 'Unknown save operation'
    raise ValueError(message)
# Read the live simulated axis without synthesizing observations. The parent
# independently checks both the written data and the saved agreement records.
banks = {}
for bank in project.experiments:
    banks[bank.name] = {
        'measured': len(bank.data.intensity_meas),
        'calculated': list(map(float, bank.data.intensity_calc)),
    }
print(
    json.dumps({
        'extension': str(Path(sys.modules[package + '._' + package].__file__).resolve()),
        'banks': banks,
        'analysis': (Path(destination) / 'analysis/analysis.edi').read_text(),
        'simulated_file': (Path(destination) / 'experiments/due.edi').read_text(),
    })
)
