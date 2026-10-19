"""Run the project-page checks once per test session and input."""

import os
import subprocess
from functools import cache
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]


@cache
def _projects_result(_session, binary, reference):
    environment = {
        **os.environ,
        'QT_QPA_PLATFORM': 'offscreen',
        'QT_QUICK_BACKEND': 'software',
        'EDI_ACCEPTANCE_REFERENCE': reference,
        'OMP_NUM_THREADS': '1',
        'OPENBLAS_NUM_THREADS': '1',
    }
    environment.pop('PYTEST_CURRENT_TEST', None)
    try:
        return subprocess.run(
            [
                binary,
                '-input',
                str(ROOT / 'tests/unit/app/tst_e04_t1_projects.qml'),
                '-o',
                '-,txt',
            ],
            env=environment,
            capture_output=True,
            text=True,
            timeout=300,
            check=False,
        )
    except subprocess.TimeoutExpired as error:
        return error


def run_projects(session, binary, reference):
    result = _projects_result(session, binary, reference)
    if isinstance(result, subprocess.TimeoutExpired):
        raise result
    return result
