"""Exercise the actual sole-kit page policy without building a WebAssembly engine."""

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

from tests.fixtures.native_process import environment_bash
from tests.fixtures.node_runtime import environment_node

ROOT = Path(__file__).resolve().parents[3]


def test_actual_web_loader_requires_isolation_and_refuses_removed_or_invalid_targets():
    node = environment_node()
    assert node.is_file(), 'The locked environment supplies Node for the actual page policy'
    result = subprocess.run(
        [str(node), str(ROOT / 'tests/system/manual/web_multithread_loader_controls.mjs')],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
        timeout=5,
    )
    assert result.returncode == 0, (
        'The sole-kit page must preserve direct/shim startup and every refusal boundary: '
        + result.stdout
        + result.stderr
    )


def test_shared_written_reference_owner_retains_real_module_and_source_custody(tmp_path):
    root = tmp_path / 'source'
    scripts = root / 'tools/ci'
    scripts.mkdir(parents=True)
    shutil.copy2(ROOT / 'tools/ci/wasm-written-reference.sh', scripts)
    binaries = tmp_path / 'bin'
    binaries.mkdir()
    log = tmp_path / 'calls.jsonl'
    transport = """import json,os,pathlib,sys
args=sys.argv[1:]
name=pathlib.Path(sys.argv[0]).name
with open(os.environ['CAPTURE_CALLS'],'a') as stream:
 stream.write(json.dumps({'name':name,'args':args})+'\\n')
if name=='git': print('a'*40)
elif args[0]=='-c': print('b'*64)
"""
    for name in ('python', 'git'):
        executable = binaries / name
        executable.write_text('#!' + sys.executable + '\n' + transport, newline='\n')
        executable.chmod(0o755)
    output = tmp_path / 'references'
    run = subprocess.run(
        [environment_bash(), str(scripts / 'wasm-written-reference.sh'), str(output)],
        cwd=root,
        env={
            **os.environ,
            'PATH': str(binaries) + os.pathsep + os.environ['PATH'],
            'CAPTURE_CALLS': str(log),
        },
        text=True,
        capture_output=True,
        check=False,
        timeout=3,
    )
    assert run.returncode == 0, (
        'The actual shared capture prerequisite reaches both independent cases: ' + run.stderr
    )
    calls = [json.loads(line) for line in log.read_text().splitlines()]
    module = calls[0]['args']
    assert module[0] == '-c' and 'edi._edi.__file__' in module[1] and 'sha256' in module[1], (
        'Native custody hashes the actually imported extension instead of a guessed build path'
    )
    assert calls[1] == {'name': 'git', 'args': ['rev-parse', 'HEAD']}, (
        'The fresh CI reference requires the exact checked-out Edi source identity'
    )
    for call, case in zip(calls[2:], ('lbco', 'ncaf'), strict=True):
        assert call['args'] == [
            '-m',
            'tests.fixtures.e04_t11_wasm.written',
            'capture',
            '--root',
            str(root),
            '--case',
            case,
            '--reference',
            str(output / case),
            '--module-sha256',
            'b' * 64,
            '--build-commit',
            'a' * 40,
        ], 'Each reference retains actual module/source custody and independent raw qualification'


def test_both_browser_owners_capture_before_running_the_full_driver():
    for name in ('wasm-check.sh', 'wasm-parallel-check.sh'):
        source = (ROOT / 'tools/ci' / name).read_text()
        assert 'mktemp -d "$OUT/native-written.XXXXXX"' in source, (
            'Browser owners allocate fresh reference roots instead of reusing failed captures'
        )
        assert 'bash "$ROOT/tools/ci/wasm-written-reference.sh" "$REFERENCE"' in source, (
            'Both browser owners delegate to the same raw-qualified native Save prerequisite'
        )
        assert '--written-reference="$REFERENCE"' in source, (
            'The full browser and matrix receive the actual captured reference root'
        )
        assert source.index('wasm-written-reference.sh') < source.index(
            'node --experimental-websocket'
        ), 'Native raw qualification completes before any browser fit can claim parity'
    matrix = (ROOT / 'tests/system/manual/web_parallel.mjs').read_text()
    assert "arg.startsWith('--written-reference=')" in matrix and ',reference]' in matrix, (
        'The performance matrix forwards the owned native counterpart into each unchanged full fit'
    )
