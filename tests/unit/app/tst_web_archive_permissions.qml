import QtQuick
import QtTest
import EdiAcceptance 1.0
import WebArchivePermissionTests 1.0

TestCase {
    name: "WebArchiveExport"
    when: windowShown
    WebArchivePermissionProof { id: proof }
    function test_write_archives() {
        verify(proof.writeReference(Probe.repoUrl("tests/fixtures/web_archive_permissions/project")),
               "The real web archive writers produce both ZIP files from independent inputs");
    }
}
