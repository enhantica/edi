// SPDX-License-Identifier: BSD-3-Clause
import QtQuick
import QtTest

import edi.app

// Send to developers in an error popup, and the crash dialog's report, open Help and feedback as a problem with the
// message in its box, the log box ticked and the unreadable file attached, whether the form was closed or open.
Item {
    id: root

    width: 1200
    height: 900

    readonly property string structure: ApplicationInfo.localPath(Qt.resolvedUrl("../../../docs/user/cli/pd-neut-cwl_cosio-d20/project/structures/cosio.edi"))

    FeedbackDialog {
        id: form

        roomWidth: root.width
        parent: root
    }
    ErrorDialog {
        id: popup

        objectName: "test.error"
        parent: root
    }
    // As the window does (Main.qml).
    Connections {
        target: AppState
        function onProblemReported(message, file) {
            form.openAs("problem", "", message, file === "" ? [] : [ApplicationInfo.fileAttachment(file)]);
        }
        function onCrashReported(log, text) {
            form.openAs("problem", log, text, []);
        }
    }

    TestCase {
        name: "ErrorSend"
        when: windowShown

        function findNamed(item, name) {
            if (!item)
                return null;
            if (item.objectName === name)
                return item;
            for (let i = 0; i < item.children.length; ++i) {
                const found = findNamed(item.children[i], name);
                if (found)
                    return found;
            }
            return null;
        }
        function messageBox() {
            return findNamed(form.contentItem, "feedback.text");
        }
        function includeBox() {
            return findNamed(form.contentItem, "feedback.include");
        }
        function sendFromPopup(message, file) {
            popup.show("The project was not opened", message, file);
            tryVerify(() => popup.opened);
            const send = findNamed(popup.contentItem, "test.error.send");
            verify(send && send.visible, "the popup offers Send to developers");
            verify(!findNamed(popup.contentItem, "test.error.copy"), "no Copy button");
            mouseClick(send);
            tryVerify(() => form.opened);
        }
        function cleanup() {
            popup.close();
            form.close();
            tryVerify(() => !form.visible && !popup.visible);
        }

        function test_a_send_while_the_form_is_closed() {
            includeBox().checked = false;
            sendFromPopup("not a project directory", root.structure);
            compare(form.kind, "problem");
            tryCompare(messageBox(), "text", "not a project directory");
            verify(includeBox().checked);
            compare(form.attachedFiles.length, 1);
            compare(form.attachedFiles[0].name, "cosio.edi");
        }
        function test_b_send_while_the_form_is_open() {
            form.openAs("feedback", "");
            tryVerify(() => form.opened);
            sendFromPopup("not a project directory", root.structure);
            compare(form.kind, "problem");
            tryCompare(messageBox(), "text", "not a project directory");
            verify(includeBox().checked);
            compare(form.attachedFiles.length, 1);
        }
        function test_c_the_crash_report() {
            AppState.crashReported("# EasyDiffraction run log\n", "EasyDiffraction closed unexpectedly.");
            tryVerify(() => form.opened);
            compare(form.kind, "problem");
            tryCompare(messageBox(), "text", "EasyDiffraction closed unexpectedly.");
            verify(includeBox().checked);
            compare(form.attachedLog, "# EasyDiffraction run log\n");
        }
    }
}
