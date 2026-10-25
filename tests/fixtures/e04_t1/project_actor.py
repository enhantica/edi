"""Run the project-page checks once per test session and selected case."""

import json
import os
import subprocess
from functools import cache
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
PROJECTS = json.loads(
    (ROOT / 'tests/fixtures/e04_t1/oracle.js')
    .read_text()
    .split('var frozen = ', 1)[1]
    .rstrip(';\n')
)['projects']
PROJECT_CASES = [
    (
        'test_verification_directories_keep_their_independent_project_population'
        if project['metadata']['_metadata.purpose'] == 'verification'
        else 'test_every_example_opens_through_its_page_row'
    )
    + ':'
    + project['id']
    for project in PROJECTS
] + [
    'test_examples_registry_is_complete',
    'test_directory_warning_is_forwarded_without_special_casing:committed-scan',
    'test_directory_warning_is_forwarded_without_special_casing:different-legacy-token',
    'test_bundled_xray_example_opens_by_real_input',
    'test_arbitrary_directory_keeps_legacy_type_inference',
]


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
    runs = []
    for case in PROJECT_CASES:
        try:
            result = subprocess.run(
                [
                    binary,
                    '-input',
                    str(ROOT / 'tests/unit/app/tst_e04_t1_projects.qml'),
                    'E04T1ExistingProjects::' + case,
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
        runs.append(result)
    return subprocess.CompletedProcess(
        args=[run.args for run in runs],
        returncode=next((run.returncode for run in runs if run.returncode), 0),
        stdout=''.join(run.stdout for run in runs),
        stderr=''.join(run.stderr for run in runs),
    )


def run_projects(session, binary, reference):
    result = _projects_result(session, binary, reference)
    if isinstance(result, subprocess.TimeoutExpired):
        raise result
    return result
