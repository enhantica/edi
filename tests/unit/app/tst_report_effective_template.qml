// SPDX-License-Identifier: BSD-3-Clause
import QtQuick
import QtTest
import edi.app
import EdiAcceptance 1.0
import ReportAcceptance 1.0
import "RenderedTable.js" as Render

Rectangle {
    width: 1300
    height: 1000
    Component {
        id: reportFactory
        ReportPage {}
    }
    TestCase {
        name: "ReportEffectiveTemplate"
        when: windowShown
        property var page
        function cleanup() {
            if (page)
                page.destroy();
            page = null;
            Session.closeProject();
        }
        function test_one_effective_template_matrix_survives_all_report_surfaces_data() {
            return [
                {
                    tag: "sequential-first-by-default",
                    mode: "sequential",
                    declared: false
                },
                {
                    tag: "independent-first-by-default",
                    mode: "independent",
                    declared: false
                },
                {
                    tag: "sequential-declared-later",
                    mode: "sequential",
                    declared: true
                },
                {
                    tag: "independent-declared-later",
                    mode: "independent",
                    declared: true
                }
            ];
        }
        function test_one_effective_template_matrix_survives_all_report_surfaces(data) {
            const reference = JSON.parse(SettingsProof.repoText("tests/fixtures/correlations/scan-reference.json"));
            const location = SettingsProof.copyProject(Probe.repoUrl("tests/fixtures/correlations/scan-" + data.mode));
            const analysis = SettingsProof.text(location, "analysis/analysis.edi");
            verify(!analysis.includes("_sequential_fit.template_file"), "The source witness genuinely has no declared template before the explicit override control");
            if (data.declared)
                verify(SettingsProof.write(location, "analysis/analysis.edi", analysis + "\n_sequential_fit.template_file 02.xy\n"), "The later declared template has independently different covariance from the first-file fallback");
            verify(Session.openProject(location), "The effective-template witness opens through the actual app Session: " + Session.lastError);
            tryCompare(Session.project, "calculating", false, 15000, "The initial scan finishes its actual data projection before fitting");
            compare(SettingsProof.fileFacts(location, "analysis/results.csv").bytes, undefined, "The fallback matrix witness starts without a result ledger or a fabricated successful fit");
            Session.project.fit.start();
            tryVerify(() => Session.project.fit.scanFitted === 2 && !Session.project.fit.running, 10000, "Both actual polynomial datasets complete on the app's fit worker");
            const index = data.declared ? 1 : 0, truth = reference.cases[index];
            Session.project.currentExperimentIndex = index;
            tryVerify(() => !Session.project.calculating && Probe.datasetReady(Session.project), 5000, "The actual effective template's live projection settles before taking its matrix");
            Session.project.correlations.level = 0;
            Session.project.correlations.maxParameters = 3;
            const failures = [];
            function check(matrix, source, persisted) {
                if (!matrix || matrix.error || !matrix.labels || matrix.labels.length !== 3 || !matrix.values || matrix.values.length !== 9) {
                    failures.push(source + " actual=" + JSON.stringify(matrix));
                    return;
                }
                for (let row = 0; row < 3; ++row) {
                    for (let column = 0; column < row; ++column) {
                        const i = truth.names.indexOf(matrix.labels[row]), j = truth.names.indexOf(matrix.labels[column]);
                        const actual = matrix.values[row * 3 + column];
                        const raw = i < 0 || j < 0 ? NaN : truth.matrix[i][j];
                        const digits = Math.abs(raw) >= 0.95 ? 3 : 2;
                        const expected = persisted ? Number(raw.toPrecision(digits)) : raw;
                        if (i < 0 || j < 0 || typeof actual !== "number" || !isFinite(actual) || Math.abs(actual - expected) > (persisted ? 1e-14 : 2e-4))
                            failures.push(source + " signed covariance/parameter identity differs: " + JSON.stringify(matrix));
                    }
                }
            }
            check({
                labels: Session.project.correlations.labels,
                values: Session.project.correlations.values
            }, "Analysis live");
            page = reportFactory.createObject(parent, {
                width: 1300,
                height: 1000,
                current: true
            });
            verify(page !== null && waitForPolish(page), "The report's actual preview is constructed from the fitted session");
            Session.project.report.setIncluded("charts", false);
            const preview = findChild(page, "report.preview");
            verify(preview !== null, "The effective-template gate reaches the actual native report preview");
            function renderedMatrix() {
                const charts = Render.descendants(preview).filter(item => item.correlations !== undefined && typeof item.cellColor === "function" && item.values !== undefined && item.labels !== undefined);
                if (charts.length !== 1)
                    return {
                        error: "Actual preview correlation charts=" + charts.length
                    };
                return {
                    labels: charts[0].labels,
                    values: charts[0].values
                };
            }
            check(renderedMatrix(), "Preview live");
            verify(Session.save(), "The actual app Save writes the fitted project before any disk report or reopen");
            const savedText = SettingsProof.text(location, "analysis/analysis.edi");
            if (!savedText.includes("_fit_parameter_correlation."))
                failures.push("Saved analysis has no effective-template correlation rows");
            const disk = SettingsProof.reportHtmlMatrices(location);
            verify(!disk.error, "The actual Python and CLI HTML processes complete: " + disk.error);
            check(disk.python, "Python HTML from disk, binding=" + disk.binding, true);
            check(disk.cli, "CLI HTML from disk, binding=" + disk.binding, true);
            page.destroy();
            page = null;
            Session.closeProject();
            verify(Session.openProject(location), "The app genuinely reopens its saved project without a live matrix bundle: " + Session.lastError);
            Session.project.currentExperimentIndex = index;
            tryVerify(() => !Session.project.calculating && Probe.datasetReady(Session.project), 5000, "The reopened effective template completes its actual data projection");
            Session.project.correlations.level = 0;
            Session.project.correlations.maxParameters = 3;
            check({
                labels: Session.project.correlations.labels,
                values: Session.project.correlations.values
            }, "Analysis reopened", true);
            page = reportFactory.createObject(parent, {
                width: 1300,
                height: 1000,
                current: true
            });
            verify(page !== null && waitForPolish(page), "The reopened app constructs its report from persisted state");
            const reopened = findChild(page, "report.preview");
            verify(reopened !== null, "The reopened report preview exists before reading its actual model");
            check(reopened.model.correlations, "Preview reopened", true);
            compare(failures.length, 0, "A scan uses its declared template else its first dataset, retaining the same independently normalized signed matrix in Analysis and preview, saved rows, Python/CLI HTML and the app after reopening; actual " + failures.join("; "));
        }
    }
}
