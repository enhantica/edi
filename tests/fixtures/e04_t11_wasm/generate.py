"""Capture the native CLI oracle; never execute a wasm artifact."""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path

import edi

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
PROJECT = ROOT / 'docs/user/cli/pd-neut-cwl_lbco-hrpt_start-4/project'


def project_digest():
    digest = hashlib.sha256()
    for path in sorted(PROJECT.rglob('*')):
        if path.is_file():
            digest.update(path.relative_to(PROJECT).as_posix().encode() + b'\0')
            digest.update(path.read_bytes())
    return digest.hexdigest()


def main():
    extension = Path(edi._edi.__file__)
    if extension.suffix not in {'.so', '.pyd'}:
        raise RuntimeError('oracle capture requires a native compiled edi extension')
    command = [
        sys.executable,
        '-m',
        'edi',
        'fit',
        str(PROJECT),
        '--dry',
        '--report',
        'machine',
        '--verbosity',
        'full',
    ]
    before = project_digest()
    run = subprocess.run(command, capture_output=True, text=True, check=True, timeout=20)
    if project_digest() != before:
        raise RuntimeError('native dry fit changed the committed project')
    fields = dict(line.split('=', 1) for line in run.stdout.splitlines() if '=' in line)
    parameters = {
        key: float(value)
        for key, value in fields.items()
        if key.startswith('param.') and key.endswith('.value')
    }
    if fields.get('status') != 'done' or fields.get('converged') != 'true' or not parameters:
        raise RuntimeError('native oracle must be a completed moving fit')
    fixture = {
        'schema': 1,
        'reference': 'native CLI, independent of wasm',
        'project': PROJECT.relative_to(ROOT).as_posix(),
        'project_sha256': before,
        'native_build_commit': edi.__build_commit__,
        'native_extension_sha256': hashlib.sha256(extension.read_bytes()).hexdigest(),
        'command': [
            'python',
            '-m',
            'edi',
            'fit',
            '<committed project>',
            '--dry',
            '--report',
            'machine',
            '--verbosity',
            'full',
        ],
        'status': fields['status'],
        'converged': fields['converged'],
        'reduced_chi_square': float(fields['reduced_chi_square']),
        'parameters': parameters,
        'relative_tolerance': 1e-9,
        'absolute_tolerance': 1e-11,
    }
    (HERE / 'native-report.txt').write_text(run.stdout)
    (HERE / 'native.json').write_text(json.dumps(fixture, indent=2) + '\n')


if __name__ == '__main__':
    main()
