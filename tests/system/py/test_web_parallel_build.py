"""Exercise the real web build script with offline compiler transports."""

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]


@pytest.fixture
def build_calls(tmp_path):
    root = tmp_path / 'edi'
    scripts = root / 'tools/ci'
    scripts.mkdir(parents=True)
    for name in ('wasm-build.sh', 'wasm-env.sh'):
        shutil.copy2(ROOT / 'tools/ci' / name, scripts / name)
    source = root / 'build/crysta-src'
    source.mkdir(parents=True)
    (source / 'CRYSTA_SOURCE_SHA').write_text('a' * 40)
    tools = tmp_path / 'toolchain'
    emsdk = tools / 'emsdk-4.0.7'
    bin_dir = emsdk / 'bin'
    bin_dir.mkdir(parents=True)
    (emsdk / '.edi-installed').write_text('4.0.7\n')
    (emsdk / 'emsdk_env.sh').write_text('export PATH="' + str(bin_dir) + ':$PATH"\n')
    (tools / 'eigen-3.4.0/share/eigen3/cmake').mkdir(parents=True)
    transport = """import json, os, pathlib, sys
name = pathlib.Path(sys.argv[0]).name
args = sys.argv[1:]
with open(os.environ['BUILD_CALLS'], 'a') as stream:
    stream.write(json.dumps(dict(name=name, args=args)) + '\\n')
if name == 'emcc':
    print('4.0.7')
if '-B' in args:
    out = pathlib.Path(args[args.index('-B') + 1])
    (out / 'app').mkdir(parents=True, exist_ok=True)
    (out / 'app/edi_app.wasm').write_bytes(b'\\0asm\\1\\0\\0\\0')
for arg in args:
    if arg.startswith('-DCMAKE_INSTALL_PREFIX='):
        pathlib.Path(arg.split('=', 1)[1]).mkdir(parents=True, exist_ok=True)
"""
    for name in ('emcc', 'emcmake', 'cmake'):
        executable = bin_dir / name
        executable.write_text('#!' + sys.executable + '\n' + transport)
        executable.chmod(0o755)
    for mode in ('singlethread', 'multithread'):
        kit = tools / 'qt/6.11.2' / ('wasm_' + mode)
        (kit / 'lib/cmake/Qt6').mkdir(parents=True)
        (kit / 'lib/cmake/Qt6/QtPublicWasmToolchainHelpers.cmake').write_text(
            'set(QT_EMCC_RECOMMENDED_VERSION "4.0.7")\n'
        )
        (kit / 'bin').mkdir()
        stub = kit / 'bin/qt-cmake.py'
        stub.write_text(transport)
        (kit / 'bin/qt-cmake').write_text(
            'exec "' + sys.executable + '" "' + str(stub) + '" "$@"\n'
        )
    calls = tmp_path / 'calls.jsonl'
    env = {
        **os.environ,
        'EDI_WASM_TOOLCHAIN': str(tools),
        'CONDA_PREFIX': str(tmp_path / 'host'),
        'BUILD_CALLS': str(calls),
        'EDI_WASM_CRYSTA_SRC': '',
    }
    result = subprocess.run(
        ['bash', str(scripts / 'wasm-build.sh'), 'multithread', 'singlethread'],
        cwd=root,
        env=env,
        capture_output=True,
        text=True,
        check=False,
        timeout=3,
    )
    assert result.returncode == 0, (
        'Both web kits must reach their actual build commands with offline compiler transports: '
        + result.stderr
    )
    return [json.loads(line) for line in calls.read_text().splitlines()]


def test_each_kit_selects_its_own_engine_backend_and_simd(build_calls):
    core = [call['args'] for call in build_calls if call['name'] == 'emcmake']
    assert len(core) == 2, 'The web build must independently configure both engine kits'
    for flags in core:
        threaded = any('/multithread/' in flag for flag in flags)
        assert '-DCRYSTA_OPENMP=OFF' in flags, (
            'Both web kits must keep native OpenMP disabled'
        )
        assert '-DCRYSTA_SLEEF=' + ('ON' if threaded else 'OFF') in flags, (
            'The multithread web kit must select the vectorised maths layer; the serial kit stays scalar'
        )
        assert '-DCRYSTA_WASM_THREADS=' + ('ON' if threaded else 'OFF') in flags, (
            'Only the multithread kit may require pthreads and shared memory'
        )
        assert '-DCRYSTA_WASM_SIMD=' + ('ON' if threaded else 'OFF') in flags, (
            'Multithread engine must enable wasm SIMD; serial fallback must stay scalar compatible'
        )


def test_app_pthread_pool_is_preallocated_and_sized_for_the_engine(build_calls):
    apps = [call['args'] for call in build_calls if call['name'] == 'qt-cmake.py']
    assert len(apps) == 2, 'Both Qt kits must configure through their actual kit launcher'
    threaded = next(flags for flags in apps if any('/multithread/' in flag for flag in flags))
    serial = next(flags for flags in apps if any('/singlethread/' in flag for flag in flags))
    text = ' '.join(threaded)
    assert 'PTHREAD_POOL_SIZE' in text, (
        'Multithread kit must preallocate enough pthread workers for its engine'
    )
    assert 'hardwareConcurrency' in text, (
        'Browser worker allocation must follow the device core count'
    )
    assert 'PTHREAD_POOL_SIZE' not in ' '.join(serial), (
        'The serial kit must remain runnable without browser shared memory or a pthread pool'
    )
