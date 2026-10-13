import QtQuick
import QtTest
import edi.app
import EdiAcceptance 1.0
import "UiInteraction.js" as Ui

TestCase {
    id: test
    name: "DatablockRename"
    when: windowShown
    property var appWindow
    Component {
        id: application
        Main {}
    }
    function initTestCase() {
        appWindow = application.createObject(null);
        verify(appWindow !== null, "The rename witness must use the production window");
        verify(waitForRendering(appWindow.contentItem), "The rename window must render before input");
    }
    function init() {
        Session.closeProject();
        AppState.reached = AppState.Page.Home;
        verify(Session.openProject(Probe.repoUrl("tests/fixtures/e04_t1/editable-project")), "The independent rename input must open");
    }
    function cleanupTestCase() {
        Session.closeProject();
        appWindow.destroy();
    }
    function test_rename_data() {
        return [
            {
                tag: "structure",
                kind: "structure",
                oldName: "lbco",
                next: "structure1",
                parameter: "atom_site.La.adp_iso"
            },
            {
                tag: "experiment",
                kind: "experiment",
                oldName: "hrpt",
                next: "experiment1",
                parameter: "instrument.calib_twotheta_offset"
            }
        ];
    }
    function block(kind) {
        return kind === "structure" ? Session.project.currentStructure : Session.project.currentExperiment;
    }
    function renameThroughCell(kind, next) {
        Ui.click(test, Probe, appWindow, "appBar.tab." + kind);
        Ui.expandGroup(test, Probe, appWindow, "group." + kind + "s");
        Ui.click(test, Probe, appWindow, kind + "s.name.0");
        keyClick(Qt.Key_A, Qt.ControlModifier);
        for (const character of next)
            keyClick(character.toUpperCase().charCodeAt(0));
        keyClick(Qt.Key_Return);
    }
    function texts() {
        let values = [Session.project.analysis.text.text];
        Probe.rows(Session.project.structures).forEach(row => values.push(row.structure.text.text));
        Probe.rows(Session.project.experiments).forEach(row => values.push(row.experiment.text.text));
        return values;
    }
    function test_rename(data) {
        const aliases = Session.project.analysis.aliases;
        aliases.append();
        verify(aliases.setText(0, "parameter", data.oldName + "." + data.parameter), "The owner’s alias must target the block before renaming");
        const sentinel = Session.project.currentStructure.cell.lengthA.value;
        Session.project.currentStructure.cell.lengthA.value = sentinel + .125;
        const before = texts();
        renameThroughCell(data.kind, data.next);
        compare(block(data.kind).name, data.next, "Committing the table cell must rename the selected block");
        compare(Probe.rows(Session.project.analysis.aliases)[0].parameter, data.next + "." + data.parameter, "The alias table must immediately show the new parameter identity");
        texts().forEach(text => verify(!(new RegExp("(^|[\\s\\\"'])" + data.oldName + "(?:\\.|[\\s\\\"']|$)", "m")).test(text), "No category text may retain the old datablock reference"));
        Session.project.undo();
        compare(block(data.kind).name, data.oldName, "One undo must restore the original datablock name");
        compare(JSON.stringify(texts()), JSON.stringify(before), "The same undo must restore every reference category");
        compare(Session.project.currentStructure.cell.lengthA.value, sentinel + .125, "Undo of rename must preserve the preceding independent edit");
        Session.project.undo();
        compare(Session.project.currentStructure.cell.lengthA.value, sentinel, "The next undo must reach the preceding edit without an extra rename-history step");
        renameThroughCell(data.kind, data.next);
        const saved = "build/test-tmp/rename-" + data.kind;
        verify(Session.saveAs(Probe.repoUrl(saved)), "Renaming with the owner's alias must save successfully");
        const analysis = Probe.readFile(saved + "/analysis/analysis.edi");
        const experiment = Probe.readFile(saved + "/experiments/" + (data.kind === "experiment" ? data.next : "hrpt") + ".edi");
        const structure = Probe.readFile(saved + "/structures/" + (data.kind === "structure" ? data.next : "lbco") + ".edi");
        [analysis, experiment, structure].forEach(text => verify(!(new RegExp("(^|[\\s\\\"'])" + data.oldName + "(?:\\.|[\\s\\\"']|$)", "m")).test(text), "Every saved .edi category must use the renamed identity"));
        verify(Session.openProject(Probe.repoUrl(saved)), "The renamed project must reopen without a model error");
        compare(block(data.kind).name, data.next, "Reopen must select the renamed block");
        verify(Session.save(), "The reopened renamed project must save cleanly in place");
        compare(Probe.readFile(saved + "/analysis/analysis.edi"), analysis, "Reload/save must preserve the rewritten alias bytes");
    }
}
