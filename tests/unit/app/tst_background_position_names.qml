import QtQuick
import QtTest
import edi.app
import EdiAcceptance 1.0
import "UiInteraction.js" as Ui

TestCase {
    id: test
    name: "BackgroundPositionNames"
    when: windowShown
    property var appWindow
    Component {
        id: application
        Main {}
    }
    function init() {
        Session.closeProject();
        appWindow = application.createObject(null);
        verify(appWindow !== null, "Position naming must use the production window");
        verify(waitForRendering(appWindow.contentItem), "The position naming window must render");
        verify(Session.openProject(Probe.repoUrl("tests/fixtures/loop_parameter_ids/name-by-position")), "The reference-bearing background witness must open");
    }
    function cleanup() {
        Session.closeProject();
        appWindow.destroy();
    }
    function ids() {
        return Probe.rows(Session.project.currentExperiment.background).map(row => row.id);
    }
    function test_rounding_references_and_one_undo() {
        const old = ["pA", "pB", "pC", "pD", "pE", "pF"];
        // Closed form: whole units first; refine only colliding groups. The first
        // pair needs two decimals, the second one, isolated points need none.
        const next = ["10.01", "10.02", "24.9", "25.1", "31", "72"];
        compare(JSON.stringify(ids()), JSON.stringify(old), "The independent points must keep their declared input ids");
        const sentinel = Session.project.currentStructure.cell.lengthA.value;
        Session.project.currentStructure.cell.lengthA.value = sentinel + .125;
        const analysis = Session.project.analysis.text.text;
        const experiment = Session.project.currentExperiment.text.text;
        Ui.click(test, Probe, appWindow, "appBar.tab.experiment");
        Ui.expandGroup(test, Probe, appWindow, "group.background");
        const buttons = Probe.objectsWithProperty(appWindow, "text").filter(item => Ui.exposed(item) && item.text === "Name points by position");
        compare(buttons.length, 1, "The background table must expose one actual position-naming button");
        mouseClick(buttons[0]);
        compare(JSON.stringify(ids()), JSON.stringify(next), "Only colliding points may gain extra decimal places");
        let renamed = analysis;
        old.forEach((id, i) => {
            renamed = renamed.split(".background." + id + ".").join(".background." + next[i] + ".").split(".background[" + id + "]").join(".background[" + next[i] + "]");
        });
        compare(Session.project.analysis.text.text, renamed, "Aliases, constraints, fit start values and both correlation endpoints must follow; coefficient, uncertainty and filename bytes remain intact");
        verify(Session.saveAs(Probe.repoUrl("build/test-tmp/background-position-names")), "Position naming must save with all references still valid");
        compare(Probe.readFile("build/test-tmp/background-position-names/analysis/analysis.edi"), renamed, "The saved analysis must retain the complete rewritten reference state");
        Session.project.undo();
        compare(JSON.stringify(ids()), JSON.stringify(old), "One undo must restore all point ids together");
        compare(Session.project.analysis.text.text, analysis, "The same undo must restore every reference");
        compare(Session.project.currentExperiment.text.text, experiment, "The same undo must preserve every original point value and position");
        compare(Session.project.currentStructure.cell.lengthA.value, sentinel + .125, "The rename undo must retain the preceding independent edit");
        Session.project.undo();
        compare(Session.project.currentStructure.cell.lengthA.value, sentinel, "The next undo must reach the preceding edit without extra point history");
    }
}
