"""Build the actual loaded-correlation view with a counting observer around its numeric reads."""

import argparse
import hashlib
import json
import os
import shutil
import subprocess
from pathlib import Path


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--root', type=Path, required=True)
    parser.add_argument('--build', type=Path, required=True)
    parser.add_argument('--sdk', type=Path, required=True)
    parser.add_argument('--core', type=Path, required=True)
    args = parser.parse_args()
    source = args.build / 'source'
    fixture = source / 'tests/fixtures/loaded_correlation_cache'
    view = source / 'app/src'
    view.mkdir(parents=True, exist_ok=True)
    shutil.copytree(Path(__file__).parent, fixture, dirs_exist_ok=True)
    inputs = {}
    for name in ['correlation_view_model.cpp', 'correlation_view_model.hpp']:
        original = args.root / 'app/src' / name
        shutil.copy2(original, view / name)
        inputs[str(original)] = hashlib.sha256(original.read_bytes()).hexdigest()
    copied = view / 'correlation_view_model.cpp'
    original = copied.read_text()
    marker = 'kept.values.push_back(row->correlation.get());'
    if original.count(marker) != 1:
        message = 'The numeric-read observer must reach the one real row-to-cache copy'
        raise RuntimeError(message)
    copied.write_text(
        original.replace(marker, 'kept.values.push_back(observed_correlation_value(*row));')
    )
    inputs['numeric_read_observer'] = hashlib.sha256(copied.read_bytes()).hexdigest()
    inputs[str(args.core)] = hashlib.sha256(args.core.read_bytes()).hexdigest()
    (args.build / 'inputs.json').write_text(json.dumps(inputs, indent=2) + '\n')
    subprocess.run(
        [
            'cmake',
            '-S',
            str(fixture),
            '-B',
            str(args.build / 'cmake'),
            '-G',
            'Ninja',
            '-DCMAKE_BUILD_TYPE=Release',
            '-DCMAKE_PREFIX_PATH=' + str(args.sdk) + ';' + os.environ['CONDA_PREFIX'],
            '-Dcrysta_DIR=' + str(args.sdk / 'lib/cmake/crysta'),
            '-DEDI_INCLUDE=' + str(args.root / 'core/include'),
            '-DEDI_VIEW=' + str(view),
            '-DEDI_CORE=' + str(args.core),
        ],
        check=True,
    )
    subprocess.run(
        ['cmake', '--build', str(args.build / 'cmake'), '--target', 'cache_probe', '-j', '2'],
        check=True,
    )


if __name__ == '__main__':
    main()
