"""reviewed model re-pins; numerical output is a REGRESSION pin only.

Run with --crysta /path/to/crysta in edi's selected consumer-build environment.
External seed identities come from committed crysta bytes, never edi's copies.
"""

import argparse
import hashlib
import json
import subprocess
import sys
from pathlib import Path

root = Path(__file__).resolve().parents[3]
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--crysta', type=Path, required=True)
args = parser.parse_args()
source = args.crysta.resolve()
sha = subprocess.check_output(['git', '-C', str(source), 'rev-parse', 'HEAD'], text=True).strip()
seed_file = root / 'tests/fixtures/c34_t23_cli_projects/source-objects.json'
seed = json.loads(seed_file.read_text())
for case in ('cosio-d20-s1', 'cosio-d20-s4'):
    raw = subprocess.check_output([
        'git',
        '-C',
        str(source),
        'show',
        f'{sha}:tests/fitting/{case}/expected.json',
    ])
    seed['projects'][case]['expected.json'] = hashlib.sha1(
        b'blob ' + str(len(raw)).encode() + b'\0' + raw, usedforsecurity=False
    ).hexdigest()
seed['c11_t62_model_repin'] = {
    'source': f'crysta {sha} (CW bound ad999b88; limit frozen per fit adb3b700)',
    'cases': ['cosio-d20-s1', 'cosio-d20-s4'],
    'kind': 'regression pins only; all other source blob identities retained',
    'generator': 'tests/fixtures/c11_t62/repin.py',
}
seed_file.write_text(json.dumps(seed, indent=2) + '\n')
record = subprocess.check_output(
    [
        sys.executable,
        '-m',
        'edi',
        'fit',
        str(source / 'tests/fitting/cosio-d20-s1/project'),
        '--dry',
        '--report',
        'machine',
        '--verbosity',
        'compact',
    ],
    text=True,
)
lines = record.splitlines()
if sum(line.startswith('elapsed_ms=') for line in lines) != 1:
    raise RuntimeError(' default-record re-pin requires exactly one elapsed field')
output = root / 'tests/fixtures/c11_t35_descent_selector/default-record-no-elapsed.txt'
output.write_text('\n'.join(line for line in lines if not line.startswith('elapsed_ms=')) + '\n')
(root / 'tests/fixtures/c11_t62/repin-provenance.json').write_text(
    json.dumps(
        {
            'generator': 'tests/fixtures/c11_t62/repin.py',
            'crysta_commit': sha,
            'edi_commit': subprocess.check_output(['git', 'rev-parse', 'HEAD'], text=True).strip(),
            'default_record_sha256': hashlib.sha256(output.read_bytes()).hexdigest(),
            'claim': (
                'Regression pin only; covariance, terminal polish and CW generation limit changed.'
            ),
        },
        indent=2,
    )
    + '\n'
)
