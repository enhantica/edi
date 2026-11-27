// SPDX-License-Identifier: BSD-3-Clause
import QtQuick
import QtQuick.Controls
import QtTest

import edi.app

// The assistant closes a project that is not empty only on the user's answer, a saved one too (edi ADR-0057): the window
// asks, Cancel keeps the project, and only Close project lets the action run. The user's own open asks nothing.
TestCase {
    id: test

    name: "AssistantCloseQuestion"
    when: windowShown

    property var window: null
    property int ran: 0
    property int abandoned: 0
    readonly property var question: findChild(window, "unsavedChanges")
    readonly property url lbco: Qt.resolvedUrl("../../../docs/user/cli/pd-neut-cwl_lbco-hrpt/project")

    function initTestCase() {
        const component = Qt.createComponent("qrc:/qt/qml/edi/app/qml/Main.qml");
        verify(component.status === Component.Ready, component.errorString());
        window = component.createObject(null);
        verify(window);
        window.visible = true;
        tryVerify(() => findChild(window, "unsavedChanges") !== null, 10000);
    }
    function cleanupTestCase() {
        Session.closeProject();
        window.destroy();
    }
    function init() {
        ran = 0;
        abandoned = 0;
    }
    function ask(closing) {
        AppState.afterChanges(() => ++test.ran, () => ++test.abandoned, false, closing);
    }
    function open() {
        verify(Session.openProject(lbco), Session.lastError);
        verify(!Session.project.modified);
    }

    function test_a_a_saved_project_asks_and_cancel_keeps_it() {
        open();
        const project = Session.project;
        ask("create");
        tryVerify(() => question.opened, 5000);
        verify(question.standardButton(Dialog.Save) === null, "nothing to save");
        verify(question.standardButton(Dialog.Discard) === null, "nothing to discard");
        verify(question.standardButton(Dialog.Yes) !== null && question.standardButton(Dialog.Cancel) !== null);
        compare(ran, 0);
        question.reject();
        tryVerify(() => !question.visible, 5000);
        wait(100);
        compare(ran, 0);
        compare(abandoned, 1);
        compare(Session.project, project);
    }
    function test_b_close_project_lets_it_run_once() {
        open();
        ask("conversation");
        tryVerify(() => question.opened, 5000);
        question.accept();
        tryCompare(test, "ran", 1, 5000);
        tryVerify(() => !question.visible, 5000);
        wait(100);
        compare(ran, 1);
        compare(abandoned, 0);
    }
    function test_c_unsaved_changes_offer_save_and_discard() {
        open();
        Session.project.title = "changed";
        tryVerify(() => Session.project.modified, 5000);
        ask("create");
        tryVerify(() => question.opened, 5000);
        verify(question.standardButton(Dialog.Save) !== null);
        verify(question.standardButton(Dialog.Discard) !== null);
        question.reject();
        tryCompare(test, "abandoned", 1, 5000);
        compare(ran, 0);
    }
    function test_d_the_users_own_action_and_an_empty_project_ask_nothing() {
        open();
        ask("");
        tryCompare(test, "ran", 1, 5000);
        verify(!question.visible);
        verify(Session.createProject("empty", ""));
        verify(!Session.project.modified);
        ask("create");
        tryCompare(test, "ran", 2, 5000);
        verify(!question.visible);
    }
}
