"""Every retained example must open through the production Qt pages."""

from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

from tests.fixtures.e04_t1.project_actor import run_projects
from tests.fixtures.fast_chart_redraws.startup import split_renderer_reports

ROOT = Path(__file__).resolve().parents[3]
APP_TESTS = ROOT / 'tests/unit/app'
ORACLE = json.loads(
    (ROOT / 'tests/fixtures/e04_t1/oracle.js')
    .read_text()
    .split('var frozen = ', 1)[1]
    .rstrip(';\n')
)
PROJECTS = ORACLE['projects']
APP_PROJECTS = [p for p in PROJECTS if p['id'] in ORACLE['catalogue_ids']]
VERIFICATION_PROJECTS = [
    p for p in PROJECTS if p['metadata']['_metadata.purpose'] == 'verification'
]


@pytest.fixture(scope='module')
def acceptance_reference():
    # Frozen separate-surface wiring regression pins; never generated at GUI runtime.
    return str(ROOT / 'tests/fixtures/e04_t1/reference')


def runner():
    override = os.environ.get('EDI_APP_TEST_RUNNER')
    candidates = (
        [Path(override)]
        if override
        else [
            ROOT / 'build/app/app/edi_app_tests',
            ROOT / 'build/app/edi_app_tests',
        ]
    )
    binary = next((path for path in candidates if path.is_file()), None)
    assert binary is not None, 'I3/I10: app-build must produce the Qt Quick Test runner'
    return binary


@pytest.fixture(scope='module')
def existing_projects_run(acceptance_reference, request):
    return run_projects(request.session, str(runner()), acceptance_reference)


def test_existing_projects_open_and_populate_pages(existing_projects_run):
    run = existing_projects_run
    output = run.stdout + run.stderr
    assert run.returncode == 0, (
        f'I19: all registered examples and legacy directories open: {output}'
    )
    _, diagnostics = split_renderer_reports(run.stderr)
    assert not diagnostics, (
        'App project loads route diagnostics to the warning model; stderr permits only '
        'the declared startup renderer report: ' + diagnostics
    )
    assert (
        'E04T1ExistingProjects' in output
        and 'test_every_example_opens_through_its_page_row' in output
    ), 'I19: the production runner must actually execute the existing-project cases'


@pytest.mark.parametrize('example_id', [project['id'] for project in APP_PROJECTS])
def test_each_registered_example_executes_in_the_production_host(
    existing_projects_run, example_id
):
    output = existing_projects_run.stdout + existing_projects_run.stderr
    assert (
        'PASS   : edi_app::E04T1ExistingProjects::'
        f'test_every_example_opens_through_its_page_row({example_id})'
    ) in output, (
        'I19: each committed example must execute through its real page row: ' + example_id
    )


@pytest.mark.parametrize('example_id', [project['id'] for project in VERIFICATION_PROJECTS])
def test_verification_directory_executes_in_the_production_host(existing_projects_run, example_id):
    output = existing_projects_run.stdout + existing_projects_run.stderr
    assert (
        'PASS   : edi_app::E04T1ExistingProjects::'
        f'test_verification_directories_keep_their_independent_project_population({example_id})'
    ) in output, (
        'verification directories retain their complete independent population checks: '
        + example_id
    )
