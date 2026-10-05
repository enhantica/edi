"""gate 1: freeze the CLI's fits, never an app/FitJob result.

Run with the pinned default environment after core-build. Every registered single/joint
project is fitted on a disposable copy, including non-executing projects. The committed
inputs are hashed and never edited. Full machine reports retain the CLI precision.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import edi
import yaml

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent


def arguments():
    args = argparse.ArgumentParser(description=__doc__)
    args.add_argument(
        '--only', help='append one newly registered project; retain existing oracles'
    )
    args.add_argument(
        '--input-project', help='author one new registered case from its independent fixture input'
    )
    args = args.parse_args()
    if args.input_project and not args.only:
        raise ValueError('an independent authoring input requires exactly one new registered case')
    authored = (ROOT / args.input_project).resolve() if args.input_project else None
    if authored is not None:
        authored.relative_to(ROOT)
        if not (authored / 'project.edi').is_file():
            raise ValueError('the independent authoring input must be a complete local project')
    args.input_path = authored
    return args


def main():
    args = arguments()
    linked_engine_source = (
        (Path(sys.modules['edi._edi'].__file__).resolve().parents[2] / '.crysta-linked-sha')
        .read_text()
        .strip()
    )
    registry = yaml.safe_load((ROOT / 'docs/user/cli/projects.yml').read_text())
    manifest = {
        'reference': 'python -m edi fit <private-copy> --report machine --verbosity full',
        'edi_sha': subprocess.check_output(
            ['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True
        ).strip(),
        'crysta_sdk': linked_engine_source,
        'cases': [],
    }
    if args.only:
        manifest = json.loads((HERE / 'cli.json').read_text())
        if args.only in {row['id'] for row in manifest['cases']}:
            raise RuntimeError('append-only generation refuses replacing an existing CLI oracle')
    with tempfile.TemporaryDirectory(prefix='cli-fit-reference-') as temporary:
        for entry in registry['projects']:
            if args.only and entry['id'] != args.only:
                continue
            source = args.input_path or ROOT / 'docs/user/cli' / entry['id'] / 'project'
            mode = str(edi.Project.load(str(source)).fitting_mode)
            if mode not in {'single', 'joint'}:
                continue
            print(f'CLI oracle: {entry["id"]} ({mode})', flush=True)
            private = Path(temporary) / entry['id']
            shutil.copytree(source, private)
            capture = private / 'parameters.json'
            # Trace the CLI's own return boundary: no extra fit and no reload of rounded values.
            wrapper = """
import edi, json, runpy, sys
from pathlib import Path
capture = Path(sys.argv.pop(1))
def capture_return(frame, event, result):
    if (event == 'return' and frame.f_code.co_name == '_fit'
            and frame.f_globals.get('__package__') == 'edi'):
        project = frame.f_locals['project']
        rows = [{'value': float(p.value), 'uncertainty': p.uncertainty,
                 'free': bool(p.free)} for p in project.parameters]
        capture.write_text(json.dumps(rows))
    return capture_return
sys.settrace(capture_return)
runpy.run_module('edi', run_name='__main__')
"""
            command = [
                sys.executable,
                '-c',
                wrapper,
                str(capture),
                'fit',
                str(private),
                '--report',
                'machine',
                '--verbosity',
                'full',
            ]
            run = subprocess.run(
                command, cwd=ROOT, text=True, capture_output=True, timeout=1800, check=False
            )
            if run.returncode:
                raise RuntimeError(
                    f'CLI reference refused {entry["id"]}: {run.stdout}\n{run.stderr}'
                )
            record = dict(line.split('=', 1) for line in run.stdout.splitlines())
            if record['mode'] != mode or not record.get('status'):
                raise RuntimeError(f'CLI reference omitted mode/status for {entry["id"]}')
            inputs = {
                p.relative_to(source).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
                for p in sorted(source.rglob('*'))
                if p.is_file()
            }
            (HERE / (entry['id'] + '.record')).write_text(run.stdout)
            manifest['cases'].append({
                'id': entry['id'],
                'path': source.relative_to(ROOT).as_posix(),
                'mode': mode,
                'minimizer': 'crysta (' + record['descent'] + ')',
                'inputs_sha256': inputs,
                'record': record,
                'stderr': run.stderr,
                'parameters': json.loads(capture.read_text()),
                **(
                    {
                        'edi_sha': subprocess.check_output(
                            ['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True
                        ).strip(),
                        'crysta_build_commit': linked_engine_source,
                    }
                    if args.only
                    else {}
                ),
            })
    write_artifacts(manifest, args.only, args.input_path)
    print(f'CLI oracle complete: {len(manifest["cases"])} projects', flush=True)


def write_artifacts(manifest, case_id=None, authoring_input=None):
    """Write captured records; validate a new independent input without another fit."""
    if authoring_input is not None:
        row = next(row for row in manifest['cases'] if row['id'] == case_id)
        inputs = {
            p.relative_to(authoring_input).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in sorted(authoring_input.rglob('*')) if p.is_file()
        }
        if inputs != row['inputs_sha256']:
            raise ValueError('captured CLI inputs must match the independent authoring project')
        row['path'] = f'docs/user/cli/{case_id}/project'
        row['authoring_input'] = authoring_input.relative_to(ROOT).as_posix()
    (HERE / 'cli.json').write_text(json.dumps(manifest, indent=2) + '\n')
    # Standard-library-only C++ expectations, usable without JSON or Qt in the core tier.
    lines = [
        '#pragma once',
        '#include <map>',
        '#include <string>',
        '#include <vector>',
        'namespace e05_t1_fixture {',
        'struct Case { std::string id, path, mode; std::map<std::string, std::string> record; };',
        'inline std::vector<Case> cases() { return {',
    ]
    for row in manifest['cases']:
        fields = ','.join(
            '{' + json.dumps(k) + ',' + json.dumps(v) + '}' for k, v in row['record'].items()
        )
        lines.append(
            '{'
            + ','.join(json.dumps(row[k]) for k in ('id', 'path', 'mode'))
            + ',{'
            + fields
            + '}},'
        )
    lines.extend(['}; }', '}'])
    (HERE / 'cli.hpp').write_text('\n'.join(lines) + '\n')


if __name__ == '__main__':
    main()
