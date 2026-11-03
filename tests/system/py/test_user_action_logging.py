"""Info receipts for real user actions, with a private identity and no network."""

import os
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
CASES = [
    *[
        'shared_control_has_one_private_info_receipt:' + kind
        for kind in (
            'button',
            'tab',
            'combobox',
            'checkbox',
            'numeric',
            'message',
            'subject',
            'name',
            'email',
            'affiliation',
            'project-title',
            'project-description',
        )
    ],
    *[
        'workflow_action_has_an_info_receipt:' + kind
        for kind in (
            'page',
            'tab',
            'project-create',
            'project-open',
            'project-save',
            'structure-add',
            'structure-remove',
            'experiment-add',
            'experiment-remove',
            'fit',
            'tutorial',
            'feedback',
        )
    ],
]


@pytest.mark.parametrize('case', CASES)
def test_real_user_action_receipts(case, tmp_path):
    home = tmp_path / 'SyntheticLogUser8274'
    home.mkdir()
    runner = Path(os.environ.get('EDI_APP_TEST_RUNNER', ROOT / 'build/app/app/edi_app_tests'))
    assert runner.is_file(), 'Action receipt checks require the real Qt application host'
    result = subprocess.run(
        [
            str(runner),
            '-input',
            str(ROOT / 'tests/unit/app/tst_user_action_logging.qml'),
            '-o',
            '-,txt',
            'UserActionLogging::test_' + case,
        ],
        capture_output=True,
        text=True,
        check=False,
        timeout=45,
        env={
            **os.environ,
            'HOME': str(home),
            'USER': home.name,
            'LOGNAME': home.name,
            'USERNAME': home.name,
            'QT_QPA_PLATFORM': 'offscreen',
            'QT_QUICK_BACKEND': 'software',
        },
    )
    output = result.stdout + result.stderr
    assert result.returncode == 0, (
        'Real user actions must produce private Info receipts: ' + output
    )
    function, _, tag = case.partition(':')
    assert f'::UserActionLogging::test_{function}({tag})' in output and '0 failed' in output, (
        'The selected real interaction must execute its logging assertions: ' + output
    )
    assert not any(line.startswith('SKIP') for line in output.splitlines()), (
        'The action logging witness cannot be replaced by a skipped host case'
    )
