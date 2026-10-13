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
        id: pageFactory
        ReportPage {}
    }
    TestCase {
        id: test
        name: "ReportLiveFigures"
        when: windowShown
        property var page
        function init() {
            verify(SettingsProof.beginConsoleCapture(), "The console observer forwards the real QtTest handler while capturing warnings and critical messages");
        }
        function cleanup() {
            if (page)
                page.destroy();
            page = null;
            Session.closeProject();
            wait(0);
            compare(SettingsProof.consoleMessages().length, 0, "Report figure construction, layout and teardown remain free of plot-width loops and missing-window critical messages");
        }
        function test_console_observer_qualifies_both_message_severities() {
            SettingsProof.qualifyConsoleCapture();
            const messages = SettingsProof.consoleMessages();
            compare(messages.length, 2, "The console observer reaches independently emitted warning and critical escape controls");
            verify(messages.some(row => row.severity === "warning" && row.text.includes("plotWidth")), "The console observer captures the actual binding-loop warning channel");
            verify(messages.some(row => row.severity === "critical" && row.category === "qt.graphs2d" && row.text.includes("window doesn't exist")), "The console observer captures the actual Qt Graphs critical channel");
            verify(SettingsProof.beginConsoleCapture(), "Synthetic console controls are cleared before observing real report teardown");
        }
        function open(path) {
            verify(Session.openProject(Probe.repoUrl(path)), "The live-report witness opens an independently committed project: " + Session.lastError);
            tryCompare(Session.project, "calculating", false, 15000, "The live-report witness finishes loading before showing figures");
            page = pageFactory.createObject(parent, {
                width: 1300,
                height: 1000,
                current: true
            });
            verify(page !== null && waitForPolish(page), "The actual Report page lays out its live figures");
            verify(waitForRendering(page), "The actual Report page completes a frame before observing its figure controllers");
        }
        function test_report_figures_have_no_chart_console_warnings_data() {
            return [
                {
                    tag: "fitted",
                    path: "tests/fixtures/report_options/pairs"
                },
                {
                    tag: "scan",
                    path: "docs/user/cli/pd-neut-cwl_cosio-d20_scan-162f/project"
                },
                {
                    tag: "multibank",
                    path: "docs/user/cli/pd-neut-tof_ncaf-wish-5bank_start-5/project"
                }
            ];
        }
        function test_report_figures_have_no_chart_console_warnings(data) {
            failOnWarning(/(?:Binding loop detected for property.*plotWidth|window doesn't exist)/);
            open(data.path);
            if (data.tag === "fitted")
                verify(Session.project.fit.available, "The fitted console witness actually holds a fit result");
            const preview = findChild(page, "report.preview");
            verify(preview !== null && preview.contentHeight > 0, "The console gate reaches a nonempty actual report preview");
            for (const position of [0, preview.contentHeight / 2, Math.max(0, preview.contentHeight - preview.height)]) {
                preview.contentY = position;
                verify(waitForPolish(preview) && waitForRendering(preview), "Scrolling flushes each actual report figure's layout and frame");
            }
            Session.closeProject();
            verify(waitForPolish(page) && waitForRendering(page), "Closing flushes figure teardown without a missing-window warning");
        }
        function test_scan_report_structure_figure_is_present() {
            open("docs/user/cli/pd-neut-cwl_cosio-d20_scan-162f/project");
            const views = Render.descendants(page).filter(item => item.objectName === "structure.view" && item.report !== null);
            verify(views.length > 0, "The scan report creates its actual structure figure rather than leaving its place blank");
            tryVerify(() => views.every(item => item.current && item.atomCount > 0 && item.cellEdgeCount > 0), 3000, "Every scan report structure figure carries current atoms and cell edges from its reported dataset");
        }
        function test_scan_report_fitted_calculated_residual_and_bragg_series_are_present() {
            open("docs/user/cli/pd-neut-cwl_cosio-d20_scan-162f/project");
            const charts = Render.descendants(page).filter(item => item.objectName === "chart");
            const controllers = charts.reduce((all, chart) => all.concat(Probe.objectsWithProperty(chart, "calculatedSeries")), []);
            verify(controllers.length > 0, "The scan report creates an actual pattern controller with series targets");
            tryVerify(() => controllers.some(item => item.report !== null && item.calculatedSeries && item.calculatedSeries.count > 0), 3000, "The reported scan dataset has calculated points in its actual chart series");
            verify(controllers.some(item => item.report !== null && item.residualSeries && item.residualSeries.count > 0), "The reported scan dataset has residual points in its actual chart series");
            verify(controllers.some(item => item.report !== null && [item.braggSeries0, item.braggSeries1, item.braggSeries2].some(series => series && series.count > 0)), "The reported scan dataset has Bragg ticks in its actual chart series");
        }
    }
}
