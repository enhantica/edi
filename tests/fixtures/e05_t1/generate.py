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


def main():
    args = argparse.ArgumentParser(description=__doc__)
    args.add_argument(
        '--only', help='append one newly registered project; retain existing oracles'
    )
    args = args.parse_args()
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
            source = ROOT / 'docs/user/cli' / entry['id'] / 'project'
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
    print(f'CLI oracle complete: {len(manifest["cases"])} projects', flush=True)


if __name__ == '__main__':
    main()
