"""Stage a seeded scan with the owner's original project and pattern grid."""

import argparse
import hashlib
import json
import shutil
import zipfile
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent


def full_scan(archive, destination):
    """Verify the external archive before staging its original complete scan."""
    expected = json.loads((HERE / 'scan-source.json').read_text())['archive_sha256']
    with archive.open('rb') as stream:
        actual = hashlib.file_digest(stream, 'sha256').hexdigest()
    if actual != expected:
        raise ValueError('The nightly scan must use the exact owner archive')
    destination.mkdir(parents=True, exist_ok=False)
    with zipfile.ZipFile(archive) as source:
        for member in source.infolist():
            target = (destination / member.filename).resolve()
            if not target.is_relative_to(destination.resolve()):
                raise ValueError('An archive member cannot leave its destination')
            if member.is_dir():
                target.mkdir(parents=True, exist_ok=True)
            else:
                target.parent.mkdir(parents=True, exist_ok=True)
                with source.open(member) as incoming, target.open('wb') as outgoing:
                    shutil.copyfileobj(incoming, outgoing)
    return destination / '44k_project'


def reduced_scan(destination, count=4000):
    """Copy the small source files, then vary only the observed intensities."""
    if not 1 <= count <= 4000:
        raise ValueError('The reduced scan contains between one and 4000 files')
    source = HERE / 'scan'
    manifest = json.loads((HERE / 'scan-source.json').read_text())
    for member, digest in manifest['members'].items():
        if hashlib.sha256((source / member).read_bytes()).hexdigest() != digest:
            raise ValueError('The owner scan source differs: ' + member)
    shutil.copytree(source / '44k_project', destination / '44k_project')
    folder = destination / '44k_data'
    folder.mkdir()
    name = 'scan-0514_pilatus_integrated_0000.xy'
    template = source / '44k_data' / name
    shutil.copyfile(template, folder / name)
    rows = [
        tuple(map(float, line.split()))
        for line in template.read_text().splitlines()
        if line.strip() and not line.startswith('#')
    ]
    rng = np.random.default_rng(514)
    for index in range(1, count):
        pattern = folder / f'scan-0514_pilatus_integrated_{index:04d}.xy'
        pattern.write_text(
            ''.join(f'{x:.4f} {max(0, y + rng.uniform(-0.01, 0.01)):.6f}\n' for x, y in rows)
        )
    return destination / '44k_project'


def tab_scan(scan, destination):
    """Stage the same datasets with a fitted template for the every-tab run."""
    data = scan.parent / '44k_data'
    template = 'scan-0514_pilatus_integrated_0000.xy'
    second = data / 'scan-0514_pilatus_integrated_0001.xy'
    fitted = HERE / 'tab-fit'
    original = HERE / 'scan'

    def samples(path):
        return [
            line.split()
            for line in path.read_bytes().splitlines()
            if line.strip() and not line.lstrip().startswith(b'#')
        ]

    if samples(data / template) != samples(original / '44k_data' / template):
        raise ValueError('The saved template fit requires the original measured samples')
    members = json.loads((HERE / 'scan-source.json').read_text())['members']
    for member in members:
        if member.startswith('44k_project/'):
            relative = Path(member).relative_to('44k_project')
            if (scan / relative).read_bytes() != (original / member).read_bytes():
                raise ValueError('The saved template fit requires the original project: ' + member)

    results = json.loads((fitted / 'second-pattern.json').read_text())
    result_file = results.get(hashlib.sha256(second.read_bytes()).hexdigest())
    if result_file is None:
        raise ValueError('The saved second fit requires its original measured samples')

    project = destination / '44k_project'
    shutil.copytree(scan, project)
    # The analysis keeps its original relative path to the entire scan.
    (destination / '44k_data').symlink_to(data.resolve(), target_is_directory=True)
    shutil.copytree(fitted / 'project', project, dirs_exist_ok=True)
    shutil.copyfile(fitted / result_file, project / 'analysis/results.csv')
    return project


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('destination', type=Path)
    parser.add_argument('--count', type=int, default=4000)
    options = parser.parse_args()
    print(reduced_scan(options.destination, options.count))
