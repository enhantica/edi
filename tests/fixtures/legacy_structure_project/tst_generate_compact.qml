import QtQuick
import QtTest
import edi.app
import ReportAcceptance 1.0
import "ui_input.js" as Input

TestCase {
    name: "LegacySavedProjectGenerator"
    when: windowShown
    function test_generate() {
        const input = SettingsProof.copyProject(Qt.resolvedUrl("project"));
        verify(Input.prepare(SettingsProof, input), "The UI reference producer builds its two-cobalt and oxygen input");
        verify(Session.openProject(input), "The reference producer opens the explicit small UI input");
        tryCompare(Session.project, "calculating", false, 15000, "The small reference input finishes calculating");
        verify(Session.saveAs(Qt.resolvedUrl("compact-project")), "The old app writes a genuine saved UI reference");
        Session.closeProject();
    }
}
