"""Shared bounded build-stage preparation; behavioral tests only validate/read it."""

import argparse
import hashlib
import importlib
import json
import os
import subprocess
import sys
from pathlib import Path

from tests.fixtures.joint_series import subject

ROOT = Path(__file__).resolve().parents[3]
PREPARATION_TIMEOUT = 45
COMPILE_TIMEOUT = 30


def configuration(root, engine):
    if engine.__name__ == 'edi':
        sdk = importlib.import_module('tests.conftest').crysta_reference_prefix()
        artifact = Path(engine._edi.__file__).resolve().parents[2]
        libraries = [artifact / 'core/libedi_core.a', sdk / 'lib/libcrysta_core.a']
        includes, defines = [root / 'core/include', sdk / 'include'], ['-DEDI_PROBE']
    else:
        library, headers = subject.selected_core(
            root,
            engine.__file__,
            archive=os.environ.get('JOINT_SERIES_CORE'),
            include=os.environ.get('JOINT_SERIES_INCLUDE'),
        )
        subject.committed_headers(root, headers, engine.__build_commit__)
        libraries, includes, defines = [library], [headers], []
    spec = {
        'engine': engine.__name__,
        'extension': subject.digest(engine.__file__).hex(),
        'archives': {str(p.resolve()): subject.digest(p).hex() for p in libraries},
        'headers': {
            str(p.resolve()): subject.digest(p).hex()
            for directory in includes
            for p in directory.rglob('*')
            if p.is_file()
        },
        'source': {
            str(root / 'tests/fixtures/joint_series' / name): subject.digest(
                root / 'tests/fixtures/joint_series' / name
            ).hex()
            for name in ('starts.cpp', 'subject.py', 'prepare_native.py')
        },
    }
    return spec, libraries, includes, defines


def directory(root, spec):
    key = hashlib.sha256(json.dumps(spec, sort_keys=True).encode()).hexdigest()
    return root / 'build/joint-series-starts' / key


def validate(build, spec):
    receipt, binary = build / 'prepared.json', build / 'starts'
    assert receipt.is_file(), (
        'Native observation requires the shared joint-series-prepare build step'
    )
    actual = json.loads(receipt.read_text())
    assert actual['spec'] == spec, (
        'Prepared native evidence must match the selected build and fixture sources'
    )
    assert binary.is_file(), 'Prepared native observation requires its built executable'
    assert actual['binary_sha256'] == subject.digest(binary).hex(), (
        'Prepared native observation must retain the executable built by its attested recipe'
    )
    return binary


def prepared(root, engine):
    spec, *_ = configuration(root, engine)
    binary = validate(directory(root, spec), spec)
    if engine.__name__ == 'crysta':
        proof = subprocess.run(
            [str(binary), '--identity'], capture_output=True, text=True, check=True, timeout=5
        )
        subject.identity(proof.stdout, engine.__build_commit__)
    return binary


def build(root, engine):
    spec, libraries, includes, defines = configuration(root, engine)
    output = directory(root, spec)
    if (output / 'prepared.json').is_file():
        return prepared(root, engine)
    output.mkdir(parents=True, exist_ok=True)
    lock = output / 'preparing'
    lock.mkdir()  # simultaneous producers refuse; consumers never wait or build
    try:
        temporary = output / 'starts.pending'
        prefix = Path(sys.prefix)
        command = [
            os.environ.get('CXX', 'c++'),
            '-std=c++20',
            '-O0',
            *defines,
            *['-I' + str(p) for p in [*includes, prefix / 'include/eigen3']],
            str(root / 'tests/fixtures/joint_series/starts.cpp'),
            *map(str, libraries),
            '-L' + str(prefix / 'lib'),
            '-Wl,-rpath,' + str(prefix / 'lib'),
            '-lsleef',
            '-fopenmp',
            '-pthread',
            '-o',
            str(temporary),
        ]
        subprocess.run(command, check=True, timeout=COMPILE_TIMEOUT)
        temporary.replace(output / 'starts')
        receipt = {'spec': spec, 'binary_sha256': subject.digest(output / 'starts').hex()}
        (output / 'prepared.json').write_text(json.dumps(receipt, sort_keys=True) + '\n')
    finally:
        lock.rmdir()
    return prepared(root, engine)


def declared_for(tasks, consumers):
    assert 'joint-series-prepare' in tasks, (
        'Native observation needs one declared preparation owner'
    )

    def reaches(name, seen):
        if name == 'joint-series-prepare':
            return True
        if name in seen:
            return False
        task = tasks.get(name, {})
        dependencies = task.get('depends-on', []) if isinstance(task, dict) else []
        return any(
            reaches(dep if isinstance(dep, str) else dep['task'], seen | {name})
            for dep in dependencies
        )

    for consumer in consumers:
        assert reaches(consumer, set()), (
            'Every behavior or runtime-measurement entry must prepare its native observer first'
        )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--engine', choices=('crysta', 'edi'), required=True)
    parser.add_argument('--worker', action='store_true')
    args = parser.parse_args()
    if args.worker:
        print(build(ROOT, importlib.import_module(args.engine)), flush=True)
    else:
        subprocess.run(
            [
                sys.executable,
                '-m',
                'tests.fixtures.joint_series.prepare_native',
                '--engine',
                args.engine,
                '--worker',
            ],
            check=True,
            timeout=PREPARATION_TIMEOUT,
        )


if __name__ == '__main__':
    main()
