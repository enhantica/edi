import QtQuick
import QtTest
import edi.app
import EdiAcceptance 1.0
import ReportAcceptance 1.0
import PropertyNotificationAcceptance 1.0

Item {
    id: surface
    width: 700
    height: 500
    PropertyNotificationProof { id: proof }
    TestCase {
        name: "E11T5PropertyNotifications"
        when: windowShown
        function result(value) {
            verify(value.ok, JSON.stringify(value));
        }
        function initTestCase() {
            failOnWarning(/.*/);
        }
        function cleanup() {
            Session.closeProject();
        }
        function test_each_property_has_its_own_notifier() {
            result(proof.metadata());
        }
        function test_category_data() {
            return ["source-legacy", "source-dedicated", "id-legacy", "id-dedicated"].map(boundary => ({tag: boundary, boundary: boundary}));
        }
        function test_category(data) {
            result(proof.category(data.boundary));
        }
        function test_block_data() {
            return [{tag: "text", error: false}, {tag: "error", error: true}];
        }
        function test_block(data) {
            result(proof.block(data.error));
        }
        function test_markdown_data() {
            return ["document-source", "document-unrelated", "layout-source", "document-font", "document-color", "dedicated-source",
                    "dedicated-font", "pointer-roundtrip"].map(boundary => ({tag: boundary, boundary: boundary}));
        }
        function test_markdown(data) {
            result(proof.markdown(surface, data.boundary));
        }
        function test_owner_deletion_data() {
            return ["category", "block", "markdown"].map(kind => ({tag: kind, kind: kind}));
        }
        function test_owner_deletion(data) {
            result(proof.deletedOwner(data.kind, surface));
        }
        function test_experiment_data() {
            return ["facility-legacy", "facility-dedicated", "instrument-legacy", "instrument-dedicated", "options", "delete"].map(boundary => ({tag: boundary, boundary: boundary}));
        }
        function test_experiment(data) {
            // Existing real-data fixture/control from CalculationOnlyFitting.test_data_transitions.
            const directory = SettingsProof.copyProject(Probe.repoUrl("tests/fixtures/excluded_display/cw"));
            verify(SettingsProof.write(directory, "observed.xye",
                    "10 100 2\n20 110 2\n30 120 2\n40 130 2\n50 140 2\n60 150 2\n70 160 2\n80 170 2\n90 180 2\n"));
            verify(Session.openProject(directory), Session.lastError);
            verify(Session.project.loadDataInto(Session.project.currentExperiment,
                    Qt.resolvedUrl(directory + "/observed.xye")), Session.project.lastError);
            const owner = Session.project.currentExperiment;
            verify(owner.descriptionEditable, "The normal plain-data source makes description selectors editable");
            result(proof.experiment(owner, Session, data.boundary));
            if (data.boundary === "delete") {
                compare(Session.hasProject, false, "Protected Close detaches the current project");
                tryVerify(() => !proof.retiredOwnerAlive());
            }
        }
    }
}
