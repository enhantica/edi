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
        '/usr/bin/git',
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
if old['repo'] in {'crysta', 'edi'}:
    snapshot['nodes'] = [
        line.split('\t', 1)[1]
        for line in snapshot['files']['tests/per-pr-runtimes.tsv'].splitlines()
        if line and not line.startswith('#')
    ]
    snapshot['execution_sources'] = {}
    pending = (
        ['tools/ci/cpp-test.sh', 'tools/ci/pack-sdk.sh', 'tools/ci/sdk-smoke/run.sh']
        if old['repo'] == 'crysta'
        else ['tools/ci/cpp-test.sh', 'tools/ci/pytest-lenient.sh']
    )
    while pending:
        path = pending.pop()
        if path in snapshot['execution_sources']:
            continue
        body = read(path)
        snapshot['execution_sources'][path] = body
        import re

        pending.extend(
            child
            for child in re.findall(
                r'tools/[\w./-]+\.(?:py|sh)',
                '\n'.join(line.split('#', 1)[0] for line in body.splitlines()),
            )
            if child not in snapshot['execution_sources']
        )
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
allowed = [
    'tests/system/py/test_c13_t12_cli_paths.py::test_create_new_refuses_real_filesystem_alias_before_publication'
]
for relative in (
    []
    if old['repo'] == 'crysta'
    else [
        'tests/system/py/test_e04_t11_wasm_delivery.py',
        'tests/system/py/test_e04_t11_wasm_fit.py',
    ]
):
    functions = {
        node.name: node
        for node in ast.parse(read(relative)).body
        if isinstance(node, ast.FunctionDef)
    }
    calls = {
        name: {ast.unparse(node.func) for node in ast.walk(function) if isinstance(node, ast.Call)}
        for name, function in functions.items()
    }
    skipped = {name for name, names in calls.items() if 'pytest.skip' in names}
    while True:
        reached = skipped | {name for name, names in calls.items() if names & skipped}
        if reached == skipped:
            break
        skipped = reached
    allowed += [
        node
        for node in snapshot['nodes']
        if node.split('::')[0] == relative and node.split('::')[1].split('[', 1)[0] in skipped
    ]
snapshot['platform_nonexecution'] = {
    'linux-64': {},
    'osx-arm64': dict.fromkeys(sorted(allowed), 'skipped'),
}
TARGET.write_text(json.dumps(snapshot, indent=2, sort_keys=True) + '\n')
