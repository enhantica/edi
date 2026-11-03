"""Freeze actual CLI MaxIter and NoStep reports on explicitly derived inputs.

MaxIter changes only max_iterations to one. NoStep couples a free driver to a
constant background and a bounded March fraction: every improving trial leaves
the domain. Both use the registered LBCO input and the normal CLI entry point.
"""

import argparse
import hashlib
import json
import runpy
import shutil
import subprocess
import sys
from pathlib import Path

import edi

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
WRAPPER = """
import edi, json, runpy, sys
from pathlib import Path
capture = Path(sys.argv.pop(1))
def capture_return(frame, event, result):
    if (event == 'return' and frame.f_code.co_name == '_fit'
            and frame.f_globals.get('__package__') == 'edi'):
        p = frame.f_locals['project']
        capture.write_text(json.dumps([{'value':float(v.value),
            'uncertainty':v.uncertainty,'free':bool(v.free)} for v in p.parameters]))
    return capture_return
sys.settrace(capture_return)
runpy.run_module('edi', run_name='__main__')
"""


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--only', choices=('maxiter', 'nostep'))
    args = parser.parse_args()
    manifest = json.loads((HERE / 'stops.json').read_text()) if args.only else {}
    cases = {row['id']: row for row in manifest.get('cases', [])}
    materialize = runpy.run_path(str(HERE / 'stop_projects.py'))['materialize']
    original = ROOT / 'docs/user/cli/pd-neut-cwl_lbco-hrpt_start-2/project'
    for kind, expected in [('maxiter', 'max_iter'), ('nostep', 'no_step')]:
        if args.only and kind != args.only:
            continue
        project = HERE / ('stop-' + kind) / 'project'
        if kind == 'nostep':
            materialize(edi, original, project, stalled=True)
        else:
            if project.exists():
                shutil.rmtree(project)
            shutil.copytree(original, project, ignore=shutil.ignore_patterns('README.md'))
        metadata = project / 'project.edi'
        lines = metadata.read_text().splitlines()
        metadata.write_text(
            '\n'.join(
                '_metadata.title "CLI stop witness"'
                if line.startswith('_metadata.title')
                else '_metadata.purpose "fit"'
                if line.startswith('_metadata.purpose')
                else line
                for line in lines
            )
            + '\n'
        )
        if kind == 'maxiter':
            analysis = project / 'analysis/analysis.edi'
            analysis.write_text(
                analysis.read_text().replace(
                    '_minimizer.max_iterations 1000', '_minimizer.max_iterations 1'
                )
            )
        hashes = {
            p.relative_to(project).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in sorted(project.rglob('*'))
            if p.is_file()
        }
        capture = project.parent / 'parameters.json'
        run = subprocess.run(
            [
                sys.executable,
                '-c',
                WRAPPER,
                str(capture),
                'fit',
                str(project),
                '--dry',
                '--report',
                'machine',
                '--verbosity',
                'full',
            ],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
        record = dict(line.split('=', 1) for line in run.stdout.splitlines())
        if run.returncode or record.get('status') != expected:
            raise RuntimeError('CLI stop witness did not reach ' + expected + ': ' + run.stderr)
        case = {
            'id': 'stop-' + kind,
            'path': project.relative_to(ROOT).as_posix(),
            'mode': 'single',
            'record': record,
            'inputs_sha256': hashes,
            'minimizer': 'crysta (' + record['descent'] + ')',
            'parameters': json.loads(capture.read_text()),
        }
        if kind == 'nostep':
            case['producer'] = {
                'edi_sha': subprocess.check_output(
                    ['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True
                ).strip(),
                'crysta_sdk': (
                    Path(sys.modules['edi._edi'].__file__).resolve().parents[2]
                    / '.crysta-linked-sha'
                )
                .read_text()
                .strip(),
            }
            case['closed_form'] = {
                'driver_start': 0.0,
                'observed': [-1.0, -1.0, -1.0],
                'calculated': [0.0, 0.0, 0.0],
                'jacobian': [1.0, 1.0, 1.0],
                'chi_square': 3.0,
                'predicted_gain': 3.0,
                'chi_square_tolerance': 1e-6,
                'blocked_by': 'march_random_fract = driver, domain [0, 1]',
            }
        cases[case['id']] = case
        capture.unlink()
        (HERE / ('stop-' + kind + '.record')).write_text(run.stdout)
    if not args.only:
        manifest = {
            'edi_sha': subprocess.check_output(
                ['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True
            ).strip(),
            'source': original.relative_to(ROOT).as_posix(),
        }
    manifest['cases'] = list(cases.values())
    (HERE / 'stops.json').write_text(json.dumps(manifest, indent=2) + '\n')


if __name__ == '__main__':
    main()
