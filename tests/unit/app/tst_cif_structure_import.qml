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
    function test_load_published_cif() {
        const before = Probe.rows(Session.project.structures).length;
        verify(Session.project.loadStructure(Probe.repoUrl(
                   "tests/fixtures/dictionary_display/published_cod_1000236.cif")),
               "Load structure accepts the independently published CIF fixture");
        compare(Probe.rows(Session.project.structures).length, before + 1,
                "Loading a CIF adds exactly one structure through the real project model");
        const structure = Probe.rows(Session.project.structures)[before];
        compare(structure.cell.lengthA.value, 10.257,
                "Load CIF preserves the published COD lattice length");
        compare(Probe.rows(structure.atomSites).length, 6,
                "Load CIF preserves every published atom site");
    }
}
