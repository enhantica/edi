import QtQuick
import QtQuick.Controls
import QtTest
import edi.app
import EdiAcceptance 1.0
import ReportAcceptance 1.0
import ReportBoundaryAcceptance 1.0
import "UiInteraction.js" as Ui

Rectangle {
    width: 1300
    height: 1000
    Component {
        id: appFactory
        Main {}
    }
    TestCase {
        id: test
        property var appWindow
        name: "ReportRestoredRows"
        when: windowShown
        SignalSpy {
            id: failed
            signalName: "saveFailed"
        }
        function cleanup() {
            BoundaryProof.clearFailure();
            failed.target = null;
            Session.closeProject();
            if (appWindow)
                appWindow.destroy();
            appWindow = null;
        }
        function test_rows_survive_template_restoration_data() {
            const cases = [];
            for (const mode of ["sequential", "independent"])
                for (const saveAs of [false, true])
                    for (const change of ["first", "replacement", "rename", "failed"])
                        for (const restore of ["single-fit-undo", "settings-undo", "reset-undo"])
                            cases.push({
                                tag: [mode, saveAs, change, restore].join("-"),
                                mode,
                                saveAs,
                                change,
                                restore
                            });
            return cases;
        }
        function test_rows_survive_template_restoration(data) {
            const location = SettingsProof.copyProject(Probe.repoUrl("tests/fixtures/correlations/scan-" + data.mode));
            verify(SettingsProof.write(location, "reports/report.edi", "_edi.schema_version 3\n_report.html true\n_report.pdf true\n_report.html_offline false\n"), "The snapshot witness begins with nonempty persisted report settings");
            appWindow = appFactory.createObject(null);
            verify(appWindow !== null && waitForRendering(appWindow.contentItem), "The restoration witness runs in the actual application window");
            verify(Session.openProject(location), "The real app opens the scan snapshot witness: " + Session.lastError);
            const project = Session.project, report = project.report;
            project.currentExperimentIndex = 1;
            tryVerify(() => !project.calculating && Probe.datasetReady(project), 5000, "The selected scan dataset finishes projection before its single fit");
            project.analysis.fittingMode = "single";
            compare(project.analysis.fittingMode, "single", "The admitted mode edit chooses a single dataset fit rather than a scan run");
            tryVerify(() => !project.calculating && Probe.datasetReady(project), 5000, "The admitted mode edit settles before a fit starts");
            project.fit.patternUpdates = 3;
            if (data.change !== "first") {
                verify(SettingsProof.write(location, "reports/" + project.name + ".html", "old retained report"), "The replacement witness has real previous output bytes");
                verify(BoundaryProof.referenceRow(project, "html", project.name + ".html"), "The earlier row has independently stated saved and digest identities");
            }
            if (data.change === "rename")
                project.name = "new-output-stem";
            Ui.click(test, Probe, appWindow, "appBar.tab.analysis");
            verify(project.fit.available, "The selected dataset admits a single fit: " + project.fit.unavailableReason);
            project.fit.start();
            verify(project.fit.running, "The actual single fit starts before its Undo witness");
            tryVerify(() => !project.fit.running && project.fit.canUndo, 10000, "An actual single dataset fit creates the older template stash: " + project.fit.status + " " + project.fit.unavailableReason);
            compare(project.scan, true, "The actual fit occurs within a scan rather than an ordinary project");
            if (data.restore === "reset-undo") {
                project.analysis.fittingMode = data.mode;
                compare(project.analysis.fittingMode, data.mode, "The Reset control admits the declared scan mode");
                tryVerify(() => !project.calculating, 5000, "The scan-mode edit settles before its real run");
                project.fit.start();
                tryVerify(() => !project.fit.running && project.fit.canReset, 10000, "A real completed scan establishes the Reset fits restoration path");
            }
            report.active = true;
            const before = SettingsProof.text(location, "reports/report.edi");
            failed.target = report;
            failed.clear();
            if (data.change === "failed")
                BoundaryProof.armFailure(location, "settings");
            report.saveReport("PT Sans");
            if (data.change === "failed") {
                verify(SettingsProof.text(location, "failure-receipt").includes("settings-rename"), "The failed publication reaches the actual late settings replacement");
                verify(failed.count > 0, "Refused publication emits the real app failure signal");
                compare(SettingsProof.text(location, "reports/report.edi"), before, "A failed publication retains the previously persisted tracking rows");
            } else
                compare(failed.count, 0, "Both selected formats finish publication before template restoration");
            BoundaryProof.clearFailure();
            const published = SettingsProof.text(location, "reports/report.edi");
            if (data.change !== "failed")
                verify(published.includes("_report_file.digest"), "The successful writer has persisted full artifact identities before Undo");
            if (data.restore === "settings-undo") {
                report.writesPdf = false;
                project.undo();
                compare(report.writesPdf, true, "The settings-only restoration really reverses its edit");
            } else if (data.restore === "reset-undo") {
                project.fit.reset();
                compare(project.fit.canReset, false, "Reset fits really clears the processed scan before Undo");
                project.undo();
                verify(project.fit.canReset, "Undo really restores the prior processed scan");
            } else {
                project.undo();
                verify(!project.fit.canUndo, "The single-fit Undo actually consumes its captured fit snapshot");
            }
            tryCompare(project, "calculating", false, 10000, "The restored template settles before its later save");
            project.currentExperimentIndex = 0;
            tryVerify(() => !project.calculating && Probe.datasetReady(project), 5000, "The restored scan also projects a different dataset before its later Save");
            const rows = text => text.split("loop_").slice(1).join("loop_");
            compare(rows(project.reportText.text), rows(published), "Snapshot restoration preserves all latest saved rows including saved time and digest");
            const destination = data.saveAs ? SettingsProof.emptyDirectory() : location;
            verify(data.saveAs ? Session.saveAs(destination) : Session.save(), "The restored scan reaches the actual Save or Save as writer");
            compare(rows(SettingsProof.text(destination, "reports/report.edi")), rows(published), "Fit Undo, settings Undo and Reset Undo cannot restore obsolete artifact rows");
            Session.closeProject();
            verify(Session.openProject(destination), "The restored and saved scan reopens through the app loader");
            tryCompare(Session.project, "calculating", false, 10000, "The reopened scan completes projection");
            compare(rows(Session.project.reportText.text), rows(published), "Reopening retains every artifact row from the last completed publication");
        }
    }
}
