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
    copied = markdown.command('markdown_copy')['reply']
    assert copied['clipboard'] == 'Bold', (
        'MD: actual Qt copy preserves the independently selected rendered characters'
    )
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
    assert (
        resource['document_control_image']
        and resource['global_control_image']
        and resource['document_control_calls'] == 1
        and resource['document_control_global_calls'] == 0
        and resource['global_control_calls'] == 1
    ), 'MD SETUP: invalid-loader controls exercise real document/global image providers'
    assert resource['image_null'] and resource['image_width'] == resource['image_height'] == 0, (
        'MD: actual displayed document exposes no usable local image payload from provider prose'
    )
    assert resource['document_provider_calls'] == resource['global_provider_calls'] == 0, (
        'MD: actual displayed document blocks both fallback providers before image loading'
    )


@pytest.mark.parametrize('dark', [False, True], ids=['light', 'dark'])
def test_long_original_paths_links_and_code_wrap_without_changing_actual_copy(markdown, dark):
    path = '/owned/測定/' + 'original_unbroken_path_' * 9 + '.cif'
    url = 'https://example.invalid/' + 'original-unbroken-location-' * 8
    code = 'original_identifier_' * 12 + '(42)'
    original = path + '\n\n<' + url + '>\n\n```text\n' + code + '\n```'
    observed = markdown.command('markdown_row', kind='assistant', text=original, dark=dark)['ui']
    assert observed['original'] == original, 'MD: wrapping cannot rewrite canonical Markdown bytes'
    assert observed['lines'] and observed['body']['width'] > 0, (
        'MD SETUP: actual Qt document has laid-out lines in a nonempty real viewport'
    )
    for token in (path, url, code):
        start = observed['plain'].index(token)
        end = start + len(token)
        occupied = [
            line
            for line in observed['lines']
            if line['start'] < end and line['start'] + line['length'] > start
        ]
        assert len(occupied) > 1, (
            'MD: independently long unbroken paths, URLs and code genuinely occupy wrapped lines'
        )
        assert all(
            line['x'] >= -1 and line['x'] + line['width'] <= observed['body']['width'] + 1
            for line in occupied
        ), 'MD: each actual rendered long-token line stays within the available reply width'
        selected = markdown.command('markdown_select', start=start, end=end)['ui']
        assert selected['selected'] == token, (
            'MD: rendered wrapping adds no hidden breaks to exact selected originals'
        )
        assert markdown.command('markdown_copy')['reply']['clipboard'] == token, (
            'MD: actual clipboard preserves the complete original path, URL and code independently'
        )
    assert markdown.command('inspect')['ui']['original'] == original, (
        'MD: rendering, selection and clipboard never mutate the original history source'
    )


def test_nested_lists_and_existing_link_follow_the_actual_changed_theme(markdown):
    original = (
        'Original first paragraph.\n\nOriginal second paragraph.\n\n'
        '- Outer first\n  - Inner original\n- Outer second\n\n'
        '[Original passive link](https://example.invalid/owned-document)'
    )
    for dark in (False, True):
        observed = markdown.command('markdown_row', kind='assistant', text=original, dark=dark)[
            'ui'
        ]
        assert observed['original'] == original, (
            'MD: theme changes preserve the original paragraph/list/link bytes'
        )
        listed = [block for block in observed['blocks'] if block['listed']]
        assert [block['text'] for block in listed] == [
            'Outer first',
            'Inner original',
            'Outer second',
        ], 'MD: actual Qt lists preserve the complete original nested reading order'
        assert listed[0]['list_indent'] == listed[2]['list_indent'] < listed[1]['list_indent'], (
            'MD: compact indentation preserves real child-versus-sibling list hierarchy'
        )
        anchors = [fragment for fragment in observed['fragments'] if fragment['anchor']]
        assert anchors and ''.join(fragment['text'] for fragment in anchors) == (
            'Original passive link'
        ), 'MD: the independently planted link remains a real formatted document anchor'
        assert all(
            fragment['href'] == 'https://example.invalid/owned-document'
            and fragment['foreground'] == observed['theme_accent']
            for fragment in anchors
        ), 'MD: existing links use the current application accent after actual theme changes'
        assert 'Original first paragraph.' in observed['plain'] and (
            'Original second paragraph.' in observed['plain']
        ), 'MD: paragraph presentation retains both independent original paragraphs'
