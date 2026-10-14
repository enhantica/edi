"""Copy independent, committed input artifacts into the test fixture."""

import argparse
import hashlib
import json
import shutil
from pathlib import Path

parser = argparse.ArgumentParser()
parser.add_argument('--fcj-project', type=Path, required=True)
parser.add_argument('--lbco-case', type=Path, required=True)
args = parser.parse_args()
root = Path(__file__).resolve().parent
for source, destination in ((args.fcj_project, root / 'fcj'),):
    shutil.copytree(source, destination, dirs_exist_ok=True)
shutil.copy2(args.lbco_case / 'fullprof/lbco.sum', root / 'lbco.sum')
manifest = {
    str(p.relative_to(root)): hashlib.sha256(p.read_bytes()).hexdigest()
    for directory in ('fcj',)
    for p in sorted((root / directory).rglob('*'))
    if p.is_file()
}
manifest['lbco.sum'] = hashlib.sha256((root / 'lbco.sum').read_bytes()).hexdigest()
(root / 'inputs.json').write_text(json.dumps(manifest, indent=2) + '\n')
