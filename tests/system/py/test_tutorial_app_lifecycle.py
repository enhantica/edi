"""Whole-application tutorial accidents through actual Qt input and saved projects.

These lifecycle cases span the app, session and backing files. One real Qt host
runs the complete actor with its ordinary per-case init and cleanup. Its entire
cost is recorded on the module; each node checks its own retained outcome.
"""

import os
import subprocess
from pathlib import Path

import pytest

from tests.fixtures.onboarding.lifecycle import check_observation
from tests.integration.app import test_onboarding_views as host

CASES = [
    'popup_lists_the_shared_scripts',
    'scientific_tutorial_does_not_modify_the_user_project:pd-neut-cwl_lbco_simulation',
    'scientific_tutorial_does_not_modify_the_user_project:pd-neut-cwl_lbco-hrpt',
    'script_completion_offers_keep_and_discard:keep',
    'script_completion_offers_keep_and_discard:discard',
    *[
        f'home_reentry_cannot_replace_the_user_project:{first}-then-{second}'
        for first in ('pd-neut-cwl_lbco_simulation', 'pd-neut-cwl_lbco-hrpt')
        for second in ('pd-neut-cwl_lbco_simulation', 'pd-neut-cwl_lbco-hrpt', 'interface')
    ],
    'unsaved_set_aside_project_blocks_replacement_and_quit:quit',
    'unsaved_set_aside_project_blocks_replacement_and_quit:replace',
    'pending_text_edit_survives_home_and_tutorial_entry',
]


@pytest.fixture(scope='module')
def lifecycle_observations():
    runner = Path(os.environ.get('EDI_APP_TEST_RUNNER', host.ROOT / 'build/app/app/edi_app_tests'))
    assert runner.is_file(), 'Tutorial lifecycle acceptance requires the real Qt host'
    sources = host.ROOT / 'tests/fixtures/online_sources'
    return subprocess.run(
        [
            str(runner),
            '-input',
            str(host.ROOT / 'tests/unit/app/tst_onboarding_tutorials.qml'),
            '-o',
            '-,txt',
            *(f'OnboardingTutorials::test_{case}' for case in CASES),
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
def test_tutorial_accident_preserves_the_real_user_project(case, lifecycle_observations):
    check_observation(lifecycle_observations, case, CASES)
