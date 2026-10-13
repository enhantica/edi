"""Freeze supported atom symbols from the independent engine's shipped tables."""

import hashlib
import json
import subprocess
import sys
from pathlib import Path

engine = Path(sys.argv[1])
folder = Path(__file__).resolve().parent
sets = []
sources = {}
for name in ('neutron', 'xray_f0'):
    path = engine / f'data/scattering/crysta-default/{name}.tsv'
    sources[str(path.relative_to(engine))] = hashlib.sha256(path.read_bytes()).hexdigest()
    sets.append({
        line.split()[0]
        for line in path.read_text().splitlines()
        if line and not line.startswith(('#', '@'))
    })
truth = {
    'engine': subprocess.check_output(
        ['git', '-C', str(engine), 'rev-parse', 'HEAD'], text=True
    ).strip(),
    'sources': sources,
    'supported': sorted(sets[0] & sets[1]),
}
(folder / 'atom-reference.json').write_text(json.dumps(truth, indent=2) + '\n')
