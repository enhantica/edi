"""Capture native CLI parity regression pins for the browser's catalogue inputs."""

import hashlib
import json
import subprocess
import sys
from pathlib import Path

import edi

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
CASES = {'lbco': 'pd-neut-cwl_lbco-hrpt', 'ncaf': 'pd-neut-tof_ncaf-wish'}


def digest(project):
    result = hashlib.sha256()
    for path in sorted(project.rglob('*')):
        if path.is_file():
            result.update(path.relative_to(project).as_posix().encode() + b'\0')
            result.update(path.read_bytes())
    return result.hexdigest()


def main():
    extension = Path(edi._edi.__file__)
    if extension.suffix not in {'.so', '.pyd'}:
        raise RuntimeError('Catalogue parity pins require the native compiled extension')
    records = {}
    for case, identity in CASES.items():
        project = ROOT / 'docs/user/cli' / identity / 'project'
        before = digest(project)
        command = [
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
        ]
        run = subprocess.run(command, check=True, capture_output=True, text=True, timeout=30)
        if before != digest(project):
            raise RuntimeError('Catalogue parity capture must retain every input byte')
        fields = dict(line.split('=', 1) for line in run.stdout.splitlines() if '=' in line)
        if fields.get('status') != 'done' or fields.get('converged') != 'true':
            raise RuntimeError('Catalogue parity capture requires a converged moving fit')
        records[case] = {
            'reference': 'Native CLI parity regression pin; not an external correctness oracle',
            'project': project.relative_to(ROOT).as_posix(),
            'project_sha256': before,
            'native_build_commit': edi.__build_commit__,
            'native_extension_sha256': hashlib.sha256(extension.read_bytes()).hexdigest(),
            'status': fields['status'],
            'converged': fields['converged'],
            'reduced_chi_square': float(fields['reduced_chi_square']),
            'rwp': float(fields['rwp']),
            'iterations': int(fields['iterations']),
            'parameters': {
                key: float(value)
                for key, value in fields.items()
                if key.startswith('param.') and key.endswith('.value')
            },
        }
        (HERE / f'catalogue-{case}-native-report.txt').write_text(run.stdout)
    (HERE / 'catalogue-native.json').write_text(json.dumps(records, indent=2) + '\n')


if __name__ == '__main__':
    main()
