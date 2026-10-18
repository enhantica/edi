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
        name: "ReportLinkPublication"
        when: windowShown
        property var page
        property var browser
        SignalSpy {
            id: failed
            signalName: "saveFailed"
        }
        SignalSpy {
            id: saved
            signalName: "saved"
        }
        function cleanup() {
            BoundaryProof.clearFailure();
            failed.target = null;
            saved.target = null;
            if (browser)
                browser.destroy();
            browser = null;
            if (page)
                page.destroy();
            page = null;
            Session.closeProject();
        }
        function test_actual_app_output_does_not_follow_retained_links_data() {
            const cases = [];
            for (const format of ["html", "pdf", "both"])
                for (const link of ["directory", "final", "none", "temp-symbolic", "temp-hard", "linked-temp-symbolic", "linked-temp-hard"])
                    for (const lateFailure of [false, true])
                        for (const web of [false, true])
                            cases.push({
                                tag: [format, link, lateFailure, web].join("-"),
                                format,
                                link,
                                lateFailure,
                                web
                            });
            return cases;
        }
        function test_actual_app_output_does_not_follow_retained_links(data) {
            const location = SettingsProof.copyProject(Probe.repoUrl("tests/fixtures/correlations/polynomial-3"));
            const outside = SettingsProof.emptyDirectory();
            const settings = "_edi.schema_version 3\n_report.html " + (data.format !== "pdf") + "\n_report.pdf " + (data.format !== "html") + "\n_report.html_offline false\n";
            verify(SettingsProof.write(location, "reports/report.edi", settings), "The link witness starts with the selected actual output formats");
            verify(SettingsProof.write(location, "reports/carried.html", "independent retained artifact"), "The link witness has a carried artifact whose bytes must survive");
            verify(Session.openProject(location), "The actual app opens the retained-link project: " + Session.lastError);
            const project = Session.project, report = project.report;
            tryCompare(project, "calculating", false, 5000, "The real project finishes its initial calculation");
            page = pageFactory.createObject(parent, {
                width: 1300,
                height: 1000,
                current: true
            });
            verify(page !== null && waitForPolish(page), "The native Report page builds its actual publication model");
            const selected = data.format === "pdf" ? "pdf" : "html";
            verify(data.link.includes("temp-") ? BoundaryProof.temporaryAlias(location, outside, project.name + "." + selected, data.link.endsWith("hard"), data.link.startsWith("linked-")) : data.link === "none" ? SettingsProof.write(outside, "target", "independent unlinked control") : BoundaryProof.retainedLink(location, outside, data.link, project.name + "." + selected), "The fixture creates a real parent or final-file link before the app writes");
            const before = BoundaryProof.inventory(outside);
            verify(before.error === undefined && Object.keys(before).length > 0, "The untouched external byte inventory is independently observable");
            const oldSettings = SettingsProof.text(location, "reports/report.edi");
            failed.target = report;
            failed.clear();
            saved.target = report;
            saved.clear();
            if (data.lateFailure)
                BoundaryProof.armFailure(location, "settings");
            if (data.web) {
                browser = SettingsProof.webExport(page, report, findChild(page, "report.preview"));
                verify(browser !== null, "The actual browser Export resource reaches the same retained filesystem boundary");
                browser.saveReport();
            } else
                report.saveReport("PT Sans");
            tryVerify(() => failed.count > 0 || saved.count > 0, 10000, "The actual native or browser-capability writer finishes its selected formats before observation");
            const after = BoundaryProof.inventory(outside);
            if (data.lateFailure) {
                verify(SettingsProof.text(location, "failure-receipt").includes("settings-rename"), "The late-failure branch really reaches settings publication after its report output");
                verify(failed.count > 0, "A real late settings failure is reported by the app");
                compare(SettingsProof.text(location, "reports/report.edi"), oldSettings, "Failed settings publication retains the previous tracking document");
            }
            compare(JSON.stringify(after), JSON.stringify(before), "Every app HTML and PDF write preserves every external byte, including before a later settings failure");
            compare(SettingsProof.text(location, "reports/carried.html"), "independent retained artifact", "Successful and refused output writes preserve carried artifacts exactly");
            if (!data.lateFailure && data.link === "none")
                compare(failed.count, 0, "A regular owned directory still permits successful output publication");
            if (!data.lateFailure && !failed.count) {
                for (const format of (data.format === "both" ? ["html", "pdf"] : [data.format]))
                    verify(BoundaryProof.ownedOutput(location, project.name + "." + format), "Successful publication owns each output and its parent without retained links");
                compare(SettingsProof.text(location, "reports/carried.html"), "independent retained artifact", "Detaching linked output storage retains carried report bytes");
            }
        }
    }
}
