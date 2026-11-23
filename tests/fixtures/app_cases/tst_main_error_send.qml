// SPDX-License-Identifier: BSD-3-Clause
import QtQuick
import QtTest

import edi.app

// The same three ways through the whole window (Main.qml): the refusal popup's Send while Help and feedback is closed,
// the same while it is open, and the crash report; each opens the form as a problem with the message in its box and the
// log box ticked.
TestCase {
    id: test

    name: "MainErrorSend"
    when: windowShown

    property var window: null

    function initTestCase() {
        const component = Qt.createComponent("qrc:/qt/qml/edi/app/qml/Main.qml");
        verify(component.status === Component.Ready, component.errorString());
        window = component.createObject(null);
        verify(window);
        window.visible = true;
        tryVerify(() => findChild(window, "refusal.dialog") !== null, 10000);
    }
    function cleanupTestCase() {
        window.destroy();
    }
    function cleanup() {
        findChild(window, "refusal.dialog").close();
        findChild(window, "feedback.form").close();
        tryVerify(() => !findChild(window, "feedback.form").visible);
    }
    function sendRefusal(message) {
        const refusal = findChild(window, "refusal.dialog");
        refusal.show(qsTr("The project was not opened"), message, "");
        tryVerify(() => refusal.opened);
        verify(findChild(window, "refusal.dialog.copy") === null, "no Copy button");
        mouseClick(findChild(window, "refusal.dialog.send"));
    }
    function expectProblem(message) {
        const form = findChild(window, "feedback.form");
        tryVerify(() => form.opened);
        compare(form.kind, "feedback", "The error report uses the shared feedback route");
        tryCompare(findChild(window, "feedback.text"), "text", message);
        verify(findChild(window, "feedback.include").checked);
    }

    function test_a_form_closed() {
        findChild(window, "feedback.include").checked = false;
        sendRefusal("not a project directory");
        expectProblem("not a project directory");
    }
    function test_b_form_open() {
        AppState.feedbackRequested("feedback", "");
        tryVerify(() => findChild(window, "feedback.form").opened);
        sendRefusal("not a project directory");
        expectProblem("not a project directory");
    }
    function test_c_crash_report() {
        AppState.crashReported("# EasyDiffraction run log\n", "EasyDiffraction closed unexpectedly.");
        expectProblem("EasyDiffraction closed unexpectedly.");
        compare(findChild(window, "feedback.form").attachedLog, "# EasyDiffraction run log\n");
    }
}
