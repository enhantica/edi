"""Legacy empty settings versus a user's intentional, persisted endpoint clear."""

import os
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]


def phase(tmp_path, name):
    source = (ROOT / 'tests/fixtures/feedback/endpoint_restart.qml').read_text()
    source = source.replace('__PHASE__', name).replace('__SNAPSHOT__', tmp_path.as_uri())
    source = source.replace('__UI_HELPER__', (ROOT / 'tests/unit/app/UiInteraction.js').as_uri())
    actor = tmp_path / f'tst_endpoint_{name}.qml'
    actor.write_text(source)
    runner = Path(os.environ.get('EDI_APP_TEST_RUNNER', ROOT / 'build/app/app/edi_app_tests'))
    assert runner.is_file(), 'Endpoint migration requires the real app with isolated settings'
    result = subprocess.run(
        [
            str(runner),
            '-input',
            str(actor),
            '-o',
            '-,txt',
            'FeedbackEndpointUpgrade::test_endpoint_upgrade_and_user_clear',
        ],
        capture_output=True,
        text=True,
        check=False,
        timeout=20,
        env={**os.environ, 'QT_QPA_PLATFORM': 'offscreen', 'QT_QUICK_BACKEND': 'software'},
    )
    output = result.stdout + result.stderr
    assert result.returncode == 0 and '0 failed' in output, (
        'The actual application preserves the required endpoint-upgrade state: '
        + name
        + '\n'
        + output
    )
    assert (
        '::FeedbackEndpointUpgrade::test_endpoint_upgrade_and_user_clear()' in output
        and '\nSKIP' not in output
    ), 'Every selected endpoint-migration phase executes without a skip'


def test_old_empty_endpoint_uses_the_deployed_default(tmp_path):
    phase(tmp_path, 'legacy')


def test_clearing_the_preferences_field_stays_off_after_a_restart(tmp_path):
    phase(tmp_path, 'clear')
    phase(tmp_path, 'read')
