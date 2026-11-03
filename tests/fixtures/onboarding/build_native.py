"""Build the production logger in isolation from the native app and its SDK."""

import hashlib
import json
import os
import subprocess
from pathlib import Path


def identities(source: Path, target: str) -> dict[str, str]:
    fixture = Path(__file__).resolve().parent / 'native'
    paths = {'CMakeLists.txt': fixture / 'CMakeLists.txt', 'probe.cpp': fixture / f'{target}.cpp'}
    if target == 'log_probe':
        paths.update({name: source / 'app/src' / name for name in ['run_log.cpp', 'run_log.hpp']})
    return {name: hashlib.sha256(path.read_bytes()).hexdigest() for name, path in paths.items()}


def require_native(source: Path, directory: Path, target: str) -> Path:
    binary = directory / target
    stamp = directory / f'{target}.identity.json'
    assert binary.is_file() and stamp.is_file(), (
        'Standalone acceptance requires the native probe and its build identity prerequisite'
    )
    identity = json.loads(stamp.read_text(encoding='utf-8'))
    assert identity['inputs'] == identities(source, target), (
        'The standalone probe must be rebuilt after its production source or fixture changes'
    )
    assert identity['binary'] == hashlib.sha256(binary.read_bytes()).hexdigest(), (
        'The standalone acceptance artifact must match the recorded build identity'
    )
    return binary


def build_native(source: Path, destination: Path, target: str) -> Path:
    prefix = Path(os.environ.get('CONDA_PREFIX', source / '.pixi/envs/app'))
    cmake = prefix / 'bin/cmake'
    assert cmake.is_file(), 'The standalone log gate requires the pinned Qt app environment'
    fixture = Path(__file__).resolve().parent / 'native'
    before = identities(source, target)
    for command in [
        [
            str(cmake),
            '-S',
            str(fixture),
            '-B',
            str(destination),
            '-G',
            'Ninja',
            f'-DEDI_SOURCE_ROOT={source}',
            f'-DCMAKE_PREFIX_PATH={prefix}',
        ],
        [str(cmake), '--build', str(destination), '--target', target, '--parallel', '2'],
    ]:
        result = subprocess.run(command, capture_output=True, text=True, check=False, timeout=120)
        assert result.returncode == 0, (
            'The standalone gate must compile the production logger unchanged: '
            + result.stdout
            + result.stderr
        )
    assert before == identities(source, target), (
        'The native probe build refuses source changes during compilation'
    )
    binary = destination / target
    (destination / f'{target}.identity.json').write_text(
        json.dumps({
            'inputs': before,
            'binary': hashlib.sha256(binary.read_bytes()).hexdigest(),
        }),
        encoding='utf-8',
    )
    return binary


def build_logger(source: Path, destination: Path) -> Path:
    return build_native(source, destination, 'log_probe')


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('target', choices=['log_probe', 'payload_probe'])
    parser.add_argument('--source', type=Path, default=Path(__file__).resolve().parents[3])
    parser.add_argument('--build', type=Path)
    arguments = parser.parse_args()
    destination = arguments.build or arguments.source / 'build/onboarding-native'
    print(build_native(arguments.source, destination, arguments.target))
