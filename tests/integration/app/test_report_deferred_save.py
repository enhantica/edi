"""A real workflow navigation must preserve the completed PDF's figure content."""

import os
import subprocess

import pytest

from tests.integration.app.test_e04_t1_projects import APP_TESTS, ROOT, runner


@pytest.fixture(scope='module')
def deferred_save_run():
    environment = {
        key: value
        for key, value in os.environ.items()
        if key not in {'QT_QPA_PLATFORM', 'QT_QUICK_BACKEND'}
    }
    return subprocess.run(
        [
            'bash',
            '-c',
            'source tools/ci/app-platform.sh && app_capture_platform report-save && exec "$@"',
            'report-save',
            str(runner()),
            '-input',
            str(APP_TESTS / 'tst_report_deferred_save.qml'),
            '-o',
            '-,txt',
        ],
        cwd=ROOT,
        env=environment,
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
    assert (
        f'PASS   : edi_app::ReportDeferredSave::test_finished_figures_survive_navigation({route})'
    ) in output, (
        'The actual Save report and workflow navigation must retain the completed model, '
        f'its included PDF image content and only completed current rows ({route}): {output}'
    )
