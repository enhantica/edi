import QtQuick
import QtTest
import edi.app
import EdiAcceptance 1.0
import ReportAcceptance 1.0

TestCase {
    id: test
    name: "ProjectArchive"
    when: windowShown
    readonly property var cases: ["sc-neut-tof_taurine_fit", "pd-neut-cwl_cosio-d20_scan-3f", "sc-neut-cwl_tb2ti2o7-heidi_basic"]
    function cleanup() {
        Session.closeProject();
    }
    function test_open_data() {
        let rows = [];
        for (const name of cases)
            for (const route of ["folder", "record", "zip"])
                rows.push({
                    tag: name + "-" + route,
                    projectName: name,
                    route: route
                });
        return rows;
    }
    function test_open(data) {
        const folder = SettingsProof.copyProject(Probe.repoUrl("docs/user/cli/" + data.projectName + "/project"));
        verify(Session.openProject(folder), "The folder route loads the independently committed project");
        const expected = Session.project.name;
        const cell = Session.project.currentStructure.cell.lengthA.value;
        Session.closeProject();
        const input = data.route === "zip" ? Probe.repoUrl("tests/fixtures/project_archive/" + data.projectName + ".zip") : data.route === "record" ? folder.toString() + "/project.edi" : folder;
        verify(Session.openProject(input), "The app opens folders, project records and interoperable ZIP archives: " + Session.lastError);
        compare(Session.project.name, expected, "Every app open route retains the project identity");
        compare(Session.project.currentStructure.cell.lengthA.value, cell, "Archive opening retains the independently loaded cell value exactly");
        if (data.route === "zip") {
            verify(Session.project.modified, "An archive-opened project asks for its first persistent Save destination");
            const destination = SettingsProof.emptyDirectory();
            verify(Session.saveAs(destination), "First Save as materializes the archive project in a chosen folder");
            verify(!Session.project.modified && !Session.project.canUndo, "Save leaves the adopted model clean and adds no Undo step");
            compare(SettingsProof.text(destination, "reports/opaque.html"), "<p>Independently authored report</p>\n", "Archive Save keeps the carried report bytes");
            verify(Session.save(), "Later Save uses the established project folder");
        }
    }
    function test_escape() {
        verify(!Session.openProject(Probe.repoUrl("tests/fixtures/project_archive/escape.zip")), "The app refuses an archive member outside its project folder");
        verify(Session.lastError.length > 0, "The rejected archive reports its containment error");
    }
    function test_cancel() {
        verify(Session.openProject(Probe.repoUrl("docs/user/cli/sc-neut-tof_taurine_fit/project")), "The first opening starts on the real taurine project");
        verify(Session.project.calculating, "Opening publishes a usable model while its first calculation is pending");
        const second = SettingsProof.copyProject(Probe.repoUrl("tests/fixtures/loop_parameter_ids/line-segment"));
        verify(Session.openProject(second), "A second project replaces an opening project with work pending");
        const active = Session.project;
        tryCompare(active, "calculating", false, 15000, "The second project's own calculation completes");
        compare(Session.project, active, "The first project's result never replaces the second project");
        compare(active.name, "relations", "Cancellation retains the independently named second project");
        compare(active.currentStructure.cell.lengthA.value, 4.1, "Cancellation retains the second project's independent cell value");
        const rows = Probe.rows(active.currentExperiment.pattern);
        verify(rows.length === 9 && rows[0].intensityMeas === 5.0484848484848488, "No taurine reflection result reaches the second project's measured pattern");
    }
    function test_save_pending() {
        verify(Session.openProject(Probe.repoUrl("docs/user/cli/sc-neut-tof_taurine_fit/project")), "Pending Save starts on the real taurine project");
        verify(Session.project.calculating, "Save is exercised during actual pending opening work");
        const destination = SettingsProof.emptyDirectory();
        verify(Session.saveAs(destination), "Save waits for coherent rounded results before publishing");
        const before = JSON.stringify(Probe.rows(Session.project.currentExperiment.pattern));
        verify(!Session.project.modified && !Session.project.canUndo, "Pending Save finishes clean and adds no Undo step");
        Session.closeProject();
        verify(Session.openProject(destination), "A project saved during opening is immediately readable");
        tryCompare(Session.project, "calculating", false, 15000, "Reopened results settle before exact comparison");
        compare(JSON.stringify(Probe.rows(Session.project.currentExperiment.pattern)), before, "Pending Save writes the exact rounded-model pattern that a reopen calculates");
    }
}
