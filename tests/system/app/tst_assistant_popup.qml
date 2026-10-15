import QtQuick
import QtQuick.Controls
import QtTest
import edi.app
import EasyApplication.Gui.Style as EaStyle
import EdiAcceptance 1.0
import "../../unit/app/UiInteraction.js" as Ui

// Owner 99d50f71f supersedes the former second-dock and alternate-entry tests.
// Real Main/Session only. No provider, seeded message model or synthetic busy state.
TestCase {
    name: "AssistantPopup"
    when: windowShown
    property var window
    property var popup
    property var assistant
    property var oldSide
    property var oldTheme
    Component {
        id: application
        Main {}
    }

    function item(name) {
        const found = findChild(window, name);
        verify(found !== null, "I16/popup: the actual application owns " + name);
        return found;
    }
    function rendered() {
        verify(waitForRendering(window.contentItem), "I16/popup: actual window renders after interaction");
    }
    function rect(control) {
        const point = control.mapToItem(window.contentItem, 0, 0);
        return [point.x, point.y, control.width, control.height];
    }
    function sameRect(actual, expected) {
        for (let i = 0; i < 4; ++i)
            verify(Math.abs(actual[i] - expected[i]) < 0.5, "I16/popup: actual sidebar/main rectangle stays aligned");
    }
    function toggle() {
        const control = item("assistant.toggle");
        verify(control.visible && control.enabled, "I16/popup: existing appbar button remains actionable");
        mouseClick(control);
        rendered();
    }
    function capture(stem) {
        let finished = false;
        let saved = false;
        verify(window.contentItem.grabToImage(result => {
            saved = result.saveToFile(stem + ".png");
            finished = true;
        }), "I16/popup: capture comes from the actual rendered Main window");
        tryVerify(() => finished, 2000, "I16/popup: actual window capture completes");
        verify(saved, "I16/popup: actual rendered capture is saved without image synthesis");
    }
    function initTestCase() {
        oldSide = Preferences.sideBarSide;
        oldTheme = EaStyle.Colors.theme;
        window = application.createObject(null);
        verify(window !== null, "I16/popup: production Main instantiates in the normal native runner");
        rendered();
        popup = item("assistant.popup");
        assistant = Session.assistant;
        compare(popup.visible, false, "I16/popup: a fresh session starts with chat closed");
        compare(assistant.connected, false, "I12/popup: native availability does not imply provider connection");
    }
    function cleanupTestCase() {
        if (popup.visible)
            toggle();
        Session.closeProject();
        Preferences.sideBarSide = oldSide;
        EaStyle.Colors.theme = oldTheme;
        window.destroy();
    }
    function test_home_appbar_only_and_no_auto_dismiss() {
        Session.closeProject();
        window.appBarCentralTabs.currentIndex = 0;
        rendered();
        const main = item("workflow.home.mainContent");
        const before = rect(main);
        window.contentItem.forceActiveFocus();
        keyClick(Qt.Key_A, Qt.ControlModifier | Qt.ShiftModifier);
        compare(popup.visible, false, "I16/popup: retired global shortcut cannot open chat");
        const button = item("assistant.toggle");
        button.forceActiveFocus();
        keyClick(Qt.Key_Space);
        tryCompare(popup, "visible", true, 500, "I16/popup: normal keyboard activation of appbar opens chat");
        compare(popup.modal, false, "I16/popup: sidebar popup does not block the whole window");
        compare(popup.dim, false, "I16/popup: sidebar popup does not dim scientific content");
        compare(popup.closePolicy, Popup.NoAutoClose, "I16/popup: outside and Escape are not dismissal routes");
        sameRect(rect(popup.contentItem), rect(item("workflow.home.sidebarHost")));
        sameRect(rect(main), before);
        keyClick(Qt.Key_Escape);
        compare(popup.visible, true, "I16/popup: Escape leaves the popup open");
        const point = main.mapToItem(window.contentItem, main.width / 2, main.height / 2);
        mouseClick(window.contentItem, point.x, point.y);
        compare(popup.visible, true, "I16/popup: genuine outside click leaves the popup open");
        compare(Session.project, null, "I16/popup: Home opening does not create a project");
        compare(window.appBarCentralTabs.currentIndex, 0, "I16/popup: Home opening does not navigate");
        verify(findChild(window, "assistant.close") === null, "I16/popup: no separate close control remains");
        Preferences.dialogShown = true;
        rendered();
        verify(findChild(window, "preferences.assistantShown") === null, "I16/popup: Preferences has no alternate chat opener");
        Preferences.dialogShown = false;
        capture("assistant-popup-home");
        toggle();
        compare(popup.visible, false, "I16/popup: same appbar button hides chat");
        sameRect(rect(main), before);
    }
    function test_workflow_same_sidebar_and_live_state_data() {
        return [
            {
                tag: "left-light",
                side: "Left",
                dark: false
            },
            {
                tag: "right-dark",
                side: "Right",
                dark: true
            }
        ];
    }
    function test_workflow_same_sidebar_and_live_state(data) {
        verify(Session.openProject(Probe.repoUrl("tests/fixtures/e04_t1/editable-project")), "I4/popup: real Session opens existing independent project fixture");
        Preferences.sideBarSide = data.side;
        EaStyle.Colors.theme = data.dark ? EaStyle.Colors.DarkTheme : EaStyle.Colors.LightTheme;
        window.appBarCentralTabs.currentIndex = 1;
        rendered();
        const main = item("workflow.project.mainContent");
        const host = item("workflow.project.sidebarHost");
        const manual = item("workflow.project.manualSidebar");
        const before = rect(main);
        const sidebarBefore = rect(host);
        const project = Session.project;
        const tab = findChild(manual, "sideBar.tab.extras");
        verify(tab !== null, "I16/popup: tab belongs to the active real manual sidebar");
        verify(tab.enabled, "I16/popup: preserved manual tab is genuinely available");
        mouseClick(tab);
        const tabIndex = manual.currentIndex;
        compare(tab.checked, true, "I16/popup: manual tab state is established by real input");
        const continued = findChild(manual, "sideBar.continue");
        verify(continued !== null, "I16/popup: covered action belongs to the active real manual sidebar");
        const covered = continued.mapToItem(window.contentItem, continued.width / 2, continued.height / 2);
        toggle();
        compare(popup.visible, true, "I16/popup: existing toolbar opens workflow overlay");
        compare(popup.assistant, assistant, "I16/popup: same real Session VM owns the single popup");
        sameRect(rect(popup.contentItem), sidebarBefore);
        sameRect(rect(main), before);
        compare(manual.visible, false, "I16/popup: covered manual subtree cannot receive pointer input");
        compare(manual.enabled, false, "I16/popup: covered manual subtree cannot receive keyboard input");
        continued.forceActiveFocus();
        verify(!continued.activeFocus, "I16/popup: covered real manual action refuses focus");
        mouseClick(window.contentItem, covered.x, covered.y);
        compare(window.appBarCentralTabs.currentIndex, 1, "I16/popup: covered Continue action cannot navigate");
        const composer = item("assistant.composer");
        composer.forceActiveFocus();
        composer.insert(0, "PbSO4 — unsent\ncell 5.43");
        composer.select(2, 8);
        const draft = composer.text;
        const start = composer.selectionStart;
        const end = composer.selectionEnd;
        const messages = assistant.messages;
        capture("assistant-popup-" + data.tag);
        toggle();
        compare(manual.visible, true, "I16/popup: hiding reveals the existing manual controls");
        compare(manual.enabled, true, "I16/popup: hiding restores manual interaction");
        compare(manual.currentIndex, tabIndex, "I16/popup: actual manual tab survives covering");
        sameRect(rect(main), before);
        toggle();
        compare(item("assistant.popup"), popup, "I16/popup: hide/show retains the same popup instance");
        compare(item("assistant.composer"), composer, "I16/popup: hide/show retains the actual draft editor");
        compare(composer.text, draft, "I16/popup: unsent multiline Unicode draft survives");
        compare(composer.selectionStart, start, "I16/popup: draft selection start survives");
        compare(composer.selectionEnd, end, "I16/popup: draft selection end survives");
        compare(assistant.messages, messages, "I16/popup: hiding does not replace the conversation model");
        compare(Session.project, project, "I16/popup: toggling does not replace the open project");
        sameRect(rect(main), before);
        toggle();
        composer.clear();
    }
}
