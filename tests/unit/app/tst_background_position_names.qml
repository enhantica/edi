import QtQuick
import QtTest
import edi.app
import EdiAcceptance 1.0
import ReportAcceptance 1.0
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
        const input = SettingsProof.copyProject(Probe.repoUrl("tests/fixtures/loop_parameter_ids/name-by-position"));
        const analysis = SettingsProof.text(input, "analysis/analysis.edi");
        const current = analysis.replace(/bank.background\[pA\]/g, "bank.background.pA")
                                .replace(/bank.background\[pB\]/g, "bank.background.pB");
        verify(SettingsProof.write(input, "analysis/analysis.edi", current),
               "The retained historical point witness must adapt only its two obsolete fit selector spellings");
        verify(Session.openProject(input), "The reference-bearing background witness must open with current fit selectors");
    }
    function cleanup() {
        Session.closeProject();
        appWindow.destroy();
        Probe.releaseScratchProjects();
    }
    function ids() {
        return Probe.rows(Session.project.currentExperiment.background).map(row => row.id);
    }
    function test_rounding_references_and_one_undo() {
        // Id actions are Manual-only; choose Manual before the rename/Undo witness.
        Session.project.currentExperiment.backgroundEstimateMode = "manual";
        const old = ["pA", "pB", "pC", "pD", "pE", "pF"];
        // Closed form: whole units first; refine only colliding groups. The first
        // pair needs two decimals, the second one, isolated points need none.
        const next = ["10.01", "10.02", "24.9", "25.1", "31", "72"];
        compare(JSON.stringify(ids()), JSON.stringify(old), "The independent points must keep their declared input ids");
        // A batch free/fixed action records its own typed Undo; a direct value write does not.
        const sentinel = Session.project.currentStructure.cell.lengthA;
        const oldFree = sentinel.free;
        verify(Session.project.setParametersFree([sentinel], !oldFree),
               "The preceding independent free/fixed batch must succeed through the recorded action API");
        compare(sentinel.free, !oldFree, "The recorded preceding action must actually change its target");
        verify(Session.project.canUndo, "The recorded free/fixed action must be offered by Undo");
        const analysis = Session.project.analysis.text.text;
        const experiment = Session.project.currentExperiment.text.text;
        Ui.click(test, Probe, appWindow, "appBar.tab.experiment");
        Ui.expandGroup(test, Probe, appWindow, "group.background");
        // Loader delegates follow the active page's visual tree, not window QObject ownership.
        const action = Ui.find(Ui.page(appWindow), "background.namePoints", true);
        verify(action !== null && action.enabled && typeof action.clicked === "function",
               "Main must expose one enabled naming action with objectName background.namePoints and clicked role");
        const buttons = [action];
        compare(String(buttons[0].text).replace(/&|\u2026/g, "").trim(), "Id from position",
                "The stable point-id action must use the approved singular Id from position label");
        Ui.scrollIntoView(buttons[0]);
        const point = Ui.clickPoint(buttons[0]);
        verify(point !== null, "The stable position-id button must expose a real pointer target");
        mouseClick(buttons[0], point.x, point.y);
        compare(JSON.stringify(ids()), JSON.stringify(next), "Only colliding points may gain extra decimal places");
        let renamed = analysis;
        old.forEach((id, i) => {
            renamed = renamed.replace(new RegExp("\\.background\\." + id + "(?=\\.|\\s|$)", "g"),
                                      ".background." + next[i]).split(".background[" + id + "]").join(".background[" + next[i] + "]");
        });
        compare(Session.project.analysis.text.text, renamed, "Aliases, constraints, fit start values and both correlation endpoints must follow; coefficient, uncertainty and filename bytes remain intact");
        verify(Session.saveAs(Probe.repoUrl("build/test-tmp/background-position-names")), "Position naming must save with all references still valid");
        compare(Probe.readFile("build/test-tmp/background-position-names/analysis/analysis.edi"), renamed, "The saved analysis must retain the complete rewritten reference state");
        Session.project.undo();
        compare(JSON.stringify(ids()), JSON.stringify(old), "One undo must restore all point ids together");
        compare(Session.project.analysis.text.text, analysis, "The same undo must restore every reference");
        compare(Session.project.currentExperiment.text.text, experiment, "The same undo must preserve every original point value and position");
        compare(sentinel.free, !oldFree, "The rename undo must retain the preceding recorded free/fixed action");
        verify(Session.project.canUndo, "The preceding recorded free/fixed action must remain offered by Undo after the naming action");
        Session.project.undo();
        compare(sentinel.free, oldFree, "The next undo must reach the preceding recorded free/fixed action without extra point history");
        console.log("BACKGROUND_NAMING_PRIOR_ACTION recorded=setParametersFree restored=true");
    }
}
