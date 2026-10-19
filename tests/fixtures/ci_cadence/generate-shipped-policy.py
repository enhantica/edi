"""Capture the independently merged fast-path policy; never read candidate files."""

import json
import subprocess
from pathlib import Path

from event_policy import apply_event_policy
from inventory import identity

ROOT = Path(__file__).resolve().parents[3]
BASE = json.loads(Path(__file__).with_name('baseline.json').read_text())
COMMIT = {'crysta': 'c7cfdf62', 'edi': 'a341b98154b53ea2499213a6c60b87e1371e9ce8'}[BASE['repo']]
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
        identity(line.split('\t', 1)[1])
        for line in read('tests/per-pr-runtimes.tsv').splitlines()
        if line and not line.startswith('#')
    ],
    'files': {p: read(p) for p in FILES},
    'execution_sources': {p: read(p) for p in BASE['execution_sources']},
}
Path(__file__).with_name('shipped-policy.json').write_text(
    json.dumps(apply_event_policy(snapshot), indent=2) + '\n'
)
