import QtQuick
import QtQuick.Controls
import QtTest
import edi.app
import EdiAcceptance 1.0
import "UiInteraction.js" as Ui

TestCase {
    id: test
    name: "BackgroundEstimate"
    when: windowShown
    property var appWindow
    Component {
        id: application
        Main {}
    }
    SignalSpy {
        id: buttonClicks
        signalName: "clicked"
    }
    function init() {
        Session.closeProject();
        appWindow = application.createObject(null);
        verify(appWindow !== null, "Estimation must use the production app window");
        verify(waitForRendering(appWindow.contentItem), "The estimator window must render");
    }
    function cleanup() {
        buttonClicks.target = null;
        Session.closeProject();
        appWindow.destroy();
        Probe.releaseScratchProjects();
    }
    function points() {
        return Probe.rows(Session.project.currentExperiment.background).map(row => ({
            id: row.id,
            position: row.position,
            intensity: row.intensity.value,
            free: row.intensity.free
        }));
    }
    function textItems(root) {
        const items = Probe.objectsWithProperty(root, "text").concat(Ui.itemsWithProperty(root, "text"));
        return items.filter((item, index) => items.indexOf(item) === index);
    }
    function buttonInventory(root) {
        return JSON.stringify(textItems(root).filter(item => typeof item.clicked === "function").map(item => ({
            objectName: item.objectName,
            text: String(item.text),
            enabled: item.enabled,
            visible: item.visible,
            inPane: Ui.inPane(item)
        })));
    }
    function namedButtons(root, names) {
        return textItems(root).filter(item =>
            names.indexOf(String(item.text).replace(/&/g, "").replace(/\u2026/g, "").trim()) >= 0
            && Ui.inPane(item) && item.enabled && typeof item.clicked === "function");
    }
    function activeDialogs(group) {
        const dialogs = Probe.visibleDialogs(appWindow).concat(Probe.visibleDialogs(group));
        return dialogs.filter((dialog, index) => dialogs.indexOf(dialog) === index);
    }
    function clickButton(button) {
        Ui.scrollIntoView(button);
        verify(waitForPolish(appWindow, 2000), "The Background action layout must settle before input");
        verify(waitForRendering(appWindow.contentItem), "The Background action must render before input");
        const point = Ui.clickPoint(button);
        verify(point !== null, "The Background action must have an exposed pointer target");
        let inputDelay = 0;
        for (let parent = button.parent; parent; parent = parent.parent)
            if (typeof parent.pressDelay === "number")
                inputDelay = Math.max(inputDelay, parent.pressDelay + 1);
        buttonClicks.target = button;
        buttonClicks.clear();
        mouseClick(button, point.x, point.y, undefined, undefined, inputDelay);
        compare(buttonClicks.count, 1, "Real pointer input must trigger exactly one Background button click");
        verify(waitForRendering(appWindow.contentItem), "The Background action must render its input result");
    }
    function test_estimate_undo_and_exact_reload_data() {
        return [{tag: "hrpt"}, {tag: "sim_si"}];
    }
    function test_estimate_undo_and_exact_reload(data) {
        verify(Session.openProject(Probe.repoUrl("tests/fixtures/background_estimate/projects/" + data.tag)),
               "The app must open the same frozen corpus input as Python");
        const original = JSON.stringify(points());
        const previousCell = Session.project.currentStructure.cell.lengthA.value;
        Session.project.currentStructure.cell.lengthA.value = previousCell + 0.125;
        const previousCanUndo = Session.project.canUndo;
        Ui.click(test, Probe, appWindow, "appBar.tab.experiment");
        Ui.expandGroup(test, Probe, appWindow, "group.background");
        const group = Ui.find(Ui.page(appWindow), "group.background", true);
        verify(group !== null, "The active Experiment page must expose group.background");
        const buttons = namedButtons(Ui.page(appWindow), ["Estimate"]);
        compare(buttons.length, 1,
                "Experiment Main must expose exactly one visible, enabled clickable control with text Estimate " +
                "(ignoring mnemonic &, ellipsis and surrounding whitespace); no objectName is required. Observed: " +
                buttonInventory(Ui.page(appWindow)));
        clickButton(buttons[0]);
        tryVerify(() => activeDialogs(group).length > 0 || JSON.stringify(points()) !== original,
                  2000, "Clicking the enabled Estimate control must open its options or replace the points");
        const dialogs = activeDialogs(group);
        if (dialogs.length) {
            compare(dialogs.length, 1, "The estimation options must belong to one active dialog");
            const apply = namedButtons(dialogs[0], ["Estimate", "OK", "Apply"]);
            compare(apply.length, 1,
                    "The active estimation dialog must expose one visible, enabled clickable control with text " +
                    "Estimate, OK or Apply (ignoring mnemonic &, ellipsis and surrounding whitespace). Observed: " +
                    buttonInventory(dialogs[0]));
            clickButton(apply[0]);
        }
        const estimated = points();
        verify(JSON.stringify(estimated) !== original, "Estimate must replace the existing background");
        const reference = JSON.parse(Probe.readFile("tests/fixtures/background_estimate/reference.json"));
        const expected = reference.cases[data.tag].methods.arpls.default.anchors;
        compare(estimated.length, expected.length, "The app must use the explicitly saved diffraction-lib tolerance 2 and drop profile");
        estimated.forEach((point, index) => {
            verify(Math.abs(point.position - expected[index][0]) <= 1e-9,
                   "App anchors must select the independent reference samples");
            verify(Math.abs(point.intensity - expected[index][1]) <= 1e-9 + 1e-6 * Math.abs(expected[index][1]),
                   "App heights must meet the independent arPLS tolerance");
            verify(!point.free, "The app must write fixed background points");
        });
        const destination = Probe.scratchProjectUrl();
        verify(Session.saveAs(destination), "Estimated points must save as an ordinary project");
        Session.project.undo();
        compare(JSON.stringify(points()), original, "One undo must restore the entire previous background");
        compare(Session.project.currentStructure.cell.lengthA.value, previousCell + 0.125,
                "The estimation undo must preserve the preceding independent edit");
        compare(Session.project.canUndo, previousCanUndo,
                "One estimation undo must restore the prior history availability without extra point operations");
        Session.closeProject();
        verify(Session.openProject(destination), "The estimated project must reload");
        compare(JSON.stringify(points()), JSON.stringify(estimated),
                "Saving and reloading must preserve every estimated point exactly");
        console.log("BACKGROUND_ESTIMATE_RECEIPT " + JSON.stringify({
            case: data.tag,
            points: points()
        }));
    }
}
