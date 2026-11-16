import QtQuick
import QtTest
import edi.app
import EdiAcceptance 1.0
import ReportAcceptance 1.0
import PatternPolishAcceptance 1.0
import "UiInteraction.js" as Ui
import "RenderedTable.js" as Render
import "../../fixtures/physical_axes/input.js" as AxisInput
import ReportBoundaryAcceptance 1.0

Item {
    id: surface
    width: 1200
    height: 850
    Component {
        id: chartFactory
        PatternChart {
            width: 1100
            height: 760
            shown: true
            settingsPage: "pattern"
        }
    }
    Component {
        id: scanFactory
        ScanViewChart {
            width: 1100
            height: 760
            shown: true
        }
    }
    TestCase {
        id: test
        name: "PatternPhysicalAxes"
        when: windowShown
        property var chart
        property var scanFigures: []
        property var peer
        property var reportFigure
        property var root
        readonly property var nativeValues: [40, 52, 64]
        readonly property var intensities: [20, 33, 25]
        readonly property real wavelength: 1.87
        readonly property real difc: 1734.5
        readonly property var timeValues: [1200, 3100, 5900]
        function open(beam) {
            root = SettingsProof.copyProject(Qt.resolvedUrl(beam === "cw" ? "../../fixtures/loop_parameter_ids/line-segment" : "../../fixtures/excluded_display/tof"));
            AxisInput.prepare(SettingsProof, root, beam);
            verify(Session.openProject(root), "The real loader opens the independent physical-axis input");
            tryCompare(Session.project, "calculating", false, 10000, "The independent calculation finishes before chart input");
            chart = chartFactory.createObject(surface, {
                experiment: Session.project.currentExperiment,
                axisProject: Session.project
            });
            verify(chart !== null && waitForPolish(chart) && waitForRendering(chart), "The actor renders the real Pattern chart");
            select(findChild(chart, "chart.toolbar.measuredStyle"), label => label === "Line");
        }
        function cleanup() {
            if (chart)
                chart.destroy();
            if (peer)
                peer.destroy();
            if (reportFigure)
                reportFigure.destroy();
            chart = peer = reportFigure = null;
            for (const figure of scanFigures)
                figure.destroy();
            scanFigures = [];
            Session.closeProject();
        }
        function select(combo, predicate) {
            verify(combo !== null && combo.visible && combo.enabled, "The real chart selector is visible and enabled");
            const options = Array.from({
                length: combo.count
            }, (_, i) => combo.textAt(i));
            const index = options.findIndex(predicate);
            verify(index >= 0, "The real selector offers the requested physical quantity");
            const point = Ui.clickPoint(combo);
            verify(point !== null, "The requested chart selector has an exposed pointer target");
            mouseClick(combo, point.x, point.y);
            tryCompare(combo.popup, "opened", true, 1000, "Real input opens the chart selector");
            const list = combo.popup.contentItem;
            list.positionViewAtIndex(index, ListView.Contain);
            tryVerify(() => list.itemAtIndex(index) && Ui.exposed(list.itemAtIndex(index)), 1000, "The requested physical choice is visible in the actual popup");
            const entry = list.itemAtIndex(index);
            mouseClick(entry, entry.width / 2, entry.height / 2);
            tryCompare(combo, "currentIndex", index, 1000, "Real input selects the requested physical quantity");
            tryCompare(combo.popup, "visible", false, 1000, "The physical-quantity popup closes after selection");
        }
        function converted(axis, value, beam) {
            const d = beam === "cw" ? wavelength / (2 * Math.sin(value * Math.PI / 360)) : value / difc;
            if (axis === "native")
                return value;
            if (axis === "d")
                return d;
            if (axis === "q")
                return 2 * Math.PI / d;
            return 1 / (2 * d);
        }
        function test_axes_follow_independent_bragg_and_tof_relations_data() {
            const rows = [];
            for (const beam of ["cw", "tof"])
                for (const axis of ["native", "d", "q", "sine"])
                    rows.push({
                        tag: beam + "-" + axis,
                        axis,
                        beam
                    });
            return rows;
        }
        function test_axes_follow_independent_bragg_and_tof_relations(data) {
            open(data.beam);
            const combo = findChild(chart, "chart.toolbar.xaxis");
            verify(combo !== null && combo.count === 4, "Pattern charts offer native, d, Q and sin(theta)/lambda");
            const patterns = {
                native: label => data.beam === "cw" ? /2.?θ|two.?theta/i.test(label) : /TOF|time.*flight/i.test(label),
                d: label => /\bd(?:-spacing)?\b/i.test(label),
                q: label => /\bQ\b/.test(label),
                sine: label => /sin/i.test(label)
            };
            select(combo, patterns[data.axis]);
            const expected = (data.beam === "cw" ? nativeValues : timeValues).map((x, i) => ({
                        x: converted(data.axis, x, data.beam),
                        y: intensities[i]
                    })).sort((a, b) => a.x - b.x);
            checkMeasured(chart, expected, "Pattern");
            peer = chartFactory.createObject(surface, {
                experiment: Session.project.currentExperiment,
                axisProject: Session.project
            });
            verify(peer !== null && waitForPolish(peer), "A peer production chart binds the same project axis");
            checkMeasured(peer, expected, "Peer chart");
            const model = BoundaryProof.fullModel(Session.project.report);
            verify(model.experiments.length === 2 && model.experiments[0].pattern.current, "The report builds the actual current axis presentation");
            const report = model.experiments[0].pattern;
            const measured = report.series.filter(row => row.kind === "measured");
            compare(measured.length, 1, "The exported report contains exactly one measured series for this experiment");
            checkPairs(measured[0].x.map((x, i) => ({
                        x,
                        y: measured[0].y[i]
                    })), expected, "Report JSON");
            reportFigure = chartFactory.createObject(surface, {
                report: Session.project.report,
                reportExperiment: model.experiments[0].id,
                settingsPage: ""
            });
            verify(reportFigure !== null && waitForPolish(reportFigure), "The report figure uses the production Pattern chart");
            checkMeasured(reportFigure, expected, "Report figure");
            const html = BoundaryProof.htmlFromJson(JSON.stringify(model), SettingsProof.localPath(Probe.repoUrl("data")));
            const embedded = /<script type="application\/json" id="edi-report-model">([\s\S]*?)<\/script>/.exec(html);
            verify(embedded !== null, "The actual HTML exporter embeds its browser chart model");
            const browser = JSON.parse(embedded[1]).experiments[0].pattern.browser;
            verify(browser && browser.traces.length > 0, "The exported HTML supplies its plotted trace coordinates");
            const trace = browser.traces.find(row => Array.isArray(row.x) && row.x.length === expected.length && Array.isArray(row.y) && row.y.every((y, i) => Math.abs(y - expected[i].y) < 1e-8));
            verify(trace !== undefined, "The HTML's measured trace retains the independently specified intensities");
            checkPairs(trace.x.map((x, i) => ({
                        x,
                        y: trace.y[i]
                    })), expected, "HTML chart");
            for (const mode of ["stacked", "map"]) {
                const figure = scanFactory.createObject(surface, {
                    project: Session.project,
                    mode
                });
                scanFigures.push(figure);
                verify(figure !== null && waitForPolish(figure), "The actual Stacked and Map views bind the independent joint project");
                verify(figure.scan === Session.project.scanViews, "Each production scan renderer consumes the project's shared axis source");
                let rows;
                tryVerify(() => {
                    rows = PatternProof.scanPoints(figure.scan);
                    return rows.length === 2 && rows.every(row => row.points.length === expected.length);
                }, 3000, "Both datasets reach the actual Stacked and Map rendering source");
                for (const row of rows)
                    checkPairs(row.points, expected, mode + " renderer");
            }
            for (const figure of scanFigures)
                figure.destroy();
            scanFigures = [];
            chart.destroy();
            peer.destroy();
            reportFigure.destroy();
            chart = peer = reportFigure = null;
            verify(waitForRendering(surface), "Axis persistence closes the figures before saving the real project");
            verify(Session.save(), "The real session saves its selected pattern-axis state");
            const savedAnalysis = SettingsProof.text(root, "analysis/analysis.edi");
            const persisted = data.axis === "d" ? "d_spacing" : "native";
            if (data.axis === "q" || data.axis === "sine")
                verify(!/_(?:pattern_chart|report)\.x_axis\s+(?:q|sin_theta_over_lambda)/.test(savedAnalysis), "Session-only reciprocal axes preserve the supported saved-file vocabulary");
            Session.closeProject();
            verify(Session.openProject(root), "The saved axis project reopens through the real loader");
            compare(Session.project.patternXAxis, persisted, "Native and d persist; the additional reciprocal axes leave the prior saved native choice intact");
        }
        function checkPairs(actual, expected, context) {
            actual = actual.slice().sort((a, b) => a.x - b.x);
            compare(actual.length, expected.length, context + " retains every independently specified measured point");
            for (let i = 0; i < expected.length; ++i) {
                verify(Math.abs(actual[i].x - expected[i].x) < 1e-8, context + " follows the independent Bragg or zero-offset TOF conversion");
                verify(Math.abs(actual[i].y - expected[i].y) < 1e-8, context + " preserves each intensity and its x association");
            }
        }
        function checkMeasured(figure, expected, context) {
            let actual;
            tryVerify(() => {
                const curves = PatternProof.series(figure, "chart.series.meas").filter(row => row.name === "chart.series.meas");
                if (curves.length !== 1)
                    return false;
                actual = curves[0].points;
                return actual.length === expected.length;
            }, 3000, context + " publishes the real complete measured series");
            checkPairs(actual, expected, context);
        }
    }
}
