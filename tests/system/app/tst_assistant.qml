import QtQuick
import QtTest
import edi.app
import EasyApplication.Gui.Style as EaStyle
import EdiAcceptance 1.0
import "../../unit/app/UiInteraction.js" as Ui

TestCase {
    id: test
    name: "AssistantContract"
    when: windowShown
    property var window
    property var initialAssistant
    Component {
        id: application
        Main {}
    }

    function initTestCase() {
        window = application.createObject(null);
        verify(window !== null, "I16: the production Main window must instantiate");
        verify(waitForRendering(window.contentItem), "I16: actual QML content must render");
    }
    function cleanupTestCase() {
        Session.closeProject();
        window.destroy();
    }
    function init() {
        verify(Session.assistant !== undefined && Session.assistant !== null, "I16: Session owns an assistant even without an open project");
        verify(typeof Preferences.assistantShown === "boolean", "I16: assistant visibility is a real persistent preference");
        verify(typeof Preferences.assistantWidth === "number", "I16: assistant width is a real persistent preference");
        initialAssistant = Session.assistant;
        Preferences.assistantShown = true;
        Preferences.assistantWidth = 347;
    }
    function panel() {
        const item = Ui.find(window.contentItem, "assistant.panel");
        verify(item !== null, "I16: the actual shell renders the named assistant panel");
        return item;
    }
    function test_app_lifetime_survives_project_and_page_changes() {
        Session.closeProject();
        compare(Session.assistant, initialAssistant, "I16: closing a project retains the assistant VM");
        verify(Session.openProject(Probe.repoUrl("tests/fixtures/e04_t1/editable-project")), "I4/I16: the existing Session opens the independent project fixture");
        window.appBarCentralTabs.currentIndex = 1;
        verify(waitForRendering(window.contentItem), "I16: the real workflow page settles");
        compare(Session.assistant, initialAssistant, "I16: loaded pages share one assistant");
        Session.closeProject();
        compare(Session.assistant, initialAssistant, "I16: session replacement does not destroy history owner");
    }
    function test_both_themes_and_live_opposite_placement_data() {
        return [
            {
                tag: "light",
                dark: false
            },
            {
                tag: "dark",
                dark: true
            }
        ];
    }
    function test_both_themes_and_live_opposite_placement(data) {
        const oldTheme = EaStyle.Colors.theme;
        EaStyle.Colors.theme = data.dark ? EaStyle.Colors.DarkTheme : EaStyle.Colors.LightTheme;
        for (const side of ["Left", "Right"]) {
            Preferences.sideBarSide = side;
            const item = panel();
            tryCompare(item, "onLeft", side === "Right", 500, "I16: changing workflow placement moves the assistant live to the opposite side");
            compare(item.assistant, initialAssistant, "I16: placement retains the same real VM");
            verify(item.width > 0 && item.height > 0, "I16: both theme/side combinations render usable geometry");
        }
        EaStyle.Colors.theme = oldTheme;
    }
    function test_hiding_retains_conversation_owner_and_width() {
        const shown = panel();
        compare(shown.panelWidth, 347, "I16: the panel uses the nontrivial preference width");
        const messages = initialAssistant.messages;
        Preferences.assistantShown = false;
        compare(Session.assistant, initialAssistant, "I16: hiding cannot destroy conversation/job state");
        compare(initialAssistant.messages, messages, "I16: hiding retains the public message model");
        Preferences.assistantShown = true;
        const restored = panel();
        compare(restored.assistant, initialAssistant, "I16: showing restores the same controller presentation");
        compare(restored.panelWidth, 347, "I16: hiding/showing retains the selected panel width");
    }
    function test_keyboard_toggle_focus_and_multiline_composer() {
        Preferences.assistantShown = false;
        window.requestActivate();
        keyClick(Qt.Key_A, Qt.ControlModifier | Qt.ShiftModifier);
        tryCompare(Preferences, "assistantShown", true, 500, "I16: the advertised keyboard shortcut opens chat");
        const composer = Ui.find(window.contentItem, "assistant.composer");
        verify(composer !== null, "I16: chat exposes the actual editable composer");
        tryVerify(() => composer.activeFocus, 500, "I16: keyboard opening focuses the composer");
        keyClicks("PbSO4");
        keyClick(Qt.Key_Return, Qt.ShiftModifier);
        keyClicks("units");
        verify(String(composer.text).includes("\n"), "I16: Shift+Enter inserts a line without sending");
        verify(String(composer.text).includes("units"), "I16: multiline keyboard editing remains usable");
    }
    function test_narrow_panel_keeps_controls_accessible() {
        const oldWidth = window.width;
        const oldMinimum = window.minimumWidth;
        window.minimumWidth = 400;
        window.width = 640;
        const item = panel();
        tryCompare(item, "overlayMode", true, 500, "I16: narrow windows use a chat overlay drawer");
        verify(item.width <= window.width, "I16: narrow chat cannot exceed the logical viewport");
        for (const name of ["assistant.composer", "assistant.connection", "assistant.model"]) {
            const control = Ui.find(window.contentItem, name);
            verify(control !== null && Ui.exposed(control), "I16: narrow chat retains reachable control " + name);
        }
        window.width = oldWidth;
        window.minimumWidth = oldMinimum;
    }
}
