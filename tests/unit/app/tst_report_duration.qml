// SPDX-License-Identifier: BSD-3-Clause
import QtQuick
import QtTest
import edi.app
import EdiAcceptance 1.0
import ReportAcceptance 1.0
import EasyApplication.Gui.Globals as Globals
import "RenderedTable.js" as Render

Rectangle {
    width: 1200
    height: 800
    Component {
        id: statusFactory
        StatusBar {
            width: 1150
            height: 40
        }
    }
    TestCase {
        name: "ReportDuration"
        when: windowShown
        property int savedPage
        function init() {
            savedPage = Globals.Vars.appBarCurrentIndex;
            Globals.Vars.appBarCurrentIndex = 4;
        }
        function cleanup() {
            Session.closeProject();
            Globals.Vars.appBarCurrentIndex = savedPage;
        }
        function test_fit_and_scan_times_have_two_significant_digits_data() {
            const rows = [];
            for (const kind of ["fit", "scan"])
                for (const pair of [[0.023, "0.023s"], [0.41, "0.41s"], [3.2, "3.2s"], [45, "45s"], [127, "127s"]])
                    rows.push({
                        tag: kind + "-" + pair[0],
                        kind: kind,
                        seconds: pair[0],
                        expected: pair[1]
                    });
            return rows;
        }
        function test_fit_and_scan_times_have_two_significant_digits(data) {
            const url = SettingsProof.copyProject(Probe.repoUrl("tests/fixtures/report_options/pairs"));
            const text = SettingsProof.text(url, "analysis/analysis.edi").replace(/_fit_result.fitting_time\s+[^\n]+/, "_fit_result.fitting_time " + data.seconds);
            verify(SettingsProof.write(url, "analysis/analysis.edi", text), "The duration witness declares the owner's nontrivial elapsed time independently of a clock");
            verify(Session.openProject(url), "The elapsed-time witness opens through the real Session");
            tryCompare(Session.project, "calculating", false, 10000, "The elapsed-time witness finishes loading its fitted record");
            if (data.kind === "scan")
                verify(SettingsProof.publishScanSummary(Session.project, data.seconds), "The scan witness publishes an independently declared summary through the actual FitViewModel");
            compare(Session.project.fit.elapsed.replace(/\s/g, ""), data.expected, "Fit and scan times use two significant digits while retaining every whole second");
            const status = createTemporaryObject(statusFactory, parent);
            verify(status !== null && waitForPolish(status), "The actual status bar lays out the same elapsed-time value");
            tryVerify(() => Render.descendants(status).some(item => item.visible && typeof item.text === "string" && item.text.replace(/\s/g, "").includes(data.expected) && Render.texts(item).some(cell => cell.visible && cell.text !== "")), 1000, "The status bar shows the formatted fit or scan time rather than only holding it in the model");
        }
    }
}
