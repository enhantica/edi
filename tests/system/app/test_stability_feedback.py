# SPDX-License-Identifier: BSD-3-Clause
"""Native error reporting and feedback actions in the production QML host."""

import os
from pathlib import Path
from unittest import mock

import pytest

from tests.integration.app import native_actor

CASES = [
    'a_previous_crash_has_send_and_ok',
    'b_caught_event_error_shows_diagnostic_actions',
    'b_failed_project_open_shows_diagnostic_actions',
    'c_unreadable_input_shows_location_and_attaches_file:structure',
    'c_unreadable_input_shows_location_and_attaches_file:experiment',
    'c_unreadable_input_shows_location_and_attaches_file:data',
    'd_non_ascii_datablock_survives_load_save_and_reopen',
    'e_survey_is_permanently_available',
    'e_user_can_open_likes_from_home_despite_timing',
    *[
        'f_failed_send_offers_a_plain_text_report:' + case
        for case in ('no-answer', 'rate-limit', 'server', 'other-success-code')
    ],
]
NATIVE_FILE = 'tst_stability_feedback.qml'
NATIVE_SELECTORS = {
    f'test_error_feedback_actions[{case}]': 'StabilityFeedback::test_' + case for case in CASES
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
def test_error_feedback_actions(case, streamed_actor):
    streamed_actor.run('StabilityFeedback::test_' + case)
