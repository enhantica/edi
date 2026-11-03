"""Actual in-app link activation with an injected operating-system URL handler."""

import pytest

from tests.integration.app import test_onboarding_views as host


@pytest.mark.parametrize(
    'case',
    [
        'about_feedback_stays_in_app',
        'feedback_opens_one_form_with_default_attachment',
        *[
            f'internal_actions_never_dispatch_resource_urls:{tag}'
            for tag in ('tutorials', 'citation', 'about', 'feedback')
        ],
    ],
)
def test_onboarding_links_stay_in_app_or_use_http(case):
    host.test_production_onboarding_control('tst_onboarding_home.qml', 'OnboardingHome', case)
