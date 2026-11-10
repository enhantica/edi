import QtQuick
import QtTest
import edi.app
import CasePinAcceptance 1.0

TestCase {
    id: test
    name: "CaseRegressionPin"
    when: windowShown
    property var appWindow
    Component {
        id: application
        Main {}
    }
    function initTestCase() {
        appWindow = application.createObject(null);
        verify(appWindow !== null, "Gate 2: the app example uses the real production window");
        verify(waitForRendering(appWindow.contentItem), "Gate 2: the headless app renders before opening an example");
    }
    function cleanupTestCase() {
        Session.closeProject();
        appWindow.destroy();
    }
    function test_real_app_example_result() {
        const identity = CasePinProof.identity();
        verify(identity.length > 0, "Gate 2: the runner declares one concrete case");
        Session.openExample(identity);
        tryVerify(() => Session.hasProject && Session.openedExample === identity, 10000, "Gate 2: the actual app bundle supplies the requested case");
        tryVerify(() => !Session.project.calculating && CasePinProof.ready(Session.project), 30000, "Gate 2: the actual app finishes its initial calculation before fitting or observing it");
        verify(CasePinProof.start(Session.project), "Gate 2: the actual app worker accepts the example operation");
        tryCompare(CasePinProof, "completed", true, 3500000, "Gate 2: the real app worker must finish the entire example");
        verify(CasePinProof.writeReceipt(), "Gate 2: the real app result is captured before any rounded Save");
    }
}
