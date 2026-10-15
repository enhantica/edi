"""Actual Qt passive presentation; original row data is not a fake transcript/VM.

No remote resource request is made. A harmless valid owned PNG independently
qualifies the actual text document's refusal of resource fallback.
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from tests.system.app import test_e11_t5_consent_dialog as prior

native = prior.native
ROOT = prior.ROOT
ORIGINAL = '**Bold Å** and `sample()`\n\n1. First original\n2. Second original'


class Markdown(prior.Consent):
    def __init__(self, binary):
        self.process = native.subprocess.Popen(
            [
                str(binary),
                str(ROOT / 'tests/integration/py/assistant_consent_probe/MarkdownHarness.qml'),
                '--markdown',
            ],
            stdin=native.subprocess.PIPE,
            stdout=native.subprocess.PIPE,
            stderr=native.subprocess.PIPE,
            text=True,
            encoding='utf-8',
        )
        self.reply_timeout = 5.0
        self.last = None
        self.handled = set()


@pytest.fixture
def markdown(monkeypatch):
    binary = Path(os.environ['EDI_ASSISTANT_CONSENT_PROBE'])
    assert binary.is_file(), 'MD SETUP: actual coherent Qt/module presentation consumer exists'
    monkeypatch.setenv('QT_QPA_PLATFORM', 'offscreen')
    monkeypatch.setenv('QT_QUICK_BACKEND', 'software')
    actor = Markdown(binary)
    try:
        actor.command('inspect')
        yield actor
    finally:
        actor.close()


@pytest.mark.parametrize('dark', [False, True], ids=['light', 'dark'])
def test_actual_assistant_document_renders_bold_code_lists_and_keeps_original_selection(
    markdown, dark
):
    observed = markdown.command('markdown_row', kind='assistant', text=ORIGINAL, dark=dark)['ui']
    assert (
        observed['original'] == ORIGINAL and observed['read_only'] and observed['select_by_mouse']
    ), (
        'MD: actual delegate preserves exact original bytes '
        'and ordinary read-only selectable widget'
    )
    assert '**Bold' not in observed['plain'] and '`sample()`' not in observed['plain'], (
        'MD: actual assistant document renders formatting instead of literal Markdown markers'
    )
    assert any(
        'Bold Å' in fragment['text'] and fragment['bold'] for fragment in observed['fragments']
    ), 'MD: real Qt character formatting renders the independently planted strong span'
    assert any(
        'sample()' in fragment['text'] and fragment['fixed_pitch']
        for fragment in observed['fragments']
    ), 'MD: real inline-code formatting uses an actual fixed-pitch font'
    assert [block['text'] for block in observed['blocks'] if block['listed']] == [
        'First original',
        'Second original',
    ], 'MD: real Qt list blocks retain both original items rather than a handwritten replacement'
    selected = markdown.command('markdown_select', start=0, end=4)['ui']
    assert selected['selected'] == 'Bold', 'MD: nontrivial actual rendered selection is selectable'
    after = markdown.command('markdown_select', start=0, end=4, type_x=True)['ui']
    assert after['plain'] == observed['plain'] and after['original'] == ORIGINAL, (
        'MD: actual keyboard edit cannot mutate displayed or original transcript bytes'
    )


@pytest.mark.parametrize('kind', ['user', 'event'])
def test_user_and_diagnostic_markup_remains_literal_plain_text(markdown, kind):
    text = '**Literal user** `code` <b>literal HTML</b>'
    observed = markdown.command('markdown_row', kind=kind, text=text, dark=False)['ui']
    assert observed['original'] == text and observed['plain'] == text, (
        'MD: user and diagnostic content remain literal, never assistant Markdown authority'
    )
    assert not any(fragment['bold'] for fragment in observed['fragments']), (
        'MD: literal user/error markup cannot acquire assistant strong formatting'
    )


def test_actual_document_refuses_owned_valid_image_resource_and_does_not_parse_html(markdown):
    image = markdown.command('fixture_image')['reply']
    assert image['saved'] and image['valid_original_image'], (
        'MD SETUP: independent task-owned PNG is valid before any subject resource request'
    )
    text = '<b>Literal HTML</b>\n\n![untrusted image](' + image['url'] + ')'
    observed = markdown.command('markdown_row', kind='assistant', text=text, dark=False)['ui']
    assert '<b>Literal HTML</b>' in observed['plain'] and observed['original'] == text, (
        'MD: Qt Markdown disables HTML interpretation while retaining the original provider bytes'
    )
    resource = markdown.command('markdown_resource', url=image['url'])['reply']
    assert not resource['resource_valid'], (
        'MD: actual displayed document refuses even valid local image fallback from provider prose'
    )
