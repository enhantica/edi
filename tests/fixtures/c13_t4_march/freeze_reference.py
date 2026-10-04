"""Freeze committed diffraction-lib reference hashes, never calculated output.

Usage: python freeze_reference.py /path/to/diffraction-lib <commit>
"""

import hashlib
import json
import subprocess
import sys
from pathlib import Path

checkout, ref = sys.argv[1:]
commit = subprocess.check_output(['git', '-C', checkout, 'rev-parse', ref], text=True).strip()
project = 'pd-neut-cwl_lbco_preferred-orientation'
prefix = f'docs/docs/verification/fullprof/{project}'
files = {}
for suffix in ('pcr', 'dat', 'prf', 'sum', 'bac'):
    name = f'lbco.{suffix}'
    content = subprocess.check_output(['git', '-C', checkout, 'show', f'{commit}:{prefix}/{name}'])
    files[name] = hashlib.sha256(content).hexdigest()
Path(__file__).with_name('fullprof.json').write_text(
    json.dumps({'upstream_commit': commit, 'project': project, 'files': files}, indent=2) + '\n'
)
