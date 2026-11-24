"""Drive the normal composer while the original assistant's real fit is running."""

import json

import pytest

from tests.integration.app.test_assistant_misfit_workflow import actor_in, replies
from tests.system.py import test_e11_t5_dev_native_integration as native

MESSAGES = ('First queued fit question.', 'Second queued fit question.')


def delivered(actor):
    rows = map(json.loads, actor.trace.read_text().splitlines())
    return [
        (
            index,
            row['params']['threadId'],
            {entry.get('text') for entry in row['params']['input'] if entry.get('type') == 'text'},
        )
        for index, row in enumerate(rows)
        if row.get('method') in {'turn/start', 'turn/steer'}
    ]


@pytest.mark.parametrize('stop', [False, True], ids=['deliver', 'cancel'])
def test_ordinary_send_during_fit_preserves_order_and_conversation(tmp_path, stop):
    turns = [[native.tool_call('run_fit', 'queued-fit')], [], [], []]
    actor = actor_in(tmp_path / 'fit-composer', turns)
    try:
        editor = native.control_expression('assistant.composer')
        send = native.control_expression('assistant.send')
        stop_button = native.control_expression('assistant.stop')
        witness = native.control_expression('fitQueueWitness')
        assert native.qml(
            actor,
            f"""
            (function() {{
                const owner = Session.project, fit = owner.fit;
                const probe = Qt.createQmlObject(
                    'import QtQuick; Item {{ objectName: "fitQueueWitness";'
                    + ' property var receipt: null }}',
                    contentItem);
                const submit = () => {{
                    if (!fit.running) return;
                    fit.runningChanged.disconnect(submit);
                    const editor = {editor}, button = {send}, stopButton = {stop_button};
                    const admitted = [];
                    for (const text of {json.dumps(MESSAGES)}) {{
                        editor.text = text;
                        const enabled = button.visible && button.enabled;
                        if (enabled) button.clicked();
                        admitted.push({{enabled, cleared: editor.text === "",
                                        running: fit.running}});
                    }}
                    const stopping = stopButton.visible && stopButton.enabled;
                    probe.receipt = {{admitted, stopping, sameProject: Session.project === owner}};
                    if ({json.dumps(stop)} && stopping) stopButton.clicked();
                }};
                fit.runningChanged.connect(submit);
                return true;
            }})()
            """,
        ), 'The original project fit supplies the synchronous observation point'
        peer = actor.folder / 'peer.json'
        peer.write_text(
            json.dumps(json.loads(peer.read_text()) | {'acknowledge_queue_steers': True})
        )
        actor.request('Run the fit in the current conversation.')
        actor.until(lambda _: native.qml(actor, witness + '.receipt') is not None, seconds=15)
        receipt = native.qml(actor, witness + '.receipt')
        assert receipt['sameProject'], 'Ordinary Send uses the project that owns the running fit'
        assert receipt['admitted'] == [{'enabled': True, 'cleared': True, 'running': True}] * 2, (
            'Each ordinary Send accepts and releases its draft while the real fit remains active'
        )
        if stop:
            assert receipt['stopping'], 'The current conversation exposes its ordinary Stop action'
            actor.until(lambda row: row['ui']['state'] == 'idle', seconds=20)
            follow_up = 'Follow-up after the cancelled wait.'
            actor.request(follow_up)
            actor.until(
                lambda row: (
                    row['ui']['state'] == 'idle'
                    and any(follow_up in body for _, _, body in delivered(actor))
                ),
                seconds=20,
            )
            assert all(text not in body for _, _, body in delivered(actor) for text in MESSAGES), (
                'Stopping the fit drops both queued drafts and leaves future Send usable'
            )
        else:
            actor.until(
                lambda row: (
                    row['ui']['state'] == 'idle'
                    and any(MESSAGES[1] in body for _, _, body in delivered(actor))
                ),
                seconds=25,
            )
            original, *later = delivered(actor)
            assert [(thread, body.intersection(MESSAGES)) for _, thread, body in later] == [
                (original[1], {text}) for text in MESSAGES
            ], 'Each queued message reaches the original conversation in its own turn and in order'
            assert replies(actor)['queued-fit']['success'], (
                'The original assistant fit produced a real completion'
            )
            incoming = map(
                json.loads, actor.trace.with_suffix('.sent.jsonl').read_text().splitlines()
            )
            (fit_id,) = (
                row['id']
                for row in incoming
                if row.get('params', {}).get('callId') == 'queued-fit'
            )
            requests = map(json.loads, actor.trace.read_text().splitlines())
            (settled,) = (i for i, row in enumerate(requests) if row.get('id') == fit_id)
            assert all(settled < index for index, _, _ in later), (
                'Delivery starts after the running fit settles, even when both drafts arrive early'
            )
    finally:
        actor.close()


def test_fit_time_send_keeps_the_original_pending_attachment(tmp_path):
    actor = actor_in(tmp_path / 'attached-fit', [[], []])
    try:
        actor.request('Keep this conversation ready for a manual fit.')
        actor.until(lambda row: row['ui']['state'] == 'idle' and bool(delivered(actor)))
        attachment = tmp_path / 'fit-queue-original.txt'
        attachment.write_text('An independent immutable attachment for this queued draft.')
        token = actor.begin_current_file_selection()
        assert actor.command('selected_add', token=token, paths=[str(attachment)])['reply'][
            'added'
        ], 'The real picker attaches the independent test file to the unsent draft'
        actor.command('accept_context')
        actor.until(lambda _: native.qml(actor, 'Session.assistant.draftAdmissionReady'))
        original = native._attachment_rows(actor)[0]
        editor = native.control_expression('assistant.composer')
        send = native.control_expression('assistant.send')
        witness = native.control_expression('attachedFitWitness')
        assert native.qml(
            actor,
            f"""
            (function() {{
                const fit = Session.project.fit;
                const probe = Qt.createQmlObject(
                    'import QtQuick; Item {{ objectName: "attachedFitWitness";'
                    + ' property var receipt: null }}', contentItem);
                const observe = () => {{
                    if (!fit.running) return;
                    fit.runningChanged.disconnect(observe);
                    const editor = {editor}, send = {send};
                    editor.text = {json.dumps(MESSAGES[0])};
                    const enabled = send.visible && send.enabled;
                    if (enabled) send.clicked();
                    probe.receipt = {{enabled, running: fit.running,
                                      queued: Session.assistant.queuedMessages.count}};
                }};
                fit.runningChanged.connect(observe);
                fit.start();
                return true;
            }})()
            """,
        ), 'The public Fit entry observes the ordinary Send during the real fit'
        actor.until(lambda _: native.qml(actor, witness + '.receipt') is not None, seconds=15)
        receipt = native.qml(actor, witness + '.receipt')
        assert receipt == {'enabled': True, 'running': True, 'queued': 1}, (
            'An ordinary file-bearing Send waits behind the active fit'
        )
        actor.until(
            lambda row: (
                row['ui']['state'] == 'idle'
                and any(MESSAGES[0] in texts for _, _, texts in delivered(actor))
            ),
            seconds=20,
        )
        history = json.loads(native._rows_history_file(actor).read_bytes())
        accepted = [
            item['payload']['files']
            for item in native.objects(history)
            if item.get('kind') == 'user'
            and item.get('text') == MESSAGES[0]
            and isinstance(item.get('payload'), dict)
            and item['payload'].get('type') == 'ediInput'
        ]
        assert len(accepted) == 1, 'The queued draft is delivered once to the real history'
        assert [(item['id'], item['name'], item['bytes']) for item in accepted[0]] == [
            (original['id'], attachment.name, attachment.stat().st_size)
        ], 'The drained message contains the admitted file identity, label, and original size'
    finally:
        actor.close()
