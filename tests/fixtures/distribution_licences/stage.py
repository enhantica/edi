"""Assemble real build outputs for the four distribution-licence checks.

Run after the requested surfaces have been built. This fixture copies delivered
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
SURFACES = ('desktop', 'web', 'python', 'cli')


def stage_desktop(destination):
    desktop = destination / 'desktop'
    subprocess.run(
        ['cmake', '--install', str(ROOT / 'build/app'), '--prefix', str(desktop)], check=True
    )


def stage_python(destination):
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


def stage_cli(destination):
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


def stage_web(destination):
    shutil.copytree(ROOT / 'build/wasm/site', destination / 'web', dirs_exist_ok=True)


def parse_surfaces(value):
    surfaces = tuple(value.split(','))
    if len(set(surfaces)) != len(surfaces) or any(item not in SURFACES for item in surfaces):
        raise argparse.ArgumentTypeError('Choose distinct surfaces from: ' + ','.join(SURFACES))
    return surfaces


def stage(destination, surfaces=SURFACES):
    destination.mkdir(parents=True, exist_ok=True)
    producers = {
        'desktop': stage_desktop,
        'web': stage_web,
        'python': stage_python,
        'cli': stage_cli,
    }
    for surface in surfaces:
        producers[surface](destination)
    variables = {
        f'EDI_{surface.upper()}_BUNDLE': str(destination / surface) for surface in surfaces
    }
    print('\n'.join(f'{name}={value}' for name, value in variables.items()))
    if os.environ.get('GITHUB_ENV'):
        with Path(os.environ['GITHUB_ENV']).open('a', encoding='utf-8') as environment:
            environment.write(''.join(f'{name}={value}\n' for name, value in variables.items()))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=ROOT / 'build/distribution-licences')
    parser.add_argument(
        '--surfaces',
        type=parse_surfaces,
        default=SURFACES,
        help='Comma-separated surfaces to stage (default: all four)',
    )
    arguments = parser.parse_args()
    if arguments.output.exists():
        raise RuntimeError('Choose a fresh staging directory; stale package files cannot count')
    stage(arguments.output.resolve(), arguments.surfaces)
