import QtQuick
import QtTest
import edi.app
import "../../unit/app/UiInteraction.js" as Ui

TestCase {
    name: "AssistantDeviceEntry"
    when: windowShown
    property var window
    property bool oldShown
    property real oldWidth
    property string oldSide
    Component {
        id: application
        Main {}
    }
    function initTestCase() {
        oldShown = Preferences.assistantShown;
        oldWidth = Preferences.assistantWidth;
        oldSide = Preferences.sideBarSide;
        window = application.createObject(null);
        verify(window !== null, "I16/device: native control instantiates the real production Main");
        verify(waitForRendering(window.contentItem), "I16/device: native Main really renders");
    }
    function cleanupTestCase() {
        Preferences.assistantShown = oldShown;
        Preferences.assistantWidth = oldWidth;
        Preferences.sideBarSide = oldSide;
        window.destroy();
    }
    function test_native_metadata_is_eligible_but_disconnected() {
        compare(ApplicationInfo.assistantAvailable, true, "I16/device: native availability needs no browser classification");
        compare(ApplicationInfo.assistantUnavailableReason, "", "I16/device: eligible native entry has no device refusal");
        compare(Session.assistant.connected, false, "I12/device: eligible native control does not fabricate provider connection");
        const toggle = Ui.find(window.contentItem, "assistant.toggle");
        verify(toggle !== null && toggle.visible && toggle.enabled, "I16/device: native AI-open remains visible and usable");
    }
    function test_native_entries_preferences_and_hidden_focus() {
        Preferences.assistantWidth = 347;
        Preferences.sideBarSide = "Left";
        Preferences.assistantShown = true;
        const panel = Ui.find(window.contentItem, "assistant.panel");
        const toggle = Ui.find(window.contentItem, "assistant.toggle");
        verify(panel !== null && toggle !== null, "I16/device: controls belong to the actual native shell");
        tryCompare(panel, "visible", true, 500, "I16/device: restored true preference still opens on native");
        mouseClick(toggle);
        tryCompare(panel, "visible", false, 500, "I16/device: real toolbar still hides the native panel");
        keyClick(Qt.Key_A, Qt.ControlModifier | Qt.ShiftModifier);
        tryCompare(panel, "visible", true, 500, "I16/device: native keyboard opening remains available");
        const composer = Ui.find(window.contentItem, "assistant.composer");
        verify(composer !== null, "I16/device: focus is observed on the real composer");
        tryVerify(() => composer.activeFocus, 500, "I16/device: native keyboard opening focuses chat");
        Preferences.dialogShown = true;
        const checkbox = Ui.find(window.contentItem, "preferences.assistantShown");
        verify(checkbox !== null && checkbox.enabled && checkbox.checked, "I16/device: native preference keeps its actual shown value");
        Preferences.dialogShown = false;
        Preferences.assistantShown = false;
        window.contentItem.forceActiveFocus();
        panel.focusComposer();
        verify(!composer.activeFocus, "I16/device: hidden assistant refuses direct focus without changing eligibility");
        Preferences.assistantShown = true;
        compare(Preferences.assistantWidth, 347, "I16/device: entry policy preserves width");
        compare(Preferences.sideBarSide, "Left", "I16/device: entry policy preserves workflow side");
    }
}
