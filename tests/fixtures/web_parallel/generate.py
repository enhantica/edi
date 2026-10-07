"""Capture scientific fit operands only from an unchanged native CLI."""

import argparse
import hashlib
import importlib
import json
import shutil
import subprocess
import tempfile
from pathlib import Path

from tests.fixtures.web_parallel.numeric import scientific

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
CASES = {
    'lbco': 'docs/user/cli/pd-neut-cwl_lbco-hrpt_start-4/project',
    'ncaf': 'docs/user/cli/pd-neut-tof_ncaf-wish-5bank_start-5/project',
}


def generate(cli, producer, *, edi=False):
    for name, relative in CASES.items():
        with tempfile.TemporaryDirectory(prefix='native-web-reference-') as scratch:
            project = Path(scratch) / 'project'
            shutil.copytree(ROOT / relative, project)
            run = subprocess.run(
                [
                    str(cli.resolve()),
                    *(['-m', 'edi'] if edi else []),
                    'fit',
                    str(project),
                    '--report',
                    'machine',
                    '--verbosity',
                    'full',
                ],
                capture_output=True,
                text=True,
                check=True,
                timeout=30,
            )
            fields = dict(line.split('=', 1) for line in run.stdout.splitlines() if '=' in line)
            if fields.get('status') != 'done' or fields.get('converged') != 'true':
                raise RuntimeError('native capture requires a completed moving fit report')
            native = cli
            if edi:
                native = Path(importlib.import_module('edi')._edi.__file__)
            fixture = {
                'reference': 'unchanged native serial/OpenMP core, independent of wasm',
                'producer': producer,
                'executable_sha256': hashlib.sha256(native.read_bytes()).hexdigest(),
                'project': relative,
                'command': ['python', '-m', 'edi', 'fit', relative]
                if edi
                else ['crysta', 'fit', relative],
                'scientific': scientific(project),
                'relative_tolerance': 1e-9,
                'absolute_tolerance': 1e-11,
            }
            (HERE / (name + '-native.json')).write_text(json.dumps(fixture, indent=2) + '\n')
            (HERE / (name + '-native-report.txt')).write_text(run.stdout)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('native_cli', type=Path)
    parser.add_argument('--producer', required=True)
    parser.add_argument('--edi', action='store_true')
    args = parser.parse_args()
    generate(args.native_cli, args.producer, edi=args.edi)
