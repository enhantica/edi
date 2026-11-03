"""Shipped feedback destination and actual form availability, without HTTP."""

import json
import os
import re
from pathlib import Path

import pytest

from tests.integration.app.test_onboarding_views import (
    test_production_onboarding_control as run_host,
)

ROOT = Path(__file__).resolve().parents[3]
SOURCE = Path(os.environ.get('EDI_ONBOARDING_SOURCE_ROOT', ROOT))
DEFAULT_ENDPOINT = 'https://edi-feedback.savanna-animas-0g.workers.dev/feedback'


def test_shipped_feedback_endpoint_is_the_public_service():
    # Reading the declaration cannot issue a request or inherit a user's settings.
    source = (SOURCE / 'app/qml/Globals/Preferences.qml').read_text()
    declaration = re.search(
        r'^\s*property string feedbackEndpoint:\s*("[^"\n]*")\s*$', source, re.MULTILINE
    )
    assert declaration is not None, 'Preferences declares the shipped feedback destination'
    assert json.loads(declaration[1]) == DEFAULT_ENDPOINT, (
        'A fresh installation defaults to the deployed public feedback service'
    )


# Each case boots the complete application, opens its real Home form and follows
# UI/model/transport or log boundaries; these belong to the system tier.
@pytest.mark.parametrize(
    'case',
    [
        'default_endpoint_enables_send_without_an_unavailable_note',
        'clearing_endpoint_disables_send',
        'preview_is_exactly_the_injected_submission:created',
        'preview_is_exactly_the_injected_submission:invalid',
        'preview_is_exactly_the_injected_submission:limited',
        'unticked_attachment_changes_the_preview',
        'real_host_log_header_and_aligned_sources',
    ],
)
def test_feedback_form_in_the_actual_application(case):
    run_host('tst_onboarding_payload.qml', 'OnboardingPayload', case)
