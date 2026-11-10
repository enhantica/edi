// SPDX-License-Identifier: BSD-3-Clause
import QtQuick
import QtTest
import edi.app
import EdiAcceptance 1.0
import ReportAcceptance 1.0
import "RenderedTable.js" as Render

Rectangle {
    width: 1200
    height: 900
    Component {
        id: experimentFactory
        ExperimentPage {}
    }
    Component {
        id: analysisFactory
        AnalysisPage {}
    }
    TestCase {
        name: "ReportDAxis"
        when: windowShown
        property var savedMeasuredStyle
        function init() {
            savedMeasuredStyle = typeof Preferences.patternMeasuredStyle === "string" ? Preferences.patternMeasuredStyle : null;
            if (savedMeasuredStyle !== null)
                Preferences.patternMeasuredStyle = "linePoints";
        }
        function cleanup() {
            if (savedMeasuredStyle !== null)
                Preferences.patternMeasuredStyle = savedMeasuredStyle;
            Session.closeProject();
        }
        function test_real_pattern_selectors_use_the_nontrivial_d_conversion_data() {
            return [
                {
                    tag: "experiment",
                    analysis: false
                },
                {
                    tag: "analysis",
                    analysis: true
                }
            ];
        }
        function test_real_pattern_selectors_use_the_nontrivial_d_conversion(data) {
            const url = SettingsProof.copyProject(Probe.repoUrl("tests/fixtures/loop_parameter_ids/line-segment"));
            let text = SettingsProof.text(url, "experiments/bank.edi");
            text = text.replace("_instrument.setup_wavelength 1.54", "_instrument.setup_wavelength 1.87");
            text = text.replace(/(\n_data.intensity_meas_su\n)40 /, function (match, header) {
                return header + "30 ";
            });
            verify(SettingsProof.write(url, "experiments/bank.edi", text), "The d-axis witness declares wavelength 1.87 and a measured point at 30 degrees");
            verify(Session.openProject(url), "The actual app opens the nontrivial d-axis input");
            tryCompare(Session.project, "calculating", false, 10000, "The d-axis witness is loaded before reading its chart layer");
            const factory = data.analysis ? analysisFactory : experimentFactory;
            const page = createTemporaryObject(factory, parent, {
                width: 1200,
                height: 900,
                current: true
            });
            verify(page !== null && waitForPolish(page), "The actual Experiment or Analysis page lays out its pattern chart");
            const measured = findChild(page, "chart.measured");
            verify(measured !== null, "The d-axis gate reaches the actual rendered measured layer");
            tryVerify(() => SettingsProof.points(measured).some(point => Math.abs(point.x - 30) < 1e-9), 2000, "The native chart really contains the independent 30-degree witness");
            const selector = findChild(page, "chart.toolbar.xaxis");
            verify(selector !== null && selector.enabled, "Both actual pattern pages enable the x-axis selector");
            let index = -1;
            for (let i = 0; i < selector.count; ++i)
                if (/^d(?: |$|[ -])/.test(selector.textAt(i)))
                    index = i;
            verify(index >= 0, "The real x-axis selector offers d spacing");
            mouseClick(selector, selector.width / 2, selector.height / 2);
            tryVerify(() => selector.popup.opened, 1000, "Actual pointer input opens the x-axis selector");
            const list = selector.popup.contentItem;
            list.positionViewAtIndex(index, ListView.Contain);
            list.forceLayout();
            const entry = list.itemAtIndex(index);
            verify(entry !== null, "The d-spacing option has a real popup delegate");
            mouseClick(entry, entry.width / 2, entry.height / 2);
            tryCompare(selector, "currentIndex", index, 1000, "Actual pointer input selects d spacing");
            tryVerify(() => SettingsProof.points(measured).some(point => Math.abs(point.x - 3.6126) < 0.00005), 2000, "The actual measured layer uses d = wavelength / (2 sin(theta)) at 1.87 A and 30 degrees");
            compare(Session.project.modified, true, "Every Pattern selector edits the one project-owned x axis followed by the report");
            compare(Session.project.patternDSpacing, true, "The project report follows the nontrivial d-spacing choice from either page");
        }
    }
}
