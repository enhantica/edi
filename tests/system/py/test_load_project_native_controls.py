"""Exercise the actual project buttons and their popups through native input."""

import os
import re
import subprocess
from pathlib import Path

import pytest

from tests.fixtures.native_process import environment_bash

ROOT = Path(__file__).resolve().parents[3]


@pytest.fixture(scope='module')
def project_control_actor(request):
    scenarios = [
        item.callspec.params['scenario']
        for item in request.session.items
        if item.path == request.node.path
    ]
    binary = Path(os.environ.get('EDI_APP_TEST_RUNNER', ROOT / 'build/app/app/edi_app_tests'))
    assert binary.is_file(), (
        'Project entry acceptance requires the built native application test runner'
    )
    return subprocess.run(
        [
            environment_bash(),
            str(ROOT / 'tests/fixtures/scan_views/run.sh'),
            str(binary),
            '-input',
            str(ROOT / 'tests/unit/app/tst_load_project_controls.qml'),
            '-o',
            '-,txt',
            *['LoadProjectControls::test_' + scenario for scenario in scenarios],
        ],
        capture_output=True,
        text=True,
        timeout=30 * len(scenarios),
        check=False,
    )


@pytest.mark.parametrize(
    'scenario',
    [
        'three_project_buttons:empty',
        'three_project_buttons:loaded',
        'load_project_opens_the_ordered_choices:empty',
        'load_project_opens_the_ordered_choices:loaded',
        'save_project_as_opens_the_ordered_choices',
        'save_copy_belongs_to_native_choices',
    ],
)
def test_load_project_controls_in_the_production_window(scenario, project_control_actor):
    run = project_control_actor
    output = run.stdout + run.stderr
    assert run.returncode == 0, (
        'Real project controls and popup must pass native input acceptance: ' + output
    )
    function, _, tag = scenario.partition(':')
    assert re.search(
        r'^PASS\s*:\s*(?:edi_app::)?LoadProjectControls::test_'
        + re.escape(function)
        + r'\('
        + re.escape(tag)
        + r'\)',
        output,
        re.MULTILINE,
    ), 'The selected project control scenario must finish in the real production window: ' + output
    assert not re.search(r'^(?:FAIL!|SKIP)\s*:', output, re.MULTILINE), (
        'A skipped or incomplete project control scenario cannot count as acceptance'
    )
