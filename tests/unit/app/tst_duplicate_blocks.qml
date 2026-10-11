import QtQuick
import QtTest
import edi.app
import EdiAcceptance 1.0
import "UiInteraction.js" as Ui

TestCase {
    id: test
    name: "DuplicateBlocks"
    when: windowShown
    property var appWindow
    Component {
        id: application
        Main {}
    }
    function initTestCase() {
        appWindow = application.createObject(null);
        verify(appWindow !== null, "The duplicate-block witness requires the production window");
        verify(waitForRendering(appWindow.contentItem), "The duplicate-block window must render before input");
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
        verify(Session.openProject(Probe.repoUrl(path)), "The independent duplicate input must open");
    }
    function categories(text) {
        return text.slice(text.indexOf("\n") + 1);
    }
    function current(kind) {
        return kind === "structure" ? Session.project.currentStructure : Session.project.currentExperiment;
    }
    function count(kind) {
        return kind === "structure" ? Session.project.structures.count : Session.project.experiments.count;
    }
    function chooseSource(kind) {
        if (kind === "structure")
            Session.project.currentStructureIndex = 0;
        else
            Session.project.currentExperimentIndex = 0;
    }
    function clickDuplicate(kind) {
        clickTab(kind);
        Ui.expandGroup(test, Probe, appWindow, "group." + kind + "s");
        Ui.click(test, Probe, appWindow, kind + "s.duplicate");
    }
    function clickTab(kind) {
        Ui.click(test, Probe, appWindow, "appBar.tab." + kind);
    }
    function test_whole_duplicate_data() {
        return [
            {
                tag: "structure",
                kind: "structure",
                background: "line-segment"
            },
            {
                tag: "line",
                kind: "experiment",
                background: "line-segment"
            },
            {
                tag: "polynomial",
                kind: "experiment",
                background: "polynomial"
            },
            {
                tag: "chebyshev",
                kind: "experiment",
                background: "chebyshev"
            }
        ];
    }
    function test_whole_duplicate(data) {
        const kind = data.kind;
        open("tests/fixtures/e04_t1/editable-project");
        if (kind === "structure")
            verify(Session.project.currentStructure.atomSites.setText(0, "adpType", "Uani"), "The structure witness must include an anisotropic tensor category");
        if (kind === "experiment" && data.background !== "line-segment") {
            Session.project.currentExperiment.backgroundType = data.background;
            Session.project.currentExperiment.backgroundTerms.append();
            Probe.rows(Session.project.currentExperiment.backgroundTerms)[0].coef.value = 13.125;
        }
        const source = current(kind);
        const name = source.name;
        const before = source.text.text;
        const experimentBefore = Session.project.currentExperiment.text.text;
        const initial = count(kind);
        clickDuplicate(kind);
        compare(count(kind), initial + 1, "Duplicate must add exactly one whole block");
        const copy = current(kind);
        compare(copy.name, name + "_copy", "The first duplicate must become current under the source-name copy suffix");
        verify(copy !== source, "The duplicate must own an independent view and model object");
        compare(categories(copy.text.text), categories(before), "Every saved category of the duplicate must equal its source before edits");
        if (kind === "structure") {
            compare(Session.project.currentExperiment.text.text, experimentBefore, "A structure copy must add no experiment link or texture row");
            verify(copy.cell.lengthA !== source.cell.lengthA, "The duplicate cell must have independent parameter objects");
            verify(Probe.rows(copy.atomSites)[0].occupancy !== Probe.rows(source.atomSites)[0].occupancy, "The duplicate atom must have independent parameter objects");
            copy.cell.lengthA.value += .125;
            Probe.rows(copy.atomSites)[0].occupancy.value = .625;
        } else {
            copy.cutoffFwhm += 1;
            if (data.background === "line-segment")
                Probe.rows(copy.background)[0].intensity.value += 17.125;
            else
                Probe.rows(copy.backgroundTerms)[0].coef.value += 17.125;
        }
        compare(source.text.text, before, "Editing the duplicate must leave every original category unchanged");
        verify(current(kind).text.text !== before, "The independent copy must record its edited categories");
        Session.project.undo();
        Session.project.undo();
        Session.project.undo();
        compare(count(kind), initial, "Undoing the copy’s edits and creation must remove exactly that duplicate");
        compare(current(kind).text.text, before, "Undo of duplication must preserve the original block");
        clickDuplicate(kind);
        chooseSource(kind);
        clickDuplicate(kind);
        compare(current(kind).name, name + "_copy2", "Duplicating the original again must select copy2 without overwriting copy");
        const saved = "build/test-tmp/duplicate-" + data.tag;
        verify(Session.saveAs(Probe.repoUrl(saved)), "Save must write every duplicated block");
        const file = saved + "/" + kind + "s/" + name + "_copy2.edi";
        const bytes = Probe.readFile(file);
        verify(bytes.startsWith("data_" + name + "_copy2"), "Save must write the new duplicate’s own .edi file");
        open(saved);
        compare(count(kind), initial + 2, "Reload must retain both saved duplicates");
        const rows = Probe.rows(kind === "structure" ? Session.project.structures : Session.project.experiments);
        verify(rows.some(row => row.name === name + "_copy2"), "Reload must preserve the numbered duplicate name");
        verify(Session.save(), "Reloaded duplicates must save in place");
        compare(Probe.readFile(file), bytes, "Saving after reload must preserve every duplicate category byte");
    }
    function test_scan_disables_experiment_duplicate() {
        open("tests/fixtures/correlations/scan-sequential");
        clickTab("experiment");
        Ui.expandGroup(test, Probe, appWindow, "group.experiments");
        const action = Ui.control(Probe, appWindow, "experiments.duplicate");
        verify(action !== null && !action.enabled, "A scan project must show its experiment Duplicate action disabled");
        const before = Session.project.experiments.count;
        verify(!Session.project.duplicateExperiment(), "Direct invocation must also refuse a scan experiment duplicate");
        compare(Session.project.experiments.count, before, "A refused scan duplicate must leave its template inventory unchanged");
    }
}
