"""Freeze an existing independent FullProf run; never execute the engine.

Usage: python freeze_pearl_authoring.py /path/to/completed/ralf-run
Source for this snapshot: the FullProf 8.40 run retained by tests seq 6,
<author-runs>/-tests-seq6-whole.log, before the no-runtime-engine ruling.
"""

import hashlib
import json
import sys
from pathlib import Path


def freeze(source: Path) -> None:
    destination = Path(__file__).parent / 'pearl-authoring'
    destination.mkdir(exist_ok=True)
    files = {}
    for suffix in ('.pcr', '.prf', '.sum', '.out'):
        path = source / ('Ceo2_PEARL' + suffix)
        name = path.with_suffix('.inp').name if suffix == '.pcr' else path.name
        content = path.read_bytes()
        (destination / name).write_bytes(content)
        files[name] = hashlib.sha256(content).hexdigest()
    manifest = {
        'version': 'FullProf.2k 8.40',
        'command': ['fp2k', 'Ceo2_PEARL', 'Ceo2_PEARL'],
        'source': 'Independent RALF run retained by -tests-seq6-whole.log; 2026-09-25',
        'input_name': 'Ceo2_PEARL.pcr (retained after the run as Ceo2_PEARL.inp)',
        'input_note': 'FullProf rewrites the sampling range; physical parameters remain fixed.',
        'data_name': 'Ceo2_PEARL.dat (original ../Ceo2_PEARL.ralf)',
        'data_sha256': hashlib.sha256((source / 'Ceo2_PEARL.dat').read_bytes()).hexdigest(),
        'sha256': files,
    }
    (destination / 'manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')


if __name__ == '__main__':
    freeze(Path(sys.argv[1]))
