"""Reproduce the immutable pre-policy inventory from its named Git object."""

import ast
import hashlib
import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
TARGET = Path(__file__).with_name('baseline.json')
old = json.loads(TARGET.read_text())


def read(path):
    return subprocess.check_output([
        'git',
        '-C',
        str(ROOT),
        'show',
        old['commit'] + ':' + path,
    ]).decode()


snapshot = {
    'repo': old['repo'],
    'commit': old['commit'],
    'files': {path: read(path) for path in old['files']},
}
if old['repo'] != 'relay':
    snapshot['nodes'] = [
        line.split('\t', 1)[1]
        for line in snapshot['files']['tests/per-pr-runtimes.tsv'].splitlines()
        if line and not line.startswith('#')
    ]
    snapshot['nonexecution'] = {}
    for path in sorted({node.split('::')[0] for node in snapshot['nodes'] if '.py::' in node}):
        calls = sorted(
            ast.dump(node, include_attributes=False)
            for node in ast.walk(ast.parse(read(path)))
            if isinstance(node, ast.Call)
            and any(token in ast.unparse(node.func) for token in ('skip', 'xfail'))
        )
        if calls:
            snapshot['nonexecution'][path] = calls
    if old['repo'] == 'edi':
        snapshot['scale_source'] = read('tests/deferred/py/scan_scale.py')
        snapshot['scale_sha256'] = hashlib.sha256(snapshot['scale_source'].encode()).hexdigest()
        snapshot['scale_nodes'] = [
            'tests/system/py/test_scan_scale.py::' + node.name
            for node in ast.parse(snapshot['scale_source']).body
            if isinstance(node, ast.FunctionDef) and node.name.startswith('test_')
        ]
TARGET.write_text(json.dumps(snapshot, indent=2, sort_keys=True) + '\n')
