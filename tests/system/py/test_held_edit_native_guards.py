"""The real window guards poll held dirty state without restoring notifications."""

import os
import subprocess
from pathlib import Path

import pytest

from tests.fixtures.onboarding.lifecycle import check_observation

ROOT = Path(__file__).resolve().parents[3]
CASES = tuple(
    f'guard:{action}-{state}'
    for action in ('close', 'open', 'create', 'replace')
    for state in ('held', 'clean')
)


@pytest.fixture(scope='module')
def guard_observations():
    runner = Path(os.environ.get('EDI_APP_TEST_RUNNER', ROOT / 'build/app/app/edi_app_tests'))
    assert runner.is_file(), 'Held native guards require the actual Qt application host'
    sources = ROOT / 'tests/fixtures/online_sources'
    return subprocess.run(
        [
            str(runner),
            '-input',
            str(ROOT / 'tests/unit/app/tst_held_edit_guards.qml'),
            '-o',
            '-,txt',
            *(f'HeldEditGuards::test_{case}' for case in CASES),
        ],
        env={
            **os.environ,
            'QT_QPA_PLATFORM': 'offscreen',
            'QT_QUICK_BACKEND': 'software',
            'EDI_ONLINE_SOURCES': ';'.join(
                f'{name}={(sources / name).as_uri()}' for name in ('cod', 'easydiffraction')
            ),
        },
        capture_output=True,
        text=True,
        check=False,
        timeout=20 * len(CASES),
    )


@pytest.mark.parametrize('case', CASES)
def test_native_guard_retains_the_held_owner_until_consent(case, guard_observations):
    check_observation(guard_observations, case, CASES, suite='HeldEditGuards')
