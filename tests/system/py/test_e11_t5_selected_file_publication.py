"""Real selected-file notifications preserve the original Composer revision relation."""

import hashlib
import json

import test_e11_t5_dev_native_integration as base

main_actor = base.main_actor
MARKER = 'e11.selectedFiles.publication271'
OBSERVER = """import QtQuick
QtObject {
    id: witness
    objectName: "e11.selectedFiles.publication271"
    property var composerOwner: null
    property var modelOwner: null
    property var entries: []
    function record(kind) {
        entries = entries.concat([{
            kind: kind, revision: composerOwner.consentFileRevision,
            pending: composerOwner.pendingFileCount, draft: composerOwner.hasDraft,
            count: modelOwner.count, current: composerOwner.assistant.selectedFiles === modelOwner
        }]);
    }
    property Connections notifications: Connections {
        target: witness.modelOwner
        function onCountChanged() { witness.record("count"); }
        function onDataChanged() { witness.record("data"); }
    }
}"""


def _save(actor, stage, value):
    (actor.folder / (stage + '.json')).write_text(json.dumps(value, indent=2) + '\n')
    return value


def _query(actor, stage, expression):
    envelope = actor.command('evaluate', expression='JSON.stringify((' + expression + '))')
    _save(actor, stage + '-raw', {'expression': expression, 'envelope': envelope})
    value = json.loads(envelope['reply']['value'])
    return _save(actor, stage, value)


def _snapshot(actor, stage):
    return _query(
        actor,
        stage,
        '(function(){const o='
        + base._whole_window_objects_expression()
        + '.filter(x=>x.objectName==='
        + json.dumps(MARKER)
        + ');if(o.length!==1)throw Error("Exact original notification witness missing");'
        'const w=o[0],c=w.composerOwner;return {revision:c.consentFileRevision,'
        'pending:c.pendingFileCount,draft:c.hasDraft,count:w.modelOwner.count,'
        'current:c.assistant===Session.assistant&&c.assistant.selectedFiles===w.modelOwner,'
        'events:w.entries};})()',
    )


def test_actual_selected_file_signals_each_advance_revision_before_publication(
    main_actor, tmp_path
):
    actor = main_actor([[]])
    files = base._attachment_fixtures(tmp_path, 2)
    physical = {str(path): hashlib.sha256(path.read_bytes()).hexdigest() for path in files}
    setup = _query(
        actor,
        'selected-publication-setup',
        '(function(){const all='
        + base._whole_window_objects_expression()
        + ';const owners=all.filter(x=>typeof x.consentFileRevision==="number"'
        '&&typeof x.pendingFileCount==="number"&&typeof x.hasDraft==="boolean");'
        'if(owners.length!==1)throw Error("Exact real Composer owner missing");'
        'const c=owners[0],w=Qt.createQmlObject('
        + json.dumps(OBSERVER)
        + ',contentItem,"selectedPublication271");'
        'w.composerOwner=c;w.modelOwner=c.assistant.selectedFiles;'
        'return {same:c.assistant===Session.assistant,count:w.modelOwner.count,'
        'revision:c.consentFileRevision,pending:c.pendingFileCount,draft:c.hasDraft};})()',
    )
    assert setup['same'] and setup['count'] == setup['pending'] == 0, (
        'The real new Composer begins with no selected or pending rows'
    )
    assert not setup['draft'], 'An empty initial editor has no invented attachment draft'
    token = actor.begin_current_file_selection()
    added = actor.command('selected_add', token=token, paths=[str(path) for path in files])
    _save(actor, 'selected-publication-add-reply', added)
    rows = base._attachment_rows(actor)
    _save(actor, 'selected-publication-admitted-rows', rows)
    stages = [_snapshot(actor, 'selected-publication-added')]
    assert added['reply']['added'] and len(rows) == 2 and all(row['pending'] for row in rows), (
        'Two actual files enter through the existing current-owner admission path'
    )
    for index, row in enumerate(rows):
        removed = _query(
            actor,
            'selected-publication-remove-' + str(index),
            'Session.assistant.removeSelectedFile(' + json.dumps(row['id']) + ')',
        )
        stages.append(_snapshot(actor, 'selected-publication-after-remove-' + str(index)))
        assert removed is True, 'The existing public remove action accepts its genuine admitted ID'
    _save(actor, 'selected-publication-all-stages', {'setup': setup, 'stages': stages})
    for stage, count in zip(stages, (2, 1, 0), strict=True):
        assert stage['current'] and stage['count'] == stage['pending'] == count, (
            'The same original owner publishes the actual remaining pending population'
        )
        assert stage['draft'] is (count > 0), (
            'Attachment-only draft state follows actual pending files'
        )
        assert stage['events'], 'A real selected-file model notification reaches the witness'
        assert stage['revision'] == setup['revision'] + len(stage['events']), (
            'Each count/data signal increments once without coalescing or role filtering'
        )
        assert all(
            event['current'] and event['revision'] == setup['revision'] + number
            for number, event in enumerate(stage['events'], 1)
        ), 'Each original handler increments before the later witness'
    assert {'count', 'data'} <= {event['kind'] for event in stages[-1]['events']}, (
        'Both genuine insertion/count and scalar data notifications are exercised'
    )
    assert all(
        hashlib.sha256(path.read_bytes()).hexdigest() == physical[str(path)] for path in files
    ), 'Presentation and removal preserve the exact original physical file bytes'
    wire = [json.loads(line) for line in actor.trace.read_text().splitlines()]
    _save(actor, 'selected-publication-wire', wire)
    assert not any(row.get('method') == 'turn/start' for row in wire), (
        'Presentation notifications and file removal never submit a provider task'
    )
