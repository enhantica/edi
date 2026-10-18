"""A real workflow navigation must preserve the completed PDF's figure content."""

import os
import subprocess

import pytest

from tests.integration.app.test_e04_t1_projects import APP_TESTS, ROOT, runner


@pytest.fixture(scope='module')
def deferred_save_run():
    return subprocess.run(
        [
            str(runner()),
            '-input',
            str(APP_TESTS / 'tst_report_deferred_save.qml'),
            '-o',
            '-,txt',
        ],
        cwd=ROOT,
        env={
            **os.environ,
            'QT_QPA_PLATFORM': 'offscreen',
            'QT_QUICK_BACKEND': 'software',
        },
        capture_output=True,
        text=True,
        timeout=120,
        check=False,
    )


@pytest.mark.parametrize(
    'route', ['deferred-pdf', 'deferred-html', 'deferred-excluded', 'immediate-pdf']
)
def test_real_save_route_keeps_finished_content_and_completed_rows(deferred_save_run, route):
    output = deferred_save_run.stdout + deferred_save_run.stderr
    assert deferred_save_run.returncode >= 0 and all(
        f'PASS   : edi_app::ReportDeferredSave::{phase}()' in output
        for phase in ['initTestCase', 'cleanupTestCase']
    ), 'The real application host must complete setup and teardown without a crash: ' + output
    assert (
        f'PASS   : edi_app::ReportDeferredSave::test_finished_figures_survive_navigation({route})'
    ) in output, (
        'The actual Save report and workflow navigation must retain the completed model, '
        f'its included PDF image content and only completed current rows ({route}): {output}'
    )
