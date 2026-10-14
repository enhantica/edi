"""Capture the independently merged fast-path policy; never read candidate files."""

import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
BASE = json.loads(Path(__file__).with_name('baseline.json').read_text())
COMMIT = {'crysta': 'c7cfdf62', 'edi': 'bd72193'}[BASE['repo']]
FILES = ['.github/workflows/ci.yml', 'tests/test-groups.json', 'pixi.toml']
FILES += (
    ['tools/ci/python-tiers.sh'] if BASE['repo'] == 'crysta' else ['tools/ci/system-tests-part.sh']
)


def read(path):
    return subprocess.check_output(
        ['/usr/bin/git', '-C', str(ROOT), 'show', COMMIT + ':' + path], text=True
    )


snapshot = {
    'repo': BASE['repo'],
    'commit': subprocess.check_output(
        ['/usr/bin/git', '-C', str(ROOT), 'rev-parse', COMMIT], text=True
    ).strip(),
    'role': 'accepted-main regression inputs; correctness follows the committed owner policy',
    'nodes': [
        line.split('\t', 1)[1]
        for line in read('tests/per-pr-runtimes.tsv').splitlines()
        if line and not line.startswith('#')
    ],
    'files': {p: read(p) for p in FILES},
}
Path(__file__).with_name('shipped-policy.json').write_text(json.dumps(snapshot, indent=2) + '\n')
