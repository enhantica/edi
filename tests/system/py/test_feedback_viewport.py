"""Real feedback viewport, frame-by-frame opening and single-scroll ownership."""

import pytest

from tests.integration.app.test_onboarding_views import (
    test_production_onboarding_control as run_host,
)

CASES = [
    *[
        f'preview_uses_six_readable_monospaced_lines:{theme}-{part}'
        for theme in ('light', 'dark')
        for part in ('height-and-scroll', 'monospace', 'normal-colour')
    ],
    'message_box_shows_five_lines',
    *[f'opening_starts_at_top_with_message_focus:{size}' for size in ('normal', 'small')],
    'privacy_note_wraps_to_two_lines_at_default_font',
    *[f'small_window_keeps_title_and_actions_visible:{size}' for size in ('minimum', 'short')],
    *[f'only_the_correct_viewport_scrolls:{size}' for size in ('normal', 'small')],
    'fitting_content_has_no_indicator_on_any_opening_frame',
]


@pytest.mark.parametrize('case', CASES)
def test_feedback_viewport_in_the_real_application(case):
    run_host('tst_feedback_viewport.qml', 'FeedbackViewport', case)
