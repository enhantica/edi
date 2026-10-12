import QtQuick
import QtQuick.Controls
import QtTest
import edi.app
import EdiAcceptance 1.0
import "UiInteraction.js" as Ui

TestCase {
    id: test
    name: "ResetAndRequired"
    when: windowShown
    property var appWindow
    Component {
        id: application
        Main {}
    }
    function init() {
        Session.closeProject();
        appWindow = application.createObject(null);
        verify(appWindow !== null, "Owner-action actors require the production window");
        verify(waitForRendering(appWindow.contentItem), "The owner-action window must render before input");
    }
    function cleanup() {
        Session.closeProject();
        appWindow.destroy();
    }
    function test_reset_lands_on_project() {
        verify(Session.openProject(Probe.repoUrl("tests/fixtures/e04_t1/editable-project")), "The reset actor must first open a real project");
        Ui.click(test, Probe, appWindow, "appBar.tab.analysis");
        Ui.click(test, Probe, appWindow, "appBar.button.reset");
        verify(!Session.hasProject, "The reset toolbar action must close its project");
        const tab = Ui.control(Probe, appWindow, "appBar.tab.project");
        verify(tab !== null && tab.checked, "The reset toolbar action must land on the Project page");
        compare(AppState.reached, AppState.Page.Project, "Reset must keep Project reached so its empty workflow remains usable");
    }
    function test_required_rule_click() {
        verify(Session.openProject(Probe.repoUrl("tests/fixtures/correlations/scan-sequential")), "The required-toggle actor must open independently declared scan rules");
        Ui.click(test, Probe, appWindow, "appBar.tab.analysis");
        Ui.click(test, Probe, appWindow, "sideBar.tab.extras");
        Ui.expandGroup(test, Probe, appWindow, "group.sequential_fit_extract");
        const table = Ui.control(Probe, appWindow, "sequentialExtract.list");
        verify(table !== null, "The scan extraction rule table must be reachable in Extras");
        const rows = Probe.rows(Session.project.analysis.sequentialExtract);
        verify(rows.length > 0, "The scan witness must carry an actual extraction rule");
        const cell = Ui.control(Probe, appWindow, "sequentialExtract.required.0");
        verify(cell !== null && Ui.exposed(cell), "The required icon cell must be rendered in its own rule row");
        const before = rows[0].required;
        if (cell.fontIcon !== undefined) {
            verify(/fail|match/i.test(cell.ToolTip.text), "The editable required icon must explain a missing match");
            mouseClick(cell);
            compare(Probe.rows(Session.project.analysis.sequentialExtract)[0].required, !before, "An editable icon must toggle its own required rule");
            compare(cell.fontIcon, before ? "toggle-off" : "toggle-on", "The editable icon must follow the changed state");
            Session.project.undo();
            compare(Probe.rows(Session.project.analysis.sequentialExtract)[0].required, before, "Undo must restore the editable rule state");
        } else {
            compare(cell.icon, before ? "toggle-on" : "toggle-off", "A read-only rule must display its actual required state");
            verify(/fail|match/i.test(cell.toolTip), "The read-only required icon must explain the no-match rule");
        }
    }
}
