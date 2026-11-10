"""Capture scientific fit operands only from an unchanged native CLI."""

import argparse
import hashlib
import importlib
import json
import shutil
import subprocess
import tempfile
from pathlib import Path

from tests.fixtures.web_parallel.numeric import (
    compare_scientific,
    scientific,
    uncertainty_tolerances,
)

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
CASES = {
    'lbco': 'docs/user/cli/pd-neut-cwl_lbco-hrpt_start-4/project',
    'ncaf': 'docs/user/cli/pd-neut-tof_ncaf-wish-5bank_start-5/project',
}


def retain_conditioning(name, fixture, previous):
    """Keep the independent matrix only if every original fitted operand still agrees."""
    old = json.loads((previous / (name + '-native.json')).read_text())
    conditioning = json.loads((previous / (name + '-conditioning.json')).read_text())
    uncertainty_tolerances(old['scientific'], conditioning)
    current_model = {
        k: v for k, v in fixture['scientific'].items() if not k.startswith('analysis/')
    }
    compare_scientific(
        {**current_model, 'analysis/analysis.edi': old['scientific']['analysis/analysis.edi']},
        old['scientific'],
        old['relative_tolerance'],
        old['absolute_tolerance'],
        conditioning=conditioning,
    )
    old_scalars = dict(old['scientific']['analysis/analysis.edi'])
    current_scalars = dict(
        row for row in fixture['scientific']['analysis/analysis.edi'] if len(row) == 2
    )
    compare_scientific(
        {'fit': [[tag, current_scalars[tag]] for tag in old_scalars]},
        {'fit': list(map(list, old_scalars.items()))},
        old['relative_tolerance'],
        old['absolute_tolerance'],
    )
    if any(binding[0].startswith('analysis/') for binding in conditioning['bindings']):
        raise ValueError('schema-only capture cannot move a conditioned analysis operand')
    conditioning['scientific_sha256'] = hashlib.sha256(
        json.dumps(fixture['scientific'], sort_keys=True).encode()
    ).hexdigest()
    conditioning['schema_capture_producer'] = fixture['producer']
    # The preserved row coordinates, native matrix and physical bounds must still be total.
    uncertainty_tolerances(fixture['scientific'], conditioning)
    (HERE / (name + '-conditioning.json')).write_text(json.dumps(conditioning, indent=2) + '\n')


def generate(cli, producer, *, edi=False, conditioning_from=None):
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
                timeout=120,
            )
            fields = dict(line.split('=', 1) for line in run.stdout.splitlines() if '=' in line)
            if fields.get('status') != 'done' or fields.get('converged') != 'true':
                raise RuntimeError('native capture requires a completed moving fit report')
            native = cli
            if edi:
                native = Path(importlib.import_module('edi')._edi.__file__)
            pre_fit = None
            if edi:
                capture = subprocess.run(
                    [
                        str(cli.resolve()),
                        '-c',
                        """import edi, json, sys
project = edi.Project.load(sys.argv[1])
record = {}
def start(preamble):
    record['initial_reduced_chi_square'] = preamble.pre_fit.reduced_chi_square
outcome = project.analysis.fit(on_start=start)
record.update(final_reduced_chi_square=outcome.reduced_chi_square,
              iterations=outcome.iterations, rwp=outcome.rwp)
print(json.dumps(record))""",
                        str(ROOT / relative),
                    ],
                    capture_output=True,
                    text=True,
                    check=True,
                    timeout=120,
                )
                pre_fit = json.loads(capture.stdout)
            fixture = {
                'reference': 'unchanged native serial/OpenMP core, independent of wasm',
                'native_start_and_finish': pre_fit,
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
            if conditioning_from is not None:
                retain_conditioning(name, fixture, conditioning_from)
            (HERE / (name + '-native.json')).write_text(json.dumps(fixture, indent=2) + '\n')
            (HERE / (name + '-native-report.txt')).write_text(run.stdout)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('native_cli', type=Path)
    parser.add_argument('--producer', required=True)
    parser.add_argument('--edi', action='store_true')
    parser.add_argument('--conditioning-from', type=Path)
    args = parser.parse_args()
    generate(
        args.native_cli, args.producer, edi=args.edi, conditioning_from=args.conditioning_from
    )
