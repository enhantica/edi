"""ADR-0063: a transport completion owns its submitted draft, not later edits."""

import json
import os
import subprocess
from pathlib import Path

import pytest

from tests.integration.app import native_actor
from tests.integration.py.test_tutorial_docs_presentation import site_module

ROOT = Path(__file__).resolve().parents[3]
FIELDS = ['message', 'name', 'email', 'affiliation']
WEBSITE = [(field, '201') for field in FIELDS] + [
    ('none', status) for status in ['201', '429', '0', '400', 'no-address', 'network-error']
]
APP_CHANGES = [
    'message',
    'name',
    'email',
    'affiliation',
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


def website_completion(change, outcome, dialog_api='native', repeat='once', configuration=None):
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
            str(ROOT / 'website/surfaces/docs/about/community.md'),
            change,
            outcome,
            dialog_api,
            repeat,
            *([str(configuration)] if configuration else []),
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
    return json.loads(result.stdout)


@pytest.mark.parametrize(('change', 'outcome'), WEBSITE, ids=[f'{c}-{s}' for c, s in WEBSITE])
def test_website_completion_preserves_the_current_draft(change, outcome):
    website_completion(change, outcome)


@pytest.mark.parametrize('outcome', ['201', '429', '0', '400'])
def test_website_confirmation_uses_the_open_attribute_fallback(outcome):
    website_completion('none', outcome, 'fallback')


def test_website_confirmation_reopens_for_a_later_result():
    website_completion('none', '201', 'native', 'repeat')


@pytest.mark.parametrize('case', APP_CASES)
def test_app_completion_preserves_the_current_draft(case, streamed_actor, tmp_path, monkeypatch):
    output = streamed_actor.run('FeedbackCompletion::test_' + case)
    if case != 'ordinary_completion:201':
        return
    marker = 'FEEDBACK_MESSAGE_PROMPT '
    app_prompt = [
        json.loads(line.split(marker, 1)[1]) for line in output.splitlines() if marker in line
    ]
    assert len(app_prompt) == 1, 'The real app message editor exposes one placeholder'
    (tmp_path / 'assets').mkdir()
    site_module('build', monkeypatch)._write_feedback_form(tmp_path)
    website = website_completion('none', '201', configuration=tmp_path / 'assets/feedback-form.js')
    assert website['placeholder'] == app_prompt[0], (
        'The docs editor and the actual app editor show the same message placeholder'
    )
    assert app_prompt[0].strip() and app_prompt[0] not in {
        'What works well for you, and what could be better?',
        'What would you like to know, and what have you tried?',
        'What did you do, what happened, and what did you expect?',
        'What would you like the app to do, and how would it help?',
    }, 'The shared message placeholder is nonempty and replaces all prior type-specific prompts'
