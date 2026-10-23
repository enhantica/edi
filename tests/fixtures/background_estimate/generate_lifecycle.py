"""Freeze disposable lifecycle inputs, labelled as state witnesses rather than physics oracles."""

import argparse
import hashlib
import json
import re
import shutil
import subprocess
from pathlib import Path

import edi

from tests.fixtures.background_estimate.lifecycle import (
    OPTIONS,
    model_input,
    persisted_points,
    scan_input,
)
from tests.fixtures.background_estimate.settings import write_settings

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, required=True)
    parser.add_argument('--engine-writer', type=Path, required=True)
    args = parser.parse_args()
    manifest = {
        'claim': (
            'REGRESSION INPUT: saved estimation state; no fitted or calculated physics oracle'
        ),
        'repository': 'https://github.com/enhantica/edi',
        'engine_commit': (ROOT / 'build/ci/.crysta-linked-sha').read_text().strip(),
        'command': 'python -m tests.fixtures.background_estimate.generate_lifecycle '
        '--source docs/user/cli/pd-neut-cwl_lbco-hrpt_start-2/project '
        '--engine-writer ../background-reference/build/save_auto',
        'cases': {},
    }
    for name in [
        'lifecycle-model',
        'lifecycle-auto',
        'lifecycle-guided',
        'lifecycle-excluded',
        'lifecycle-scan-independent',
        'lifecycle-scan-sequential',
    ]:
        destination = HERE / 'projects' / name
        if destination.exists():
            raise FileExistsError('A committed lifecycle input cannot be overwritten: ' + name)
        if name.startswith('lifecycle-scan-'):
            scan_input(destination, args.source, edi, name.removeprefix('lifecycle-scan-'))
        else:
            model_input(destination, args.source)
        if name in {'lifecycle-auto', 'lifecycle-guided'}:
            write_settings(destination, {**OPTIONS, 'mode': 'auto'}, experiment='hrpt')
            calculated = destination.with_name(destination.name + '-calculated')
            subprocess.run(
                [
                    str(args.engine_writer.resolve()),
                    str(destination),
                    str(calculated),
                    'guided' if name == 'lifecycle-guided' else 'data-only',
                ],
                check=True,
                capture_output=True,
                text=True,
                timeout=10,
            )
            shutil.rmtree(destination)
            calculated.rename(destination)
        elif name == 'lifecycle-excluded':
            path = destination / 'experiments/hrpt.edi'
            text = path.read_text()
            marker = (
                'loop_\n_excluded_region.id\n_excluded_region.start\n'
                '_excluded_region.end\ngap -1000 1000\n'
            )
            text, count = re.subn(r'(?ms)loop_\n_excluded_region\..*?(?=\nloop_|\Z)', marker, text)
            if count != 1:
                raise ValueError(
                    'The excluded-data lifecycle input needs its one original exclusion loop'
                )
            path.write_text(text)
            write_settings(destination, {**OPTIONS, 'mode': 'auto'}, experiment='hrpt')
        manifest['cases'][name] = {
            'points': persisted_points(destination, experiment='hrpt'),
            'sha256': {
                p.relative_to(destination).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
                for p in sorted(destination.rglob('*'))
                if p.is_file()
            },
        }
    target = HERE / 'lifecycle-cases.json'
    target.write_text(json.dumps(manifest, indent=2) + '\n')
    print('Generated lifecycle inputs with the pinned engine', manifest['engine_commit'])


if __name__ == '__main__':
    main()
