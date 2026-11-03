"""Actual optional-contact form, transport outcomes and persisted restart state."""

import json
import os
import subprocess
from pathlib import Path

import pytest

from tests.integration.app.test_onboarding_views import (
    test_production_onboarding_control as run_host,
)

ROOT = Path(__file__).resolve().parents[3]
CASES = [
    'opening_line_is_between_the_title_and_kind',
    'general_feedback_is_first_and_default',
    *[
        f'subject_and_message_placeholders_follow_the_kind:{kind}'
        for kind in ('feedback', 'question', 'problem', 'idea')
    ],
    *[
        f'optional_subject_is_trimmed_and_shown_in_the_payload:{kind}'
        for kind in ('empty', 'whitespace', 'filled')
    ],
    'kind_has_no_redundant_question_label',
    'contact_fields_follow_the_kind_before_the_message',
    *[f'contact_payload_has_only_filled_trimmed_keys:{mask}' for mask in range(8)],
    'contact_payload_has_only_filled_trimmed_keys:without-diagnostics',
    *[
        f'failed_submission_preserves_optional_contact:{status}'
        for status in ('limited', 'offline')
    ],
    *[f'preview_and_message_share_the_field_border:{theme}' for theme in ('light', 'dark')],
    'checkbox_indicator_aligns_with_kind',
    *[f'empty_message_disables_send:{kind}' for kind in ('empty', 'whitespace')],
    *[
        f'submission_keeps_text_on_failure_and_thanks_on_success:{outcome}'
        for outcome in ('created', 'created-auto', 'limited', 'offline')
    ],
]


@pytest.mark.parametrize('case', CASES)
def test_redesigned_feedback_in_the_real_application(case):
    run_host('tst_feedback_redesign.qml', 'FeedbackRedesign', case)


def test_optional_contact_is_remembered_between_application_runs(tmp_path):
    source = (ROOT / 'tests/unit/app/tst_feedback_redesign.qml').read_text()
    for helper in ('UiInteraction.js', 'RenderedTable.js'):
        source = source.replace(
            '"' + helper + '"', json.dumps((ROOT / 'tests/unit/app' / helper).as_uri())
        )
    snapshot = tmp_path / 'settings'
    snapshot.mkdir()
    source = source.replace(
        'property url restartSnapshot: ""',
        'property url restartSnapshot: ' + json.dumps(snapshot.as_uri()),
    )
    runner = Path(os.environ.get('EDI_APP_TEST_RUNNER', ROOT / 'build/app/app/edi_app_tests'))
    assert runner.is_file(), 'Remembered contact is exercised by two real application processes'
    for phase, action in [('write', 'writeContactSettings'), ('read', 'readContactSettings')]:
        actor = tmp_path / f'tst_feedback_restart_{phase}.qml'
        text = source.replace(
            'property string restartPhase: ""',
            'property string restartPhase: ' + json.dumps(phase),
        )
        end = text.rfind('}')
        text = text[:end] + f'function test_restart_phase() {{ {action}(); }}\n' + text[end:]
        actor.write_text(text)
        result = subprocess.run(
            [
                str(runner),
                '-input',
                str(actor),
                '-o',
                '-,txt',
                'FeedbackRedesign::test_restart_phase',
            ],
            capture_output=True,
            text=True,
            check=False,
            timeout=20,
            env={**os.environ, 'QT_QPA_PLATFORM': 'offscreen', 'QT_QUICK_BACKEND': 'software'},
        )
        output = result.stdout + result.stderr
        assert result.returncode == 0 and '0 failed' in output, (
            'The actual contact settings survive the process boundary: ' + phase + '\n' + output
        )
        assert '::FeedbackRedesign::test_restart_phase()' in output and '\nSKIP' not in output, (
            'Each fresh application executes its required persistence phase without a skip'
        )


def test_crash_report_keeps_the_problem_kind():
    run_host('tst_onboarding_crash.qml', 'OnboardingCrash', 'popup_offers_the_actual_crashed_log')
