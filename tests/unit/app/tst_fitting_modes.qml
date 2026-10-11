import QtQuick
import QtTest
import edi.app
import EdiAcceptance 1.0
import "UiInteraction.js" as Ui

TestCase {
    id: test
    name: "ApplicableFittingModes"
    when: windowShown
    property var appWindow
    Component {
        id: application
        Main {}
    }
    function initTestCase() {
        appWindow = application.createObject(null);
        verify(appWindow !== null, "The fitting-mode witness requires the production window");
        verify(waitForRendering(appWindow.contentItem), "The fitting-mode window must render before input");
    }
    function init() {
        Session.closeProject();
        AppState.reached = AppState.Page.Home;
    }
    function cleanupTestCase() {
        Session.closeProject();
        appWindow.destroy();
    }
    function open(path) {
        verify(Session.openProject(Probe.repoUrl(path)), "The independent mode witness must open");
        Ui.click(test, Probe, appWindow, "appBar.tab.analysis");
        Ui.click(test, Probe, appWindow, "sideBar.tab.extras");
    }
    function options(expected) {
        const actual = Probe.rows(Session.project.analysis.fittingModeOptions).map(row => [row.token, row.label]);
        compare(JSON.stringify(actual), JSON.stringify(expected), "The selector must offer exactly the applicable tokens with the owner’s descriptive labels");
        Ui.expandGroup(test, Probe, appWindow, "group.fitting_mode");
        const selector = Ui.control(Probe, appWindow, "fittingMode.type");
        verify(selector !== null, "The applicable-mode selector must be exposed in its group");
        compare(selector.enabled, expected.length > 1, "A single applicable mode must be shown disabled");
        if (expected.length === 1) {
            mouseMove(selector.parent, selector.parent.width / 2, selector.parent.height / 2);
            tryVerify(() => Probe.objectsWithProperty(selector.parent, "text").some(item => item.visible && /one experiment|several experiments/.test(item.text)), 3000, "Hovering the disabled mode row must show its explanatory tooltip");
        }
    }
    function jointCategory(expected) {
        const present = Probe.rows(Session.project.analysis.categories).some(row => row.categoryId === "joint_fit");
        compare(present, expected, "The Joint-fit weights group must exist only while joint mode is active");
    }
    function test_single_to_joint_and_undo() {
        open("tests/fixtures/e04_t1/editable-project");
        options([["single", "Single experiment"]]);
        jointCategory(false);
        verify(Session.project.duplicateExperiment(), "The mode witness must grow to several experiments through a real project edit");
        options([["joint", "Joint: all experiments at once"]]);
        Session.project.analysis.fittingMode = "joint";
        jointCategory(true);
        Session.project.undo();
        tryCompare(Session.project.analysis, "fittingMode", "single", 2000, "Undoing the added experiment must restore the applicable single mode");
        options([["single", "Single experiment"]]);
        jointCategory(false);
    }
    function test_scan_data() {
        return [
            {
                tag: "sequential",
                mode: "sequential"
            },
            {
                tag: "independent",
                mode: "independent"
            }
        ];
    }
    function test_scan(data) {
        open("tests/fixtures/correlations/scan-" + data.mode);
        options([["sequential", "Sequential: each from the previous"], ["independent", "Independent: each from the same start"]]);
        jointCategory(false);
        const other = data.mode === "sequential" ? "independent" : "sequential";
        Session.project.analysis.fittingMode = other;
        compare(Session.project.analysis.fittingMode, other, "Selecting the other scan mode must preserve its stored token");
        jointCategory(false);
    }
}
