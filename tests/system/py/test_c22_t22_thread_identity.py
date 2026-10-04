from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

from conftest import corpus_case_dir

ROOT = Path(__file__).resolve().parents[3]
IDENTITY_PROBE = r"""
import json
import sys
import edi

project = edi.Project.load(sys.argv[1])
result = project.analysis.fit()
print(json.dumps({
    'banks': [
        {
            'name': bank.name,
            'reduced_chi_square': float(bank.reduced_chi_square).hex(),
            'rwp': float(bank.rwp).hex(),
        }
        for bank in result.banks
    ],
    'converged': bool(result.converged),
    'iterations': int(result.iterations),
    'reduced_chi_square': float(result.reduced_chi_square).hex(),
    'rwp': float(result.rwp).hex(),
    'status': str(result.status),
    'uncertainty': {key: float(value).hex() for key, value in result.uncertainty.items()},
    'values': {key: float(value).hex() for key, value in result.values.items()},
}, sort_keys=True))
"""


def _fit_identity(project: Path, threads: int) -> dict[str, Any]:
    environment = os.environ.copy()
    environment.update({
        'OMP_DYNAMIC': 'FALSE',
        'OMP_NUM_THREADS': str(threads),
        'OMP_WAIT_POLICY': 'passive',
    })
    completed = subprocess.run(
        [sys.executable, '-c', IDENTITY_PROBE, str(project)],
        cwd=ROOT,
        env=environment,
        check=False,
        capture_output=True,
        text=True,
        timeout=120,
    )
    assert completed.returncode == 0, (
        'the isolated edi fit-identity probe must complete successfully; output:\n'
        + completed.stdout
        + completed.stderr
    )
    return json.loads(completed.stdout.splitlines()[-1])


def test_c22_t22_edi_fit_is_byte_identical_across_thread_counts() -> None:
    project = corpus_case_dir('cosio-d20-s1') / 'project'
    serial = _fit_identity(project, 1)
    threaded = _fit_identity(project, 4)
    assert threaded == serial, (
        'ADR-0034 makes the threading policy a pure performance choice; edi fit values, '
        'uncertainties, metrics, status and iteration count must remain bit-identical'
    )
