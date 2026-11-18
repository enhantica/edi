# SPDX-License-Identifier: BSD-3-Clause
"""Build the stability and settings probes with the existing app prerequisites."""

import argparse
import json
import os
import runpy
import subprocess
from pathlib import Path


def build(source, destination):
    prefix = Path(os.environ.get('CONDA_PREFIX', source / '.pixi/envs/app'))
    cmake = prefix / 'bin/cmake'
    for provider, fixture, directory, target, stamp in (
        (
            'application_errors',
            'onboarding/native',
            destination,
            'error_boundary_probe',
            'error_boundary.identity.json',
        ),
        (
            'settings_identity',
            'settings_identity',
            source / 'build/settings-identity',
            'settings_identity_probe',
            'identity.json',
        ),
    ):
        generator = runpy.run_path(str(source / 'tests/fixtures' / provider / 'prepare.py'))
        generator['prepare'](source, directory)
        expected = (
            directory
            / (
                'application_provider.inc'
                if provider == 'application_errors'
                else 'settings_provider.inc'
            )
        ).read_bytes()
        commands = [
            [
                str(cmake),
                '-S',
                str(source / 'tests/fixtures' / fixture),
                '-B',
                str(directory),
                '-G',
                'Ninja',
                f'-DEDI_SOURCE_ROOT={source}',
                f'-DCMAKE_PREFIX_PATH={prefix}',
            ],
            [str(cmake), '--build', str(directory), '--target', target, '--parallel', '4'],
        ]
        for command in commands:
            subprocess.run(command, check=True, timeout=120)
        generator['prepare'](source, directory)
        actual = (
            directory
            / (
                'application_provider.inc'
                if provider == 'application_errors'
                else 'settings_provider.inc'
            )
        ).read_bytes()
        assert actual == expected, (
            'ADR-0062/0091: standalone probe preparation refuses concurrent provider changes'
        )
        (directory / stamp).write_text(json.dumps(generator['identity'](source, directory)))
        print(f'{target}: built and stamped', flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, required=True)
    parser.add_argument('--build', type=Path, required=True)
    arguments = parser.parse_args()
    build(arguments.source.resolve(), arguments.build.resolve())
