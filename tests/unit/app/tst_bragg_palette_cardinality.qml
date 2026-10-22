import QtQuick
import "RenderedTable.js" as Render
import "ApprovedPalette.js" as Approved
import QtTest
import edi.app
import EdiAcceptance 1.0
import ReportAcceptance 1.0
import EasyApplication.Gui.Style as Style

Rectangle {
    width: 1300
    height: 1000
    Component {
        id: factory
        PatternChart {
            width: 1250
            height: 900
        }
    }
    TestCase {
        name: "BraggPaletteCardinality"
        when: windowShown
        property var chart
        property string oldScheme
        property int oldTheme
        function initTestCase() {
            oldScheme = Preferences.colourScheme;
            oldTheme = Style.Colors.theme;
            const location = SettingsProof.copyProject(Qt.resolvedUrl("../../fixtures/report_palette/project"));
            verify(Session.openProject(location), "The complete-palette witness opens independently named linked structures");
            tryCompare(Session.project, "calculating", false, 15000, "All independent structure reflections finish calculating");
        }
        function cleanupTestCase() {
            Preferences.colourScheme = oldScheme;
            Style.Colors.theme = oldTheme;
            Session.closeProject();
        }
        function cleanup() {
            if (chart)
                chart.destroy();
            chart = null;
        }
        function test_native_bragg_ticks_labels_and_icons_share_every_colour_data() {
            const reference = Approved.reference(SettingsProof);
            const cases = [];
            for (const scheme of reference.schemes)
                for (const dark of [false, true])
                    for (const report of [false, true])
                        cases.push({
                            tag: [scheme.id, dark, report].join("-"),
                            scheme: scheme.id,
                            dark,
                            report
                        });
            return cases;
        }
        function test_native_bragg_ticks_labels_and_icons_share_every_colour(data) {
            Preferences.colourScheme = data.scheme;
            Style.Colors.theme = data.dark ? Style.Colors.DarkTheme : Style.Colors.LightTheme;
            const project = Session.project;
            const expected = Approved.colours(SettingsProof, data.scheme, "structures", project.structures.count, data.report ? false : data.dark);
            const input = data.report ? {
                report: project.report,
                reportExperiment: project.currentExperiment.name
            } : {
                experiment: project.currentExperiment
            };
            if (data.report) {
                project.report.colourScheme = data.scheme;
                project.report.active = true;
            }
            chart = factory.createObject(parent, input);
            chart.colors.light = data.report;
            verify(chart !== null && waitForPolish(chart), "The actual native or report pattern chart reaches its controller");
            const controllers = Probe.objectsWithProperty(chart, "braggLabels");
            compare(controllers.length, 1, "The actual chart has one shared presentation controller");
            const controller = controllers[0];
            tryVerify(() => controller.braggLabels.length === project.structures.count, 5000, "Every independent structure reaches the actual Bragg rows");
            let series = [];
            tryVerify(() => {
                series = Render.series(chart).filter(item => String(item.objectName).startsWith("chart.series.bragg.") && item.at !== undefined);
                return series.length === controller.braggLabels.length && series.every(row => row.count > 1);
            }, 3000, "Every per-structure Qt series finishes its actual deferred point upload before its colour is observed");
            const failures = [];
            for (let place = 0; place < controller.braggLabels.length; ++place) {
                const label = controller.braggLabels[place];
                const wanted = expected[place];
                if (String(label.color).toLowerCase() !== wanted)
                    failures.push("label " + place);
                if (!data.report && String(AppColors.structure(place)).toLowerCase() !== wanted)
                    failures.push("icon " + place);
                const ink = series.filter(row => {
                    for (let point = 0; point < row.count; ++point)
                        if (Math.abs(row.at(point).y - label.centre) < .5)
                            return true;
                    return false;
                });
                if (ink.length !== 1 || String(ink[0].color).toLowerCase() !== wanted)
                    failures.push("actual tick series " + place);
            }
            compare(failures.length, 0, "Every real native/report tick, row label and icon keeps the frozen structure colour across every entry and gradient endpoint: " + failures.join(", "));
        }
    }
}
