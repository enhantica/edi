import QtQuick
import QtTest
import edi.app
import EdiAcceptance 1.0
import ReportAcceptance 1.0
import ReportBoundaryAcceptance 1.0

Rectangle {
    width: 1300
    height: 1000
    Component {
        id: pageFactory
        ReportPage {}
    }
    TestCase {
        name: "ReportPublicationState"
        when: windowShown
        property var page
        property var browser
        SignalSpy {
            id: failed
            signalName: "saveFailed"
        }
        function cleanup() {
            BoundaryProof.clearFailure();
            failed.target = null;
            if (browser)
                browser.destroy();
            browser = null;
            if (page)
                page.destroy();
            page = null;
            Session.closeProject();
        }
        function test_published_rows_survive_every_later_save_and_refresh_text_data() {
            const cases = [];
            for (const scan of [false, true])
                for (const web of [false, true])
                    for (const saveAs of [false, true])
                        for (const change of ["first", "replacement", "rename"])
                            cases.push({
                                tag: [scan, web, saveAs, change].join("-"),
                                scan,
                                web,
                                saveAs,
                                change
                            });
            return cases;
        }
        function test_published_rows_survive_every_later_save_and_refresh_text(data) {
            const input = data.scan ? "tests/fixtures/report_context/long-scan" : "docs/user/cli/pd-neut-cwl_lbco-hrpt_start-2/project";
            const location = SettingsProof.copyProject(Probe.repoUrl(input));
            verify(SettingsProof.write(location, "reports/report.edi", "_edi.schema_version 3\n_report.html true\n_report.pdf false\n_report.html_offline false\n"), "The state witness starts with explicit report settings");
            verify(Session.openProject(location), "The state witness opens through the real app Session: " + Session.lastError);
            tryCompare(Session.project, "calculating", false, 15000, "The actual project load finishes before publication");
            page = pageFactory.createObject(parent, {
                width: 1300,
                height: 1000,
                current: true
            });
            verify(page !== null && waitForPolish(page), "The actual Report page reaches its live model");
            const project = Session.project, report = project.report;
            if (data.change !== "first") {
                verify(SettingsProof.write(location, "reports/" + project.name + ".html", "independent previous report bytes"), "Replacement and rename start with a real old output");
                verify(BoundaryProof.referenceRow(project, "html", project.name + ".html"), "The independent old row reaches the actual publication path");
                project.title = "Replacement changes the report digest";
                if (data.change === "rename")
                    project.name = "renamed-report";
            }
            tryCompare(project, "calculating", false, 15000, "The changed project settles before report publication");
            tryCompare(report, "calculating", false, 15000, "The report sees the completed current project before publication");
            const cached = project.reportText.text;
            verify(cached.includes("_report.html"), "Report Text is actually read and cached before publication");
            if (data.web) {
                browser = SettingsProof.webExport(page, report, findChild(page, "report.preview"));
                verify(browser !== null, "The browser Export resource reaches the same publication boundary");
                browser.saveReport();
            } else
                report.saveReport("PT Sans");
            const name = project.name + ".html";
            tryVerify(() => report.savedReports.some(row => row.name === name), 15000, "The actual writer successfully publishes the requested named row");
            const published = SettingsProof.text(location, "reports/report.edi");
            const failures = [];
            if (rows(project.reportText.text) !== rows(published))
                failures.push("the already-read Report Text did not invalidate after publication");
            report.writesPdf = true;
            project.undo();
            compare(report.writesPdf, false, "Undo really reverses the later report setting without undoing saved output");
            const destination = data.saveAs ? SettingsProof.emptyDirectory() : location;
            verify(data.saveAs ? Session.saveAs(destination) : Session.save(), "The later actual project Save or Save as succeeds");
            const persisted = SettingsProof.text(destination, "reports/report.edi");
            function rows(text) {
                return text.split("loop_").slice(1).join("loop_");
            }
            if (rows(persisted) !== rows(published))
                failures.push("the save model replaced the published tracking rows");
            Session.closeProject();
            verify(Session.openProject(destination), "The saved project really reopens through the app loader");
            tryCompare(Session.project, "calculating", false, 15000, "The reopened project finishes its actual calculation");
            if (!Session.project.report.savedReports.some(row => row.name === name))
                failures.push("the reloaded model lost the named saved row");
            compare(failures.length, 0, "Successful report publication stays coherent in live, persisted, scan-template and cached Text models: " + failures.join("; "));
        }
        function test_late_failure_preserves_completed_rows_and_refreshes_text_data() {
            const cases = [];
            for (const scan of [false, true])
                for (const web of [false, true])
                    for (const kind of ["settings-write", "settings-close", "pdf"])
                        cases.push({
                            tag: [scan, web, kind].join("-"),
                            scan,
                            web,
                            kind
                        });
            return cases;
        }
        function test_late_failure_preserves_completed_rows_and_refreshes_text(data) {
            const input = data.scan ? "tests/fixtures/report_context/long-scan" : "docs/user/cli/pd-neut-cwl_lbco-hrpt_start-2/project";
            const location = SettingsProof.copyProject(Probe.repoUrl(input));
            verify(SettingsProof.write(location, "reports/report.edi", "_edi.schema_version 3\n_report.html true\n_report.pdf false\n_report.html_offline false\n"), "The late-failure witness has explicit HTML-only settings");
            verify(Session.openProject(location), "The late-failure witness opens the real project");
            tryCompare(Session.project, "calculating", false, 15000, "The late-failure witness finishes loading");
            page = pageFactory.createObject(parent, {
                width: 1300,
                height: 1000,
                current: true
            });
            verify(page !== null && waitForPolish(page), "The actual Report page reaches publication");
            const project = Session.project, report = project.report;
            report.saveReport("PT Sans");
            tryVerify(() => report.savedReports.length > 0, 15000, "A real completed report establishes the previous rows");
            project.title = "Changed report before a real late failure";
            project.name = "failure-replacement";
            report.hidden = [];
            if (data.kind === "pdf")
                report.writesPdf = true;
            const before = SettingsProof.text(location, "reports/report.edi");
            const oldRows = report.savedReports.map(row => row.name + ":" + row.format + ":" + row.saved).join(";");
            tryCompare(project, "calculating", false, 15000, "The changed project settles before report publication");
            tryCompare(report, "calculating", false, 15000, "The report sees the completed current project before publication");
            const cached = project.reportText.text;
            verify(cached.includes("_report_file"), "The Text snapshot is read before the failing replacement");
            failed.target = report;
            failed.clear();
            BoundaryProof.armFailure(location, data.kind);
            if (data.web) {
                browser = SettingsProof.webExport(page, report, findChild(page, "report.preview"));
                verify(browser !== null, "The browser Export resource reaches actual late failure");
                browser.saveReport();
            } else
                report.saveReport("PT Sans");
            tryVerify(() => SettingsProof.text(location, "failure-receipt").includes(data.kind === "settings-close" ? "close-after-write" : "write-after-open"), 15000, "The failure reaches a real post-open settings or PDF write");
            BoundaryProof.clearFailure();
            verify(failed.count > 0, "The app reports a late output failure before claiming completion");
            const after = SettingsProof.text(location, "reports/report.edi");
            const failures = [];
            if (data.kind !== "pdf" && (after !== before || report.savedReports.map(row => row.name + ":" + row.format + ":" + row.saved).join(";") !== oldRows))
                failures.push("failed settings publication changed previously saved rows");
            if (rows(project.reportText.text) !== rows(after))
                failures.push("cached Text disagrees with persisted partial-success rows");
            verify(Session.save(), "The project still saves after a reported export failure");
            function rows(text) {
                return text.split("loop_").slice(1).join("loop_");
            }
            if (rows(SettingsProof.text(location, "reports/report.edi")) !== rows(after))
                failures.push("later Save lost the successful formats or restored failed rows");
            compare(failures.length, 0, "Ordinary, scan, desktop and browser failure routes retain the same completed row state: " + failures.join("; "));
        }
    }
}
