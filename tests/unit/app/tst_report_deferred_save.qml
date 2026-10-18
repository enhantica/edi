// SPDX-License-Identifier: BSD-3-Clause
import QtQuick
import QtTest
import edi.app
import EdiAcceptance 1.0
import ReportAcceptance 1.0
import "RenderedTable.js" as Render

Item {
    width: 1300
    height: 1000
    Component {
        id: mainFactory
        Main {}
    }
    TestCase {
        name: "ReportDeferredSave"
        when: windowShown
        property var window
        property var location
        SignalSpy {
            id: saved
            signalName: "saved"
        }
        SignalSpy {
            id: failed
            signalName: "saveFailed"
        }
        function cleanup() {
            saved.target = null;
            failed.target = null;
            Session.closeProject();
            if (window)
                window.destroy();
            window = null;
        }
        function test_finished_figures_survive_navigation_data() {
            return [
                {
                    tag: "deferred-pdf",
                    deferred: true,
                    pdf: true,
                    figures: true
                },
                {
                    tag: "deferred-html",
                    deferred: true,
                    pdf: false,
                    figures: true
                },
                {
                    tag: "deferred-excluded",
                    deferred: true,
                    pdf: true,
                    figures: false
                },
                {
                    tag: "immediate-pdf",
                    deferred: false,
                    pdf: true,
                    figures: true
                }
            ];
        }
        function draws(facts) {
            verify(!facts.error && facts.pages.length > 0, "The actual saved PDF has readable page and image objects: " + facts.error);
            return imageIdentities(facts);
        }
        function imageIdentities(facts) {
            return (facts.pages ?? []).reduce((all, page) => all.concat(page.image_draws), []).map(image => ({
                        pixels: image.pixels,
                        sha256: image.sha256
                    }));
        }
        function test_finished_figures_survive_navigation(data) {
            location = SettingsProof.copyProject(Probe.repoUrl("tests/fixtures/report_evolution/project"));
            verify(SettingsProof.write(location, "reports/report.edi", "_edi.schema_version 3\n_report.html true\n_report.pdf " + data.pdf + "\n_report.html_offline false\n"), "The navigation witness independently declares its output formats");
            verify(Session.openProject(location), "The actual application opens the committed scan witness: " + Session.lastError);
            tryCompare(Session.project, "calculating", false, 15000, "The initial scan projection finishes before the save request");
            window = mainFactory.createObject(null, {
                width: 1300,
                height: 1000,
                visible: true
            });
            verify(window !== null, "The navigation gate creates the production application window");
            AppState.open(AppState.Page.Report);
            let page;
            tryVerify(() => {
                page = Render.descendants(window.contentItem).find(item => item.pageName === "report");
                return page && page.current;
            }, 5000, "The real workflow opens its Report page");
            verify(waitForPolish(page) && waitForRendering(page), "The actual Report page finishes layout and drawing before the first save");
            const project = Session.project, report = project.report;
            report.setIncluded("charts", data.figures);
            report.setIncluded("evolution", data.figures);
            const preview = findChild(page, "report.preview");
            verify(preview !== null && waitForPolish(preview), "The actual preview applies included and excluded figure options");
            const group = findChild(page, "group.reportExport");
            verify(group !== null, "The navigation witness reaches the production Export group");
            const actions = Render.descendants(group).filter(item => item.text === "Save report" && typeof item.clicked === "function");
            compare(actions.length, 1, "The actual Export group has exactly one Save report action");
            const action = actions[0];
            saved.target = report;
            failed.target = report;
            saved.clear();
            failed.clear();
            const htmlName = "reports/" + project.name + ".html", pdfName = "reports/" + project.name + ".pdf";
            const publications = [];
            report.savedReportsChanged.connect(() => {
                for (const row of report.savedReports) {
                    if (row.state !== "current")
                        continue;
                    const facts = row.format === "pdf" ? SettingsProof.pdfFacts(SettingsProof.childUrl(location, "reports/" + row.name)) : null;
                    publications.push({
                        format: row.format,
                        calculating: report.calculating,
                        exists: SettingsProof.fileFacts(location, "reports/" + row.name).bytes > 0,
                        error: facts ? facts.error : false,
                        images: facts ? imageIdentities(facts) : []
                    });
                }
            });
            const modelBefore = JSON.stringify(preview.model);
            if (data.deferred) {
                // Keep request and navigation in one input turn, before worker delivery.
                project.currentStructure.cell.lengthA.value = 5.37;
                compare(report.calculating, true, "The real parameter edit owes a calculation at the Save report boundary");
                verify(action.enabled, "Save report remains enabled while its calculation is pending");
                action.clicked();
                compare(group.savePending, true, "The real Save report handler retains the calculation-deferred request");
                compare(saved.count, 0, "No format is published before the requested calculation finishes");
                compare(report.savedReports.length, 0, "No current saved-file row exists for the unfinished model");
                const other = findChild(window.contentItem, "appBar.tab.structure");
                verify(other !== null && other.enabled, "The real app bar offers another enabled workflow page");
                AppState.open(AppState.Page.Structure);
                compare(page.current, false, "The real workflow has left Report before worker delivery");
                compare(report.calculating, true, "Navigation completes while the requested calculation is still owed");
                verify(!SettingsProof.fileFacts(location, htmlName).bytes && !SettingsProof.fileFacts(location, pdfName).bytes, "Leaving Report does not publish an unfinished file");
            } else
                action.clicked();
            tryCompare(report, "calculating", false, 15000, "The real edited project finishes calculating");
            tryVerify(() => saved.count === 1 || failed.count > 0, 15000, "The deferred or immediate Save report reaches actual file publication");
            compare(failed.count, 0, "The actual Save report completes without an export failure");
            compare(report.savedReports.length, data.pdf ? 2 : 1, "Only completed ticked formats receive saved-file rows");
            verify(report.savedReports.every(row => row.state === "current"), "Every completed row is current for the finished model");
            const html = SettingsProof.htmlModel(SettingsProof.childUrl(location, htmlName));
            verify(!html.error && html.structures.length === 1 && html.experiments.length === 1, "The actual saved HTML retains the finished structure and experiment");
            if (data.deferred) {
                verify(JSON.stringify(html) !== modelBefore, "The save witness changes its model instead of exporting the initial preview again");
                verify(html.structures[0].categories.some(category => category.rows && category.rows.some(row => row.text && String(row.text).includes("5.37"))), "The actual exported structure contains the independently authored finished cell length");
            }
            const actual = data.pdf ? draws(SettingsProof.pdfFacts(SettingsProof.childUrl(location, pdfName))) : [];
            verify(publications.length > 0 && publications.every(row => !row.calculating && row.exists && !row.error), "Every current-row notification follows calculation completion and publication of a readable actual file");
            if (data.pdf)
                verify(publications.some(row => row.format === "pdf") && publications.filter(row => row.format === "pdf").every(row => JSON.stringify(row.images) === JSON.stringify(actual)), "The PDF is marked current only with its final figure content already present, including at every row notification");
            const reference = JSON.parse(SettingsProof.repoText("tests/fixtures/report_evolution/reference.json"));
            compare(actual.length, data.pdf && data.figures ? 2 + reference.names.length : 0, "The saved PDF draws the included structure, pattern and every authored evolution image, and draws no excluded figure");
            if (!data.pdf)
                verify(!SettingsProof.fileFacts(location, pdfName).bytes, "The deferred HTML-only control creates no PDF");
            if (data.deferred) {
                AppState.open(AppState.Page.Report);
                tryCompare(page, "current", true, 3000, "The same production Report page returns for the finished-model control");
                verify(waitForPolish(preview) && waitForRendering(preview), "The finished on-page model has completed layout and drawing");
            }
            saved.clear();
            action.clicked();
            tryCompare(saved, "count", 1, 15000, "The unchanged immediate on-page Save report writes the same ticked formats");
            compare(failed.count, 0, "The finished immediate on-page control also succeeds");
            if (data.pdf)
                compare(JSON.stringify(actual), JSON.stringify(draws(SettingsProof.pdfFacts(SettingsProof.childUrl(location, pdfName)))), "Every deferred structure, pattern and evolution image matches the immediate save of the same finished model, including image bytes and dimensions");
            verify(report.savedReports.every(row => row.state === "current"), "The immediate on-page save retains current completed rows");
        }
    }
}
