import QtQuick
import QtQuick.Controls
import QtTest
import edi.app
import EdiAcceptance 1.0
import ReportAcceptance 1.0
import "UiInteraction.js" as Ui

TestCase {
    id: test
    name: "BackgroundTermIds"
    when: windowShown
    property var appWindow
    property var backgroundPanel
    // Use the actual Main-tab component in a bounded Qt window; unrelated
    // QtGraphs rendering must not determine a naming/Undo actor's lifetime.
    Component { id: application; ApplicationWindow { width: 900; height: 800; visible: true } }
    Component { id: backgroundComponent; BackgroundGroup { width: 650; x: 20; y: 20 } }
    function init() {
        Session.closeProject();
        appWindow = application.createObject(null);
        verify(appWindow !== null, "Term id actions must use the production app window");
        verify(waitForRendering(appWindow.contentItem), "The term id action window must render");
    }
    function cleanup() {
        if (backgroundPanel) backgroundPanel.destroy();backgroundPanel = null;
        Session.closeProject();
        appWindow.close();
        appWindow.destroy();
        Probe.releaseScratchProjects();
    }
    function rows() { return Probe.rows(Session.project.currentExperiment.backgroundTerms); }
    function ids() { return rows().map(row => row.id); }
    function values() { return rows().map(row => [row.order, row.coef.value, row.coef.free]); }
    function source(kind) { return Probe.repoUrl("tests/fixtures/background_estimate/projects/ids-" + kind + "-explicit"); }
    function action(kind) {
        verify(Session.openProject(source(kind)), "The app must load explicit ids on sparse " + kind + " terms: " + Session.lastError);
        tryVerify(() => !Session.project.calculating, 1000, "The initial series calculation must complete before renaming term ids");
        // Id actions are Manual-only; choose Manual before the rename/Undo witness.
        Session.project.currentExperiment.backgroundEstimateMode = "manual";
        backgroundPanel = backgroundComponent.createObject(appWindow.contentItem,
            {experiment: Session.project.currentExperiment});
        verify(backgroundPanel !== null && waitForPolish(backgroundPanel),
               "The series naming actor must render the actual Main BackgroundGroup");
        let action = null;
        tryVerify(() => {
            action = Ui.find(backgroundPanel, "background.nameTerms", true);
            return action !== null;
        }, 500, "The actual Main component must instantiate background.nameTerms");
        verify(action !== null && action.enabled && typeof action.clicked === "function",
               "Main must expose one enabled naming action with objectName background.nameTerms and clicked role");
        const buttons = [action];
        compare(String(buttons[0].text).replace(/&|\u2026/g, "").trim(), "Id from order",
                "The stable term-id action must use the approved singular Id from order label");
        const old = ["high", "floor", "bend"], next = ["5", "0", "3"];
        compare(JSON.stringify(ids()), JSON.stringify(old), "Explicit ids must be observable on the app's public backgroundTerms rows");
        const originalValues = JSON.stringify(values());
        const originalAnalysis = Session.project.analysis.text.text;
        // A batch free/fixed action records its own typed Undo; a direct value write does not.
        const sentinel = Session.project.currentStructure.cell.lengthA;
        const oldFree = sentinel.free;
        verify(Session.project.setParametersFree([sentinel], !oldFree),
               "The preceding independent free/fixed batch must succeed through the recorded action API");
        compare(sentinel.free, !oldFree, "The recorded preceding action must actually change its target");
        verify(Session.project.canUndo, "The recorded free/fixed action must be offered by Undo");
        Ui.scrollIntoView(buttons[0]);
        const point = Ui.clickPoint(buttons[0]);
        verify(point !== null, "The stable term-id button must expose a real pointer target");
        mouseClick(buttons[0], point.x, point.y);
        compare(JSON.stringify(ids()), JSON.stringify(next), "Id from order must use decimal powers 5,0,3, preserving sparse file row order");
        compare(JSON.stringify(values()), originalValues, "Changing ids from order must preserve every power, coefficient and free flag");
        let expected = originalAnalysis;
        old.forEach((identity, index) => expected = expected.split("bank.background." + identity).join("bank.background." + next[index]));
        compare(Session.project.analysis.text.text, expected,
                "Term id renaming must follow aliases, fit-start keys and both correlation endpoints, preserving constraint text and unrelated filename bytes");
        const destination = Probe.scratchProjectUrl();
        verify(Session.saveAs(destination), "Required ids from order must save through the actual app");
        compare(SettingsProof.text(destination, "analysis/analysis.edi"), expected,
                "Saving renamed terms must retain every rewritten reference exactly");
        Session.project.undo();
        compare(JSON.stringify(ids()), JSON.stringify(old), "One undo must restore all explicit term ids together");
        compare(Session.project.analysis.text.text, originalAnalysis, "One undo must restore every prior term reference");
        compare(sentinel.free, !oldFree,
                "The term id undo must preserve the preceding recorded free/fixed action");
        verify(Session.project.canUndo, "Saving a term rename must keep the preceding recorded free/fixed action offered by Undo");
        Session.project.undo();
        compare(sentinel.free, oldFree,
                "The next Undo after a saved term rename must restore the preceding recorded free/fixed action");
        console.log("BACKGROUND_NAMING_PRIOR_ACTION recorded=setParametersFree restored=true");
        Session.closeProject();
        verify(Session.openProject(destination), "Saved order-derived explicit ids must reload through the app");
        tryVerify(() => !Session.project.calculating, 1000,
                  "The actual saved-id reload must finish its worker before the bounded actor exits");
        compare(JSON.stringify(ids()), JSON.stringify(next), "Reloading must retain every saved term id exactly");
        compare(JSON.stringify(values()), originalValues, "Reloading renamed ids must retain sparse powers and physical values exactly");
        console.log("BACKGROUND_TERM_IDS " + JSON.stringify({type: kind, ids: ids(), action: "background.nameTerms"}));
    }
    function missing(kind) {
        const input = SettingsProof.copyProject(source(kind));
        let text = SettingsProof.text(input, "experiments/bank.edi").replace("_background.id\n", "");
        ["high", "floor", "bend"].forEach(identity => text = text.replace(new RegExp("^" + identity + " ", "m"), ""));
        verify(SettingsProof.write(input, "experiments/bank.edi", text), "The negative control must omit only the required term id column");
        verify(SettingsProof.write(input, "analysis/analysis.edi", "_edi.schema_version 3\n_fitting_mode.type single\n"),
               "The missing-id control must isolate required ids from unrelated reference resolution");
        verify(!Session.openProject(input), "The app must refuse missing term ids without an ordinal fallback");
        const message = String(Session.lastError).toLowerCase();
        verify(message.indexOf("background") >= 0 && message.indexOf("id") >= 0 && /missing|required|must|need/.test(message),
               "The missing-id app refusal must name the required background id field: " + message);
        console.log("BACKGROUND_TERM_IDS_REFUSED " + kind);
    }
    function test_order_action_polynomial() { action("polynomial"); }
    function test_order_action_chebyshev() { action("chebyshev"); }
    function test_missing_polynomial() { missing("polynomial"); }
    function test_missing_chebyshev() { missing("chebyshev"); }
}
