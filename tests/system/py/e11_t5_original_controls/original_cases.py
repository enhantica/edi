"Original real-control characterization, independent of the extraction bodies."

import json

import pytest
import test_e11_t5_dev_native_integration as original
from test_e11_t5_dev_native_integration import control_expression, qml


def _original_composer(actor):
    return qml(
        actor,
        '(function(){const e='
        + control_expression('assistant.composer')
        + (
            ';if(!e)return null;let c=e.parent;while(c&&typeof c.textRevi'
            'sion!=="number")c=c.parent;if(!c)return null;return {text:e.'
            'text,preedit:e.preeditText,composing:e.inputMethodComposing,'
            'revision:c.textRevision,ownerRevision:c.draftOwnerRevision,i'
            'ntent:c.sessionDraftIntent,clear:c.clearDraft,submittedCount'
            ':c.submittedDrafts.length,report:c.workReportDraft,published'
            ':Session.assistant.sessionDraft};})()'
        ),
    )


def _hold_original_draft_read(actor):
    release = actor.folder / 'release-original-draft-read'
    path = actor.folder / 'peer.json'
    config = json.loads(path.read_bytes())
    config['session_fixture']['read_hold'] = str(release)
    path.write_text(json.dumps(config))
    return release


def _original_restore_input(actor, input_transition, text, captured, facts, out):
    if input_transition != 'unchanged':
        actor.command('manual_ime', preedit='Q', commit='')
        preedit = _original_composer(actor)
        facts['stages'].append(preedit)
        out.write_text(json.dumps(facts, indent=2))
        assert preedit['text'] == text and preedit['preedit'] == 'Q' and preedit['composing'], (
            'The actual focused composer receives real IME preedit withou'
            't publishing it as draft text'
        )
        assert preedit['revision'] > captured['revision'] and preedit['published'] == text
        if input_transition != 'preedit_active':
            actor.command(
                'manual_ime',
                preedit='',
                commit=' committed' if input_transition == 'ime_commit' else '',
            )
            settled_input = _original_composer(actor)
            facts['stages'].append(settled_input)
            out.write_text(json.dumps(facts, indent=2))
            assert (
                settled_input['revision'] > preedit['revision'] and not settled_input['preedit']
            ), 'Actual IME completion or cancellation publishes its newer input revision'
            assert settled_input['text'] == text + (
                ' committed' if input_transition == 'ime_commit' else ''
            )


def _assert_original_restore_result(
    actor, input_transition, facts, captured, before_release, restored, target
):
    resumes = [row for row in facts['wire'] if row.get('method') == 'thread/resume']
    assert resumes and resumes[-1]['params']['threadId'] == target, (
        'The original exact target really resumes'
    )
    expected = '' if input_transition == 'unchanged' else before_release['text']
    assert (
        restored['text'] == expected
        and restored['published'] == expected
        and restored['intent'] is None
    ), (
        'Unchanged capture restores A draft; newer real input survive'
        's, consumes the intent and publishes actual current text'
    )
    if input_transition == 'preedit_cancel':
        assert (
            before_release['text'] == captured['text']
            and before_release['revision'] > captured['revision']
        ), (
            'Same literal text with a genuine newer IME revision cannot p'
            'ass through a text-only restore fence'
        )
    if input_transition == 'preedit_active':
        actor.command('manual_ime', preedit='', commit='')


@pytest.mark.parametrize(
    'input_transition', ['unchanged', 'preedit_cancel', 'ime_commit', 'preedit_active']
)
def test_original_restore_keeps_only_actual_newer_input_and_publishes_current_text(
    main_actor, input_transition
):
    actor = main_actor([[], []])
    original._session_configure(
        actor, session_fixture={'threads': [], 'page_size': 12}, observe_context_continuity=True
    )
    target, current = original._two_genuine_session_threads(actor)
    text = 'Actual B draft survives only a newer input revision.'
    original._type_original_draft(actor, text)
    actor.command('click', name='assistant.sessions')
    rows = original._session_wait(actor)
    assert target in {row['id'] for row in rows}, (
        'The target is a genuine app-created original browser row'
    )
    release = _hold_original_draft_read(actor)
    boundary = len(original._session_wire(actor))
    click = actor.command('session_row_click', thread_id=target)['reply']
    captured = _original_composer(actor)
    facts = {
        'target': target,
        'current': current,
        'transition': input_transition,
        'click': click,
        'captured': captured,
        'stages': [],
    }
    out = actor.folder / 'original-draft-restore-transition.json'
    out.write_text(json.dumps(facts, indent=2))
    assert click['reached'] and click['actual_pressed_changes'] > 0
    assert (
        captured and captured['intent']['id'] == target and captured['intent']['text'] == text
    ), 'Real selection captures the actual original editor before its held metadata response'
    assert any(
        row.get('method') == 'thread/read' and row['params']['threadId'] == target
        for row in original._session_wire(actor)[boundary:]
    ), 'The real original target read is held before resume'
    # Escape dismisses this actual waiting popup; the accepted selection remains
    # pending. No synthetic restored signal, draft setter or forced success.
    actor.command('manual_key', key='escape')
    assert not qml(actor, control_expression('assistant.sessionsDialog') + '.opened')
    facts['closed_before_input'] = actor.until(
        lambda _value: not qml(actor, control_expression('assistant.sessionsDialog') + '.visible')
    )
    actor.command('click', name='assistant.composer')
    facts['focused_before_input'] = actor.command('focused_input')['reply']
    out.write_text(json.dumps(facts, indent=2))
    assert facts['focused_before_input']['name'] == 'assistant.composer', (
        'Real IME must reach the original editor'
    )
    assert facts['focused_before_input']['text'] == text, (
        'Closure and the one physical click preserve the draft'
    )
    _original_restore_input(actor, input_transition, text, captured, facts, out)
    before_release = _original_composer(actor)
    usage_before = len(original._session_wire(actor, 'account/rateLimits/read'))
    release.touch()
    actor.command('refresh_usage')
    actor.until(lambda _value: not qml(actor, 'Session.assistant.sessionsLoading'))
    restored = _original_composer(actor)
    facts.update(
        before_release=before_release,
        restored=restored,
        wire=original._session_wire(actor)[boundary:],
    )
    out.write_text(json.dumps(facts, indent=2))
    assert len(original._session_wire(actor, 'account/rateLimits/read')) > usage_before
    _assert_original_restore_result(
        actor, input_transition, facts, captured, before_release, restored, target
    )


def test_original_composer_clear_preserves_active_ime_then_clears_settled_capture(main_actor):
    actor = main_actor([[]])
    actor.connect()
    actor.request('Actual original history before the IME Clear boundary.')
    actor.until(lambda value: value['ui']['state'] == 'idle' and bool(value['ui']['messages']))
    text = 'Original settled literal with an independent IME overlay.'
    original._type_original_draft(actor, text)
    before = _original_composer(actor)
    actor.command('manual_ime', preedit='Q', commit='')
    preedit = _original_composer(actor)
    # The original public Clear owner is invoked without a focus-changing mouse
    # event; this reaches the same native request/retire/commit signal path.
    qml(actor, '(function(){Session.assistant.clearHistory();return true;})()')
    actor.until(
        lambda value: value['ui']['state'] == 'idle' and original._rows_probe(actor)['count'] == 0
    )
    composing_clear = _original_composer(actor)
    facts = {'before': before, 'preedit': preedit, 'composing_clear': composing_clear}
    out = actor.folder / 'original-composer-ime-clear.json'
    out.write_text(json.dumps(facts, indent=2))
    assert (
        preedit['preedit'] == 'Q'
        and preedit['composing']
        and preedit['revision'] > before['revision']
    )
    assert composing_clear['text'] == text and composing_clear['published'] == text, (
        'Real logical conversation removal cannot erase its actual composing draft'
    )
    assert (
        composing_clear['clear'] is None
        and composing_clear['ownerRevision'] > before['ownerRevision']
        and composing_clear['submittedCount'] == 0
        and composing_clear['report'] is None
    ), 'Original retirement and matching Clear consume/reset their real presentation ownership'
    actor.command('manual_ime', preedit='', commit='')
    cancelled = _original_composer(actor)
    qml(actor, '(function(){Session.assistant.clearHistory();return true;})()')
    settled_clear = _original_composer(actor)
    facts.update(cancelled=cancelled, settled_clear=settled_clear)
    out.write_text(json.dumps(facts, indent=2))
    assert (
        cancelled['text'] == text
        and cancelled['revision'] > preedit['revision']
        and not cancelled['preedit']
    )
    assert (
        settled_clear['text'] == ''  # noqa: PLC1901 - require an exact empty string, never general falsiness
        and settled_clear['published'] == ''  # noqa: PLC1901 - require an exact empty string, never general falsiness
        and settled_clear['clear'] is None
    ), 'The actual same-text settled Clear remains effective after genuine IME cancellation'


def test_original_browser_opens_before_late_current_owner_refresh(main_actor):
    actor = main_actor([[]])
    original._session_configure(actor, session_fixture={'threads': [], 'page_size': 12})
    actor.connect()
    marker = 'e11.original.browser.open-order'
    source = (
        '(function(){const p='
        + control_expression('assistant.popup')
        + ',b='
        + control_expression('assistant.sessions')
        + ',d='
        + control_expression('assistant.sessionsDialog')
        + ';'
    )
    source += (
        (
            'if(!p||!b||!d)return false;const vm=Session.assistant,o=Qt.c'
            "reateQmlObject('import QtQuick; Item {property var facts:[];"
            "}',window.contentItem);o.objectName="
        )
        + json.dumps(marker)
        + ';'
    )
    source += (
        'let armed=true;const press=function(){if(armed&&b.pressed){a'
        'rmed=false;o.facts.push({event:"press",owner:p.assistant===v'
        'm});p.assistant=null;}};'
    )
    source += (
        'const opening=function(){o.facts.push({event:"aboutToShow",n'
        'ullOwner:p.assistant===null});p.assistant=vm;d.aboutToShow.d'
        'isconnect(opening);b.pressedChanged.disconnect(press);};'
    )
    source += 'b.pressedChanged.connect(press);d.aboutToShow.connect(opening);return true;})()'
    assert qml(actor, source), (
        'Observers bind the original current window controls before genuine input'
    )
    boundary = len(original._session_wire(actor, 'thread/list'))
    actor.command('click', name='assistant.sessions')
    original._session_wait(actor)
    facts = qml(actor, '(' + control_expression(marker) + ').facts')
    result = {
        'events': facts,
        'list_requests': original._session_wire(actor, 'thread/list')[boundary:],
        'opened': qml(actor, control_expression('assistant.sessionsDialog') + '.opened'),
    }
    (actor.folder / 'original-browser-open-owner-order.json').write_text(
        json.dumps(result, indent=2)
    )
    assert facts == [
        {'event': 'press', 'owner': True},
        {'event': 'aboutToShow', 'nullOwner': True},
    ], (
        'Original open occurs while the typed view owner is null and '
        'before callback restores its actual owner'
    )
    assert result['opened'] and result['list_requests'], (
        'Refresh uses the actual owner installed by the original opening effect'
    )


@pytest.mark.parametrize('activation_effect', ['restore_owner', 'retire_account', 'leave_null'])
def test_original_browser_row_activation_precedes_current_owner_selection(
    main_actor, activation_effect
):
    actor = main_actor([[], []])
    original._session_configure(actor, session_fixture={'threads': [], 'page_size': 12})
    target, current = original._two_genuine_session_threads(actor)
    actor.command('click', name='assistant.sessions')
    rows = original._session_wait(actor)
    assert target in {row['id'] for row in rows}
    marker = 'e11.original.browser.activation-order'
    source = (
        '(function(){const p='
        + control_expression('assistant.popup')
        + ',t='
        + control_expression('assistant.sessions.list')
        + ';'
    )
    source += (
        'const matches=testAppObjects.snapshot().filter(x=>x.threadId==='
        + json.dumps(target)
        + (
            '&&x.visible&&x.Window.window===window);if(!p||!t||matches.le'
            'ngth!==1)return false;const r=matches[0];'
        )
    )
    source += (
        'const areas=Array.from(r.children).filter(x=>typeof x.accept'
        'edButtons==="number"&&x.parent===r&&x.width>0&&x.width<r.wid'
        'th-1&&Math.abs(x.height-r.height)<=1);if(areas.length!==1)re'
        'turn false;const a=areas[0],vm=Session.assistant;'
    )
    source += (
        (
            "const o=Qt.createQmlObject('import QtQuick; Item {property v"
            "ar facts:[];}',window.contentItem);o.objectName="
        )
        + json.dumps(marker)
        + ';'
    )
    source += (
        'let armed=true;const press=function(){if(armed&&a.pressed){a'
        'rmed=false;p.assistant=null;o.facts.push({event:"press",null'
        'Owner:p.assistant===null});}};'
    )
    source += (
        'const started=function(id){o.facts.push({event:"selectionSta'
        'rted",id:id});};vm.sessionSelectionStarted.connect(started);'
    )
    source += (
        'const activated=function(index){o.facts.push({event:"rowActi'
        'vated",index:index,expected:r.index,nullOwner:p.assistant==='
        'null});t.rowActivated.disconnect(activated);a.pressedChanged'
        '.disconnect(press);'
    )
    if activation_effect == 'restore_owner':
        source += 'p.assistant=vm;'
    elif activation_effect == 'retire_account':
        source += 'p.assistant=vm;vm.signOut();'
    source += (
        '};a.pressedChanged.connect(press);t.rowActivated.connect(activated);return true;})()'
    )
    assert qml(actor, source), (
        'The original exact-ID row and row-owned area are unique before order is judged'
    )
    boundary = len(original._session_wire(actor))
    click = actor.command('session_row_click', thread_id=target)['reply']
    if activation_effect == 'restore_owner':
        actor.until(lambda _value: not qml(actor, 'Session.assistant.sessionsLoading'))
    facts = qml(actor, '(' + control_expression(marker) + ').facts')
    wire = original._session_wire(actor)[boundary:]
    (actor.folder / 'original-browser-activation-order.json').write_text(
        json.dumps(
            {
                'effect': activation_effect,
                'click': click,
                'events': facts,
                'wire': wire,
                'target': target,
                'current': current,
            },
            indent=2,
        )
    )
    assert click['reached'] and click['actual_pressed_changes'] > 0
    assert (
        len(facts) >= 2
        and facts[0] == {'event': 'press', 'nullOwner': True}
        and facts[1]['event'] == 'rowActivated'
        and facts[1]['nullOwner']
        and facts[1]['index'] == facts[1]['expected']
    ), 'The original table activation effect precedes every view-owner selection lookup'
    selected = [row for row in facts if row['event'] == 'selectionStarted']
    if activation_effect == 'restore_owner':
        assert selected and selected[0]['id'] == target
        assert any(
            row.get('method') == 'thread/resume' and row['params']['threadId'] == target
            for row in wire
        ), 'Selection reaches the real current owner installed by the table activation callback'
    else:
        assert not selected and not any(row.get('method') == 'thread/read' for row in wire), (
            'A real activation remains observable when its callback remov'
            'es or retires selection eligibility'
        )
    if activation_effect == 'leave_null':
        qml(
            actor,
            '(function(){'
            + control_expression('assistant.popup')
            + '.assistant=Session.assistant;return true;})()',
        )


def _original_footer_geometry(actor):
    return qml(
        actor,
        '(function(){const d='
        + control_expression('assistant.sessionsDialog')
        + (
            ';if(!d||!d.footer)return null;const f=d.footer,buttons=[];fo'
            'r(let i=0;i<f.count;++i){const b=f.itemAt(i);buttons.push(b?'
            '{visible:b.visible,implicitWidth:b.implicitWidth,text:b.text'
            '}:null);}return {count:f.count,spacing:f.spacing,natural:f.n'
            'aturalButtonWidth,content:f.contentWidth,buttons:buttons};})'
            '()'
        ),
    )


def _assert_original_footer_relation(value):
    assert value and value['count'] == len(value['buttons'])
    expected = sum(
        button['implicitWidth'] for button in value['buttons'] if button and button['visible']
    )
    expected += max(0, value['count'] - 1) * value['spacing']
    assert (
        abs(value['natural'] - expected) <= 0.001 and abs(value['content'] - expected) <= 0.001
    ), (
        'Actual footer width follows each current visible button and '
        'the original full-count spacing relation'
    )


def test_original_browser_footer_dependencies_remain_live_with_null_view_owner(main_actor):
    actor = main_actor([[]])
    original._session_configure(actor, session_fixture={'threads': [], 'page_size': 12})
    actor.connect()
    actor.command('click', name='assistant.sessions')
    original._session_wait(actor)
    d = control_expression('assistant.sessionsDialog')
    p = control_expression('assistant.popup')
    marker = 'e11.original.browser.footer-holder'
    assert qml(
        actor,
        '(function(){const d='
        + d
        + ',p='
        + p
        + (
            ';if(!d||!p)return false;const f=d.footer;const buttons=[];fo'
            'r(let i=0;i<f.count;++i){const b=f.itemAt(i);if(b&&b.text==='
            '"Refresh")buttons.push(b);}if(buttons.length!==1)return fals'
            "e;const b=buttons[0],o=Qt.createQmlObject('import QtQuick; I"
            'tem {property var original:null;property var button:null;pro'
            "perty var owner:null;property var extra:null;}',window.conte"
            'ntItem);o.objectName='
        )
        + json.dumps(marker)
        + (
            ';o.button=b;o.owner=p.assistant;o.original={spacing:f.spacin'
            'g,visible:b.visible,pixel:b.font.pixelSize,name:b.objectName'
            '};b.objectName="e11.original.browser.footer.refresh";return '
            'true;})()'
        ),
    )
    snapshots = []
    out = actor.folder / 'original-browser-footer-dependencies.json'

    def retain(stage):
        value = _original_footer_geometry(actor)
        snapshots.append({'stage': stage, 'geometry': value})
        out.write_text(json.dumps(snapshots, indent=2))
        _assert_original_footer_relation(value)
        return value

    baseline = retain('baseline')
    # A real current named button is used only as a test-owned input label;
    # no production ID or synthetic clicked() signal is added.
    boundary = len(original._session_wire(actor, 'thread/list'))
    actor.command('click', name='e11.original.browser.footer.refresh')
    original._session_wait(actor)
    assert len(original._session_wire(actor, 'thread/list')) > boundary, (
        'Genuine original footer Refresh reaches its existing backend owner'
    )
    # Scalar session reads leave a compact model envelope. Obtain the existing
    # current full scene before the strict passive census and null-owner action.
    (actor.folder / 'original-footer-current-full-scene.json').write_text(
        json.dumps(actor.command('inspect'), indent=2)
    )
    holder = control_expression(marker)
    try:
        qml(actor, '(function(){' + p + '.assistant=null;return true;})()')
        qml(actor, '(function(){' + d + '.footer.spacing+=3;return true;})()')
        spacing = retain('null_owner_spacing')
        assert spacing['spacing'] == baseline['spacing'] + 3
        qml(actor, '(function(){const o=' + holder + ';o.button.visible=false;return true;})()')
        hidden = retain('null_owner_visibility')
        assert hidden['natural'] < spacing['natural'], (
            'Actual visible-button dependency remains live without a view owner'
        )
        qml(
            actor,
            '(function(){const o='
            + holder
            + (
                ';o.button.visible=true;o.button.font.pixelSize=o.original.pi'
                'xel+7;return true;})()'
            ),
        )
        font = retain('null_owner_font')
        assert abs(font['natural'] - spacing['natural']) > 0.001, (
            'Actual font-driven implicit width is captured by the original geometry binding'
        )
        # Dynamic item membership uses the existing real DialogButtonBox
        # Container API and a standard control, not a planted width result.
        assert qml(
            actor,
            '(function(){const o='
            + holder
            + ',f='
            + d
            + (
                ".footer;o.extra=Qt.createQmlObject('import QtQuick; import Q"
                'tQuick.Controls; Button {text:"Independent additional footer'
                ' control"}\',f);f.addItem(o.extra);return true;})()'
            ),
        )
        added = retain('null_owner_count')
        assert added['count'] == font['count'] + 1 and added['natural'] > font['natural'], (
            'Real added control membership invalidates count and itemAt dependencies'
        )
        qml(
            actor,
            '(function(){const o='
            + holder
            + ',f='
            + d
            + ('.footer;f.removeItem(o.extra);o.extra.destroy();o.extra=null;return true;})()'),
        )
        removed = retain('null_owner_remove')
        assert (
            removed['count'] == font['count']
            and abs(removed['natural'] - font['natural']) <= 0.001
        )
    finally:
        qml(
            actor,
            '(function(){const o='
            + holder
            + ',p='
            + p
            + ',f='
            + d
            + (
                '.footer;p.assistant=o.owner;if(o.extra){f.removeItem(o.extra'
                ');o.extra.destroy();}f.spacing=o.original.spacing;o.button.v'
                'isible=o.original.visible;o.button.font.pixelSize=o.original'
                '.pixel;o.button.objectName=o.original.name;return true;})()'
            ),
        )
    retain('restored_owner')


_ORIGINAL_NULL_PUBLICATION = {
    'column': -1,
    'description': 'TypeError: Value is null and could not be converted to an object',
    'event': 'warning',
    'line': 623,
    'message_type': 1,
    'object_available': False,
    'object_name': '',
    'operation': 'manual_ime',
    'phase': 'command',
    'rendered': (
        'qrc:/qt/qml/edi/app/qml/Components/AssistantComposer.qml:623'
        ': TypeError: Value is null and could not be converted to an '
        'object'
    ),
    'url': 'qrc:/qt/qml/edi/app/qml/Components/AssistantComposer.qml',
}


def _assert_original_ime_publications(facts, stderr):
    before = bytes.fromhex(facts['warning_before_hex'])
    after = bytes.fromhex(facts['ime_warning_capture_hex'])
    assert after.startswith(before), 'The actual native warning log must remain append-only'
    prefix = [json.loads(line) for line in before.splitlines()]
    warnings = [json.loads(line) for line in after[len(before) :].splitlines()]
    first = sum(row['event'] == 'warning' for row in prefix)
    assert len(facts['ime_commands']) == 2, 'Both original real IME actions are mandatory'
    expected = [
        {**_ORIGINAL_NULL_PUBLICATION, 'command_sequence': str(sequence), 'ordinal': first + index}
        for index, sequence in enumerate(facts['ime_commands'])
    ]
    assert warnings == expected, (
        'Each real IME action requires exactly its original623 text-h'
        'andler error; cold preedit/composing handlers and observer e'
        'valuations add no warning'
    )
    assert stderr == ''.join(row['rendered'] + '\n' for row in expected), (
        'Both exact original IME warnings need their separate stderr '
        'counterparts without extra errors'
    )


def test_original_composer_revision_effects_precede_null_owner_text_publication(main_actor):
    actor = main_actor([[]])
    actor.connect()
    text = 'Actual original editor remains its own input owner.'
    original._type_original_draft(actor, text)
    marker = 'e11.original.composer.null-owner'
    e = control_expression('assistant.composer')
    p = control_expression('assistant.popup')
    assert qml(
        actor,
        '(function(){const e='
        + e
        + (
            ';if(!e)return false;let c=e.parent;while(c&&typeof c.textRev'
            'ision!=="number")c=c.parent;if(!c)return false;const o=Qt.cr'
            "eateQmlObject('import QtQuick; Item {property var composer:n"
            "ull;}',window.contentItem);o.objectName="
        )
        + json.dumps(marker)
        + ';o.composer=c;c.assistant=null;return c.assistant===null;})()',
    )
    before = _original_composer(actor)
    stderr_path = actor.folder / 'host.stderr'
    stderr_offset = len(stderr_path.read_bytes())
    out = actor.folder / 'original-composer-null-owner-effects.json'
    facts = {
        'before': before,
        'warning_before_hex': (actor.folder / 'qml-warning-events.jsonl').read_bytes().hex(),
        'ime_commands': [],
    }
    out.write_text(json.dumps(facts, indent=2))
    try:
        actor.command('manual_ime', preedit='Q', commit='')
        facts['ime_commands'].append(actor._command_sequence)
        preedit = _original_composer(actor)
        actor.command('manual_ime', preedit='', commit='')
        facts['ime_commands'].append(actor._command_sequence)
        cancelled = _original_composer(actor)
        facts['ime_warning_capture_hex'] = (
            (actor.folder / 'qml-warning-events.jsonl').read_bytes().hex()
        )
        preedit_stderr = stderr_path.read_bytes()[stderr_offset:].decode(errors='replace')
        facts.update(preedit=preedit, cancelled=cancelled, preedit_stderr=preedit_stderr)
        out.write_text(json.dumps(facts, indent=2))
        assert (
            preedit['text'] == text
            and preedit['preedit'] == 'Q'
            and preedit['revision'] > before['revision']
        )
        assert (
            cancelled['text'] == text
            and not cancelled['preedit']
            and cancelled['revision'] > preedit['revision']
        )
        assert cancelled['published'] == text, (
            'Real original IME keeps the canonical draft despite the required text-handler errors'
        )
        assert preedit['composing'] and not cancelled['composing'], (
            'The real preedit and cancellation still change actual composition state'
        )
        _assert_original_ime_publications(facts, preedit_stderr)
        facts['text_stderr_offset'] = len(stderr_path.read_bytes())
        facts['text_warning_before_hex'] = (
            (actor.folder / 'qml-warning-events.jsonl').read_bytes().hex()
        )
        actor.command('manual_text', text=' New actual text.')
        facts['text_command'] = actor._command_sequence
        changed = _original_composer(actor)
        text_stderr = stderr_path.read_bytes()[facts['text_stderr_offset'] :].decode(
            errors='replace'
        )
        facts.update(
            changed=changed,
            text_stderr=text_stderr,
            all_text_stderr=stderr_path.read_bytes()[stderr_offset:].decode(errors='replace'),
            text_warning_capture_hex=(actor.folder / 'qml-warning-events.jsonl')
            .read_bytes()
            .hex(),
        )
        out.write_text(json.dumps(facts, indent=2))
        assert (
            changed['text'] == text + ' New actual text.'
            and changed['revision'] > cancelled['revision']
        ), (
            'Actual text mutation and its original revision increment hap'
            'pen before a null view-owner publication attempt'
        )
        assert changed['published'] == text and 'TypeError' in text_stderr, (
            'The original null-owner publication fails after its input ef'
            'fects and cannot write a different backend draft'
        )
    finally:
        qml(
            actor,
            '(function(){const o='
            + control_expression(marker)
            + ',p='
            + p
            + (
                ';o.composer.assistant=Qt.binding(function(){return p.assista'
                'nt;});return true;})()'
            ),
        )
