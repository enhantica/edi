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


@pytest.fixture(scope='module')
def action_receipts(tmp_path_factory, request):
    # One real host runs every original Qt data row, each with its own init/cleanup.
    # Amortize process/QML startup; retain the complete transcript for every assertion.
    home = tmp_path_factory.mktemp('action-receipts') / 'SyntheticLogUser8274'
    home.mkdir()
    runner = Path(os.environ.get('EDI_APP_TEST_RUNNER', ROOT / 'build/app/app/edi_app_tests'))
    assert runner.is_file(), 'Action receipt checks require the real Qt application host'
    requested = [
        item.callspec.params['case']
        for item in request.session.items
        if item.path == request.node.path
    ]
    result = subprocess.run(
        [
            str(runner),
            '-input',
            str(ROOT / 'tests/unit/app/tst_user_action_logging.qml'),
            '-o',
            '-,txt',
            *['UserActionLogging::test_' + case for case in requested],
        ],
        capture_output=True,
        text=True,
        check=False,
        timeout=300,
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

    result.requested = requested
    return result


@pytest.mark.parametrize('case', CASES)
def test_real_user_action_receipts(case, action_receipts):
    output = action_receipts.stdout + action_receipts.stderr
    assert action_receipts.returncode == 0, (
        'Real user actions must produce private Info receipts: ' + output
    )
    function, _, tag = case.partition(':')
    assert f'::UserActionLogging::test_{function}({tag})' in output and '0 failed' in output, (
        'The selected real interaction must execute its logging assertions: ' + output
    )
    assert all(
        '::UserActionLogging::test_' + name.partition(':')[0] + '(' + name.partition(':')[2] + ')'
        in output
        for name in action_receipts.requested
    ), 'The shared native host retains every requested action and private-field data row'
    assert not any(line.startswith('SKIP') for line in output.splitlines()), (
        'The action logging witness cannot be replaced by a skipped host case'
    )
