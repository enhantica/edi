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
INDICATOR = 'assistant.voiceIndicator'
METER = 'assistant.voiceLevel'
MISSING = 'assistant.voiceMissing'
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


def meter_snapshot(actor):
    return read_control(
        actor,
        METER,
        '(function(){if(!item||!item.visible)return null;'
        'const dots=[];for(const row of Array.from(item.children)){'
        'for(const dot of Array.from(row.children)){'
        'if(dot.objectName==="voiceDot"&&dot.visible)dots.push(dot);}}'
        'dots.sort((a,b)=>a.x-b.x);'
        'return {heights:dots.map(dot=>dot.height), recognising:item.recognising, '
        'animated:item.animated, level:item.level};})()',
    )


def wait_for_voice_dots(actor, *, recognising=False):
    first = None

    def active(_row):
        nonlocal first
        first = meter_snapshot(actor)
        return first and first['recognising'] is recognising

    actor.until(active)
    assert first and len(first['heights']) == 16, (
        'Voice activity displays all sixteen dots in the composer'
    )
    if recognising:
        assert first['level'] == 0, 'The dots show recognition without new microphone input'
    if first['animated']:
        actor.until(
            lambda _row: (
                (meter := meter_snapshot(actor))
                and meter['recognising'] is recognising
                and len(meter['heights']) == len(first['heights'])
                and meter['heights'] != first['heights']
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

    placeholder = read_control(actor, COMPOSER, 'item && item.placeholderText')
    actor.command('click', name=MIC)
    wait_for_voice_dots(actor)
    assert read_control(actor, COMPOSER, 'item && item.placeholderText') == placeholder, (
        'Recording leaves the composer placeholder intact while the dots ripple'
    )
    assert draft(actor) == PREFIX + SUFFIX, 'Listening preserves the existing unsent draft'
    actor.command('click', name=MIC)
    wait_for_voice_dots(actor, recognising=True)
    assert read_control(actor, COMPOSER, 'item && item.placeholderText') == placeholder, (
        'Recognising speech keeps the ordinary composer placeholder and uses the moving dots'
    )
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
    actor.until(lambda _row: visible(actor, INDICATOR))
    actor.command('click', name=COMPOSER)
    actor.command('manual_key', key='escape')
    actor.until(lambda _row: not visible(actor, INDICATOR))
    assert visible(actor, COMPOSER), 'Escape cancels recording while keeping the composer open'
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
    actor.command('click', name=MIC)
    actor.until(lambda _row: visible(actor, 'assistant.voiceMessage'))
    detail = read_control(actor, 'assistant.voiceMessage', 'item && item.text')
    assert detail and re.search(message, detail, re.IGNORECASE), (
        'A refused capture reports the specific missing device or permission problem'
    )
    assert not visible(actor, INDICATOR) and draft(actor) == PREFIX + SUFFIX, (
        'A refused capture never enters recording or changes the draft'
    )
    assert_unsent(actor)


def test_missing_model_opens_installation_note_and_preserves_send(voice_actor, tmp_path):
    actor = voice_actor(tmp_path / 'uninstalled-model.bin')
    assert read_control(actor, MIC, 'item && item.visible && item.enabled'), (
        'The microphone remains visible and can open its note when the model is absent'
    )
    actor.command('click', name=MIC)
    actor.until(lambda _row: read_control(actor, MISSING, 'item && item.opened'))
    message = read_control(actor, MISSING + '.message', 'item && item.visible && item.text')
    assert message and re.search(r'voice input.*not installed', message, re.IGNORECASE), (
        'The missing-component note explains why voice input is unavailable'
    )
    updates = read_control(
        actor, MISSING + '.updates', 'item && ({visible:item.visible,text:item.text})'
    )
    assert updates and re.search(r'updates in preferences', updates['text'], re.IGNORECASE), (
        'The voice note names Updates in Preferences as the way to add the module'
    )
    assert updates['visible'] is qml(actor, 'DesktopUpdates.managed'), (
        'The voice note offers the Updates link on installations managed by Maintenance Tool'
    )
    assert not visible(actor, INDICATOR) and draft(actor) == PREFIX + SUFFIX, (
        'Opening the voice installation note leaves capture idle and preserves the draft'
    )
    actor.command('dialog_ok', name=MISSING, role='ok')
    actor.until(lambda _row: not visible(actor, MISSING))
    assert read_control(actor, 'assistant.send', 'item && item.visible && item.enabled'), (
        'The normal Send control remains usable without the optional voice installation'
    )
    assert_unsent(actor)
