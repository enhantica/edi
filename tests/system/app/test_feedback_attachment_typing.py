# SPDX-License-Identifier: BSD-3-Clause
"""A blocked editor is isolated so later stability cases still execute."""

from tests.system.app.test_post_release_stability import actor as _actor

actor = _actor
TYPING = 'PostReleaseStability::test_c_typing_with_attachment_remains_responsive'

NATIVE_SELECTORS = {'test_typing_with_a_real_attachment_stays_responsive': TYPING}


def test_typing_with_a_real_attachment_stays_responsive(actor):
    actor.run(NATIVE_SELECTORS['test_typing_with_a_real_attachment_stays_responsive'])
