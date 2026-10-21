"""Assemble real build outputs for the four distribution-licence checks.

Run after core-build, app-build and wasm-build. This fixture copies delivered
files; it never manufactures a component list from the expected matrix.
"""

import argparse
import os
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]


def stage(destination):
    destination.mkdir(parents=True, exist_ok=True)
    desktop = destination / 'desktop'
    subprocess.run(
        ['cmake', '--install', str(ROOT / 'build/app'), '--prefix', str(desktop)], check=True
    )
    wheels = destination / 'wheels'
    wheels.mkdir(exist_ok=True)
    subprocess.run(
        [sys.executable, '-m', 'hatchling', 'build', '-t', 'wheel', '-d', str(wheels)],
        cwd=ROOT,
        check=True,
    )
    built = list(wheels.glob('*.whl'))
    if len(built) != 1:
        raise RuntimeError('The licence fixture needs exactly one freshly built Python wheel')
    with zipfile.ZipFile(built[0]) as wheel:
        wheel.extractall(destination / 'python')
    cli = destination / 'cli'
    (cli / 'bin').mkdir(parents=True, exist_ok=True)
    shutil.copy2(ROOT / 'build/ci/cli/easydiffraction', cli / 'bin/easydiffraction')
    # Only collect sidecars actually emitted beside the CLI. A missing notice
    # remains a failing gate; copying the overview here would conceal that gap.
    for name in ('LICENSE', 'THIRD-PARTY-NOTICES', 'licenses'):
        source = ROOT / 'build/ci/cli' / name
        if source.is_dir():
            shutil.copytree(source, cli / name, dirs_exist_ok=True)
        elif source.is_file():
            shutil.copy2(source, cli / name)
    shutil.copytree(ROOT / 'build/wasm/site', destination / 'web', dirs_exist_ok=True)
    variables = {
        f'EDI_{surface.upper()}_BUNDLE': str(destination / surface)
        for surface in ('desktop', 'web', 'python', 'cli')
    }
    print('\n'.join(f'{name}={value}' for name, value in variables.items()))
    if os.environ.get('GITHUB_ENV'):
        with Path(os.environ['GITHUB_ENV']).open('a', encoding='utf-8') as environment:
            environment.write(''.join(f'{name}={value}\n' for name, value in variables.items()))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=ROOT / 'build/distribution-licences')
    arguments = parser.parse_args()
    if arguments.output.exists():
        raise RuntimeError('Choose a fresh staging directory; stale package files cannot count')
    stage(arguments.output.resolve())
