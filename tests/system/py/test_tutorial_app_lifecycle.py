"""Whole-application tutorial accidents through actual Qt input and saved projects.

These lifecycle cases span the app, session and backing files. The actor is a
Qt unit fixture; its complete application invocation is a system gate.
"""

import pytest

from tests.integration.app import test_onboarding_views as host

CASES = [
    'popup_lists_the_shared_scripts',
    'scientific_tutorial_does_not_modify_the_user_project:simulation',
    'scientific_tutorial_does_not_modify_the_user_project:fitting',
    'script_completion_offers_keep_and_discard:keep',
    'script_completion_offers_keep_and_discard:discard',
    *[
        f'home_reentry_cannot_replace_the_user_project:{first}-then-{second}'
        for first in ('simulation', 'fitting')
        for second in ('simulation', 'fitting', 'interface')
    ],
    'unsaved_set_aside_project_blocks_replacement_and_quit:quit',
    'unsaved_set_aside_project_blocks_replacement_and_quit:replace',
    'pending_text_edit_survives_home_and_tutorial_entry',
]


@pytest.mark.parametrize('case', CASES)
def test_tutorial_accident_preserves_the_real_user_project(case):
    host.test_production_onboarding_control(
        'tst_onboarding_tutorials.qml', 'OnboardingTutorials', case
    )
