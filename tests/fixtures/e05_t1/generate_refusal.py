"""CLI-authored failed-fit input: the measured lbco project has no free parameters.

The app may open and calculate this input, but fitting must reject its empty free set.
No original project is edited; the private derived input and CLI reason are fixtures.
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


def main():
    project = HERE / 'failed-fit/project'
    if project.exists():
        shutil.rmtree(project)
    source = ROOT / 'docs/user/cli/pd-neut-cwl_lbco-hrpt_start-2/project'
    shutil.copytree(source, project, ignore=shutil.ignore_patterns('README.md'))
    metadata = project / 'project.edi'
    metadata.write_text(
        '\n'.join(
            '_metadata.title "CLI failed-fit witness"'
            if line.startswith('_metadata.title')
            else line
            for line in metadata.read_text().splitlines()
        )
        + '\n'
    )
    p = edi.Project.load(str(project))
    for parameter in p.parameters:
        parameter.free = False
    p.save()
    run = subprocess.run(
        [
            sys.executable,
            '-m',
            'edi',
            'fit',
            str(project),
            '--dry',
            '--report',
            'machine',
            '--verbosity',
            'full',
        ],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    record = dict(line.split('=', 1) for line in run.stdout.splitlines())
    if (
        not run.returncode
        or record.get('status') != 'error'
        or 'no free parameters' not in run.stderr
    ):
        raise RuntimeError('CLI did not reject the independently specified empty free set')
    fixture = {
        'path': project.relative_to(ROOT).as_posix(),
        'record': record,
        'reason': 'no free parameters',
        'edi_sha': subprocess.check_output(
            ['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True
        ).strip(),
        'inputs_sha256': {
            p.relative_to(project).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in sorted(project.rglob('*'))
            if p.is_file()
        },
    }
    (HERE / 'refusal.json').write_text(json.dumps(fixture, indent=2) + '\n')


if __name__ == '__main__':
    main()
