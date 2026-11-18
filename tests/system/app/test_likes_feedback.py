# SPDX-License-Identifier: BSD-3-Clause
"""The likes bar's actual controls and feedback routes in the production window."""

import os
from pathlib import Path
from unittest import mock

import pytest

from tests.integration.app import native_actor

CASES = [
    'a_bar_uses_the_approved_controls',
    *[
        'b_activity_blocks_an_offer:' + case
        for case in [
            'fitting',
            'tutorial',
            'disabled',
            'young',
            'few-sessions',
            'recent',
        ]
    ],
    'b_live_activity_hides_the_bar:fitting',
    'b_live_activity_hides_the_bar:tutorial',
    'c_negative_answers_open_the_existing_form:problem',
    'c_negative_answers_open_the_existing_form:question',
    'd_yes_sends_then_opens_feedback',
    'e_opt_out_and_close_are_dismissible:opt-out',
    'e_opt_out_and_close_are_dismissible:close',
    'f_another_fit_does_not_repeat_a_recent_prompt',
    'g_unsuccessful_fits_do_not_prompt:stopped',
    'g_unsuccessful_fits_do_not_prompt:maxIterations',
    'h_opt_out_survives_a_new_bar_instance',
    'i_preferences_offer_both_feedback_switches:likes',
    'i_preferences_offer_both_feedback_switches:survey',
]
NATIVE_FILE = 'tst_likes_feedback.qml'
NATIVE_SELECTORS = {
    f'test_likes_bar_actions[{case}]': 'LikesFeedback::test_' + case for case in CASES
}


@pytest.fixture(scope='module')
def streamed_actor(request, tmp_path_factory):
    root = Path(__file__).resolve().parents[3]
    collection = (root / 'tests/fixtures/online_sources/easydiffraction').as_uri()
    with mock.patch.dict(
        os.environ, {'EDI_ONLINE_SOURCES': f'cod={collection};easydiffraction={collection}'}
    ):
        yield from native_actor.streamed_actor.__wrapped__(request, tmp_path_factory)


@pytest.mark.parametrize('case', CASES)
def test_likes_bar_actions(case, streamed_actor):
    streamed_actor.run('LikesFeedback::test_' + case)
