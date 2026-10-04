"""Freeze historical INPUT hashes for the k=1 exemption (regression pins).

Run with the pre-task edi commit as argument. No current product bytes enter
these expectations; outputs are excluded and checked by independent replay.
"""

import hashlib
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
FIX = Path(__file__).resolve().parent
BASE = json.loads((FIX / 'baseline.json').read_text())


def git(*args):
    return subprocess.check_output(['git', '-C', str(ROOT), *args])


revision = git('rev-parse', sys.argv[1]).decode().strip()
projects = {}
for name, baseline in BASE.items():
    if baseline['source'] == 'edi PR #75':
        continue  # YAP changes occupancy, so it is never exempt.
    source = Path(baseline['source'])
    pcr = git('show', f'{revision}:{source}')
    if pcr.decode().replace('\r\n', '\n') != baseline['pcr']:
        raise ValueError(f'{name}: historical PCR differs from the frozen baseline')
    paths = git('ls-tree', '--name-only', revision, f'{source.parent}/').decode().splitlines()
    auxiliary = {}
    for path in map(Path, paths):
        if path.suffix.lower() not in {'.dat', '.gss', '.irf', '.hkl', '.int'}:
            continue
        # The pre-task LaB6 directory contains three independent PCR/data pairs.
        if source.parent.name == 'pd-neut-cwl_lab6' and path.stem != source.stem:
            continue
        auxiliary[path.name] = hashlib.sha256(git('show', f'{revision}:{path}')).hexdigest()
    projects[name] = {
        'source': str(source),
        'pcr_sha256': hashlib.sha256(pcr).hexdigest(),
        'auxiliary_sha256': auxiliary,
    }
(FIX / 'unchanged-inputs.json').write_text(
    json.dumps({'source_commit': revision, 'projects': projects}, indent=2) + '\n'
)
