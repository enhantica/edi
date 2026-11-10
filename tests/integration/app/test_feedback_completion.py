"""ADR-0063: a transport completion owns its submitted draft, not later edits."""

import os
import subprocess
from pathlib import Path

import pytest

from tests.integration.app import native_actor

ROOT = Path(__file__).resolve().parents[3]
FIELDS = ['message', 'subject', 'name', 'email', 'affiliation', 'reason']
WEBSITE = [(field, '201') for field in FIELDS] + [
    ('none', status) for status in ['201', '429', '0', '400', 'no-address', 'network-error']
]
APP_CHANGES = [
    'message',
    'subject',
    'name',
    'email',
    'affiliation',
    'kind',
    'include',
    'close',
    'closing',
    'reopen',
    'reopen-identical',
    'attachment-added',
    'attachment-changed',
    'attachment-cleared',
]
APP_CASES = (
    ['a_unsent_crash_attachment']
    + [f'later_draft:{change}' for change in APP_CHANGES]
    + [f'ordinary_completion:{status}' for status in ['201', '429', '0', '400', 'no-address']]
    + ['submitted_kind_is_logged']
    + [
        f'successor_can_send:{change}-{order}'
        for change in [
            'attachment-added',
            'attachment-changed',
            'attachment-cleared',
            'close',
            'cancel',
            'open-as',
        ]
        for order in ['old-first', 'new-first']
    ]
)
NATIVE_FILE = 'tst_feedback_completion.qml'
NATIVE_SELECTORS = {
    f'test_app_completion_preserves_the_current_draft[{case}]': 'FeedbackCompletion::test_' + case
    for case in APP_CASES
}


@pytest.fixture(scope='module')
def streamed_actor(request, tmp_path_factory):
    previous = os.environ.get('EDI_ONLINE_SOURCES')
    collection = (ROOT / 'tests/fixtures/online_sources/easydiffraction').as_uri()
    os.environ.setdefault('EDI_ONLINE_SOURCES', f'cod={collection};easydiffraction={collection}')
    try:
        yield from native_actor.streamed_actor.__wrapped__(request, tmp_path_factory)
    finally:
        if previous is None:
            os.environ.pop('EDI_ONLINE_SOURCES', None)


def website_completion(change, outcome, dialog_api='native', repeat='once'):
    asset = Path(
        os.environ.get(
            'FEEDBACK_WEBSITE_ASSET', ROOT / 'website/surfaces/docs/assets/contact-form.js'
        )
    )
    result = subprocess.run(
        [
            'node',
            str(ROOT / 'tests/fixtures/feedback_completion/website.cjs'),
            str(asset),
            change,
            outcome,
            dialog_api,
            repeat,
        ],
        capture_output=True,
        text=True,
        check=False,
        timeout=10,
    )
    assert result.returncode == 0, (
        'ADR-0063 F1: website completion preserves later edits and ordinary outcomes: '
        + result.stdout
        + result.stderr
    )


@pytest.mark.parametrize(('change', 'outcome'), WEBSITE, ids=[f'{c}-{s}' for c, s in WEBSITE])
def test_website_completion_preserves_the_current_draft(change, outcome):
    website_completion(change, outcome)


@pytest.mark.parametrize('outcome', ['201', '429', '0', '400'])
def test_website_confirmation_uses_the_open_attribute_fallback(outcome):
    website_completion('none', outcome, 'fallback')


def test_website_confirmation_reopens_for_a_later_result():
    website_completion('none', '201', 'native', 'repeat')


@pytest.mark.parametrize('case', APP_CASES)
def test_app_completion_preserves_the_current_draft(case, streamed_actor):
    streamed_actor.run('FeedbackCompletion::test_' + case)
