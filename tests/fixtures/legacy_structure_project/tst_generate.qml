import QtQuick
import QtTest
import edi.app

TestCase {
    name: "LegacySavedProjectGenerator"
    when: windowShown
    function test_generate() {
        verify(Session.openProject(Qt.resolvedUrl("../../../docs/user/cli/pd-neut-cwl_cosio-d20/project")), "The reference producer opens the committed cobalt input");
        tryCompare(Session.project, "calculating", false, 15000, "The reference producer waits for the original calculation");
        verify(Session.saveAs(Qt.resolvedUrl("project")), "The reference producer writes a genuine saved project into its own fixture directory");
        Session.closeProject();
    }
}
