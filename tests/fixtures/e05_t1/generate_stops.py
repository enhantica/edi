"""Freeze actual CLI MaxIter and NoStep reports on explicitly derived inputs.

MaxIter changes only max_iterations to one. NoStep fixes every parameter except
one atom's ADP and sets occupancies to zero, so the free ADP cannot improve chi2.
Both cases use the same registered lbco input and the normal CLI entry point.
"""

import hashlib
import json
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
    cases = []
    original = ROOT / 'docs/user/cli/pd-neut-cwl_lbco-hrpt_start-2/project'
    for kind, expected in [('maxiter', 'max_iter'), ('nostep', 'no_step')]:
        project = HERE / ('stop-' + kind) / 'project'
        if project.exists():
            shutil.rmtree(project)
        shutil.copytree(original, project, ignore=shutil.ignore_patterns('README.md'))
        metadata = project / 'project.edi'
        lines = metadata.read_text().splitlines()
        metadata.write_text(
            '\n'.join(
                '_metadata.title "CLI stop witness"'
                if line.startswith('_metadata.title')
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
        else:
            p = edi.Project.load(str(project))
            for parameter in p.parameters:
                parameter.free = False
            for site in p.structure.atom_sites:
                site.occupancy.value = 0
            p.structure.atom_sites[0].adp_iso.free = True
            p.save()
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
        cases.append({
            'id': 'stop-' + kind,
            'path': project.relative_to(ROOT).as_posix(),
            'mode': 'single',
            'record': record,
            'inputs_sha256': hashes,
            'minimizer': 'crysta (' + record['descent'] + ')',
            'parameters': json.loads(capture.read_text()),
        })
        capture.unlink()
        (HERE / ('stop-' + kind + '.record')).write_text(run.stdout)
    manifest = {
        'edi_sha': subprocess.check_output(
            ['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True
        ).strip(),
        'source': original.relative_to(ROOT).as_posix(),
        'cases': cases,
    }
    (HERE / 'stops.json').write_text(json.dumps(manifest, indent=2) + '\n')


if __name__ == '__main__':
    main()
