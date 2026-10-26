"""The real native test runner owns its report preload until app destruction."""

import json
import os
import sys
from pathlib import Path

import pytest

from tests.fixtures.fast_chart_redraws.rendering import ROOT, capture


@pytest.mark.skipif(
    sys.platform not in {'linux', 'darwin'},
    reason='The native report preload fixture is built on Linux and macOS',
)
@pytest.mark.parametrize('outcome', ['success', 'failure'])
def test_report_preload_is_removed_after_runner_exit(tmp_path, outcome):
    actor = tmp_path / 'RunnerLifecycle.qml'
    actor.write_bytes(
        (ROOT / 'tests/fixtures/report_publication/RunnerLifecycle.qml').read_bytes()
    )
    environment = dict(os.environ)
    environment.update(TMPDIR=str(tmp_path), TMP=str(tmp_path), TEMP=str(tmp_path))
    environment.pop('EDI_REPORT_ACCEPTANCE_PRELOADED', None)
    environment.pop('EDI_REPORT_ACCEPTANCE_OWNER_PID', None)
    status, output = capture(
        [
            os.environ.get('EDI_APP_TEST_RUNNER', ROOT / 'build/app/app/edi_app_tests'),
            '-input',
            actor,
            '-o',
            '-,txt',
            'ReportRunnerCleanup::test_exit:' + outcome,
        ],
        env=environment,
        timeout=30,
    )
    live = [
        json.loads(line.split('REPORT_FAULTS_LIVE ', 1)[1])
        for line in output.splitlines()
        if 'REPORT_FAULTS_LIVE ' in line
    ]
    assert len(live) == 1 and len(live[0]) == 1, (
        'The exit cleanup gate must first observe the actual compiled report preload: ' + output
    )
    library = Path(live[0][0])
    assert library.parent.name.startswith('edi-report-faults-') and library.name == 'faults.so', (
        'The observed temporary artifact is the report failure witness owned by this runner'
    )
    assert status == (1 if outcome == 'failure' else 0) and 'cleanupTestCase()' in output, (
        'The cleanup witness exits normally with the requested passing or failing Qt Test result: '
        + output
    )
    assert not (tmp_path / library.parent).exists(), (
        'App destruction removes its report preload directory after either passing or failing '
        'Qt Test results, including a runner which never emits aboutToQuit'
    )
