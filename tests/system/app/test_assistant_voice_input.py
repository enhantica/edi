# SPDX-License-Identifier: BSD-3-Clause
"""Drive voice input through the native assistant composer with offline audio."""

import hashlib
import json
import os
import re
from pathlib import Path

import pytest

from tests.system.py.test_e11_t5_dev_native_integration import MainActor, control_expression, qml

ROOT = Path(__file__).resolve().parents[3]
FIXTURE = ROOT / 'tests/fixtures/assistant_voice'
MODEL_SHA256 = '818710568da3ca15689e31a743197b520007872ff9576237bda97bd1b469c3d7'
MIC = 'assistant.voice'
CANCEL = 'assistant.voiceCancel'
COMPOSER = 'assistant.composer'
PREFIX = 'Keep this: '
SUFFIX = ' [draft tail]'


@pytest.fixture(scope='module')
def tiny_model():
    model = ROOT / 'build/voice-models/ggml-tiny-q5_1.bin'
    assert model.is_file(), 'Offline acceptance must have local tiny Whisper weights'
    with model.open('rb') as stream:
        assert hashlib.file_digest(stream, 'sha256').hexdigest() == MODEL_SHA256, (
            'The staged model bytes match the independently published tiny-q5_1 digest'
        )
    return model


@pytest.fixture
def voice_actor(monkeypatch, tmp_path):
    actors = []

    def start(model_path, capture='available'):
        runner = Path(
            os.environ.get(
                'EDI_ASSISTANT_UI_PROBE',
                ROOT / 'build/app/assistant-ui-probe/assistant_real_owner_probe',
            )
        )
        assert runner.is_file(), 'The native voice tests require the actual assistant UI test host'
        monkeypatch.setenv('EDI_TEST_ASSISTANT_VOICE_MODEL', str(model_path))
        monkeypatch.setenv('EDI_TEST_ASSISTANT_VOICE_WAV', str(FIXTURE / 'inaugural.wav'))
        monkeypatch.setenv('EDI_TEST_ASSISTANT_VOICE_CAPTURE', capture)
        actor = MainActor(runner, tmp_path, {'turns': []}, False)
        actors.append(actor)
        actor.connect()
        editor = control_expression(COMPOSER)
        if not visible(actor, COMPOSER):
            actor.command('click', name='assistant.toggle')
        actor.until(lambda _row: visible(actor, COMPOSER))
        qml(
            actor,
            '(function(){const editor='
            + editor
            + ';editor.text='
            + json.dumps(PREFIX + SUFFIX)
            + f';editor.cursorPosition={len(PREFIX)};return editor.text;}})()',
        )
        assert draft(actor) == PREFIX + SUFFIX, (
            'Voice acceptance starts from an existing draft with a cursor between two text spans'
        )
        return actor

    yield start
    for actor in actors:
        actor.close()


def read_control(actor, name, expression):
    return qml(
        actor,
        '(function(){const item=' + control_expression(name) + ';return ' + expression + ';})()',
    )


def visible(actor, name):
    return read_control(actor, name, '!!(item && item.visible)')


def draft(actor):
    return read_control(actor, COMPOSER, 'item && item.text')


def visible_text(actor):
    return set(
        qml(
            actor,
            'testAppObjects.snapshot().filter(item=>Qt.isQtObject(item)&&'
            'item.visible===true&&typeof item.text==="string"&&item.text.trim())'
            '.map(item=>item.text.trim())',
        )
    )


def assert_unsent(actor):
    requests = (
        list(map(json.loads, actor.trace.read_text().splitlines())) if actor.trace.exists() else []
    )
    assert not any(request.get('method') == 'turn/start' for request in requests), (
        'Voice input never submits a message to the assistant'
    )


def words(text):
    return re.findall(r"[\w']+", text.casefold())


def edits(expected, actual):
    row = list(range(len(actual) + 1))
    for left_index, left in enumerate(expected, start=1):
        next_row = [left_index]
        for right_index, right in enumerate(actual, start=1):
            next_row.append(
                min(
                    row[right_index] + 1,
                    next_row[-1] + 1,
                    row[right_index - 1] + (left != right),
                )
            )
        row = next_row
    return row[-1]


def test_pressing_microphone_twice_inserts_editable_speech_at_the_cursor(voice_actor, tiny_model):
    actor = voice_actor(tiny_model)
    geometry = read_control(
        actor,
        MIC,
        '(function(){const send='
        + control_expression('assistant.send')
        + ';if(!item||!item.visible||!item.enabled||!send||!send.visible)return null;'
        'const gap=item.parent.spacing, a=item.mapToItem(null,0,0), b=send.mapToItem(null,0,0);'
        'return {sameRow:item.parent===send.parent,gap:'
        'Math.max(a.x,b.x)-Math.min(a.x+item.width,b.x+send.width),spacing:gap};})()',
    )
    assert geometry and geometry['sameRow'] and 0 <= geometry['gap'] <= geometry['spacing'] + 1, (
        'The microphone is a visible, enabled action immediately beside Send'
    )

    actor.command('click', name=MIC)
    actor.until(lambda _row: visible(actor, CANCEL))
    assert draft(actor) == PREFIX + SUFFIX, 'Listening preserves the existing unsent draft'
    actor.command('click', name=MIC)
    actor.until(lambda _row: draft(actor) != PREFIX + SUFFIX)
    updated = draft(actor)
    assert updated.startswith(PREFIX) and updated.endswith(SUFFIX), (
        'Transcription preserves both original spans and inserts speech at the insertion cursor'
    )
    spoken = updated[len(PREFIX) : -len(SUFFIX)]
    expected = words((FIXTURE / 'inaugural.txt').read_text(encoding='utf-8'))
    assert edits(expected, words(spoken)) / len(expected) <= 0.15, (
        'The recognized words match the independently transcribed clip within 15% word error'
    )
    assert_unsent(actor)


def test_cancel_discards_captured_audio_and_leaves_the_draft_unsent(voice_actor, tiny_model):
    actor = voice_actor(tiny_model)
    actor.command('click', name=MIC)
    actor.until(lambda _row: visible(actor, CANCEL))
    assert visible(actor, CANCEL), 'An active recording exposes a cancellation control'
    actor.command('click', name=CANCEL)
    actor.until(lambda _row: not visible(actor, CANCEL))
    assert draft(actor) == PREFIX + SUFFIX, 'Cancelling a recording discards the captured speech'
    assert_unsent(actor)


@pytest.mark.parametrize(
    ('capture', 'message'),
    [
        (
            'no-device',
            (
                r'(?:no|cannot find|unavailable).*(?:microphone|audio input)'
                r'|(?:microphone|audio input).*(?:not available|unavailable|not found)'
            ),
        ),
        ('permission-denied', r'(?:permission|denied|refused|access)'),
    ],
    ids=['no-device', 'permission-denied'],
)
def test_microphone_refusals_explain_the_problem_without_editing(
    voice_actor, tiny_model, capture, message
):
    actor = voice_actor(tiny_model, capture)
    assert visible(actor, MIC), (
        'An installed model exposes the microphone before permission checks'
    )
    before = visible_text(actor)
    actor.command('click', name=MIC)
    actor.until(lambda _row: bool(visible_text(actor) - before))
    assert any(re.search(message, text, re.IGNORECASE) for text in visible_text(actor) - before), (
        'A refused capture reports the specific missing device or permission problem'
    )
    assert not visible(actor, CANCEL) and draft(actor) == PREFIX + SUFFIX, (
        'A refused capture never enters recording or changes the draft'
    )
    assert_unsent(actor)


def test_missing_model_hides_microphone_but_preserves_send(voice_actor, tmp_path):
    actor = voice_actor(tmp_path / 'uninstalled-model.bin')
    assert not visible(actor, MIC), 'The app hides the microphone when voice weights are absent'
    assert read_control(actor, 'assistant.send', 'item && item.visible && item.enabled'), (
        'The normal Send control remains usable without the optional voice installation'
    )
