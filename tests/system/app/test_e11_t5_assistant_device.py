"""Native control for the owner-declared device UX; browser cases use the real CDP driver."""

import os
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]


@pytest.fixture(scope='module')
def native_device_receipts():
    runner = Path(os.environ.get('EDI_APP_TEST_RUNNER', ROOT / 'build/app/app/edi_app_tests'))
    assert runner.is_file(), 'I16/device: coherent actual native Quick Test runner is required'
    return subprocess.run(
        [
            str(runner),
            '-input',
            str(Path(__file__).with_name('tst_assistant_device.qml')),
            '-o',
            '-,txt',
        ],
        env={**os.environ, 'QT_QPA_PLATFORM': 'offscreen', 'QT_QUICK_BACKEND': 'software'},
        capture_output=True,
        text=True,
        timeout=15,
        check=False,
    )


@pytest.mark.parametrize(
    'case',
    [
        'test_native_metadata_is_eligible_but_disconnected',
        'test_native_entries_preferences_and_hidden_focus',
    ],
)
def test_device_policy_preserves_real_native_entry(native_device_receipts, case):
    output = native_device_receipts.stdout + native_device_receipts.stderr
    assert f'PASS   : edi_app::AssistantDeviceEntry::{case}(' in output, (
        'I16/device: each unchanged native eligibility/entry control executes in real Main: '
        + case
        + '\n'
        + output
    )
