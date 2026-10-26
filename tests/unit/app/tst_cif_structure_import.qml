import QtQuick
import QtQuick.Controls
import QtTest
import edi.app
import EdiAcceptance 1.0
import "UiInteraction.js" as Ui
import "E04Review.js" as Review

TestCase {
    id: test
    name: "CifStructureImport"
    when: windowShown
    property var appWindow
    Component { id: application; Main {} }
    function init() {
        appWindow = application.createObject(null);
        verify(appWindow !== null, "Display checks use the production application window");
        Session.openProject(Probe.repoUrl("tests/fixtures/loop_parameter_ids/line-segment"));
        verify(Session.hasProject, "The independent P1 display project opens in the app");
        verify(waitForRendering(appWindow.contentItem), "The production window renders before inspection");
    }
    function cleanup() {
        Session.closeProject();
        appWindow.destroy();
    }
    function test_load_published_cif_data() {
        return [
            {tag: "cod", file: "published_cod_1000236.cif", cell: 10.257, atoms: 6, group: 199},
            {tag: "owner", file: "owner_tbti.cif", cell: 10.13, atoms: 4, group: 227}
        ];
    }
    function test_load_published_cif(data) {
        const before = Probe.rows(Session.project.structures).length;
        verify(Session.project.loadStructure(Probe.repoUrl(
                   "tests/fixtures/dictionary_display/" + data.file)),
               "Load structure accepts the independently published CIF fixture");
        compare(Probe.rows(Session.project.structures).length, before + 1,
                "Loading a CIF adds exactly one structure through the real project model");
        const structure = Session.project.currentStructure;
        compare(structure.cell.lengthA.value, data.cell,
                "Load CIF preserves the published COD lattice length");
        compare(Probe.rows(structure.atomSites).length, data.atoms,
                "Load CIF preserves every published atom site");
        compare(structure.spaceGroup.itNumber, data.group,
                "Load CIF preserves the independently stated published space group");
    }
}
