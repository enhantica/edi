// SPDX-License-Identifier: BSD-3-Clause
import QtQuick
import QtQuick.Window
import QtTest
import edi.app
import EdiAcceptance 1.0
import ReportAcceptance 1.0
import ChartBackendAcceptance 1.0
import PatternPolishAcceptance 1.0
import "../../unit/app/RenderedTable.js" as Render
import "../../unit/app/UiInteraction.js" as Ui

Item {
    Component { id: factory; Main { visible: true; width: 1280; height: 800 } }
    TestCase {
        id: test
        name: "BackloggedFrames"
        when: windowShown
        property var app: null
        function cleanup() {
            PatternProof.stopFollowFrames();
            ChartBackendProof.setFrameDelay(0);
            if (Session.project && Session.project.fit.running) {
                Session.project.fit.cancel();
                tryCompare(Session.project.fit, "running", false, 10000, "The backlog actor stops its own worker before closing its project");
            }
            Session.closeProject();
            if (app) { app.close(); app.destroy(); }
            app = null;
            Preferences.resetToDefaults();
        }
        function click(name) {
            console.log("BACKLOG_INPUT " + name);
            // Showing N of M text needs polish as each queued handover advances.
            // Locate the actual exposed control without waiting for global idleness.
            tryVerify(() => !Ui.moving(app.contentItem), 3000, "Live backlog navigation waits for actual viewport motion to stop");
            let control;
            tryVerify(() => {
                control = Ui.target(Ui.control(Probe, app, name));
                return control && control.enabled && Ui.exposed(control);
            }, 2000, "Backlog navigation uses an enabled real control inside its actual visible viewport: " + name);
            const point = Ui.clickPoint(control);
            verify(point !== null, "Backlog navigation has a real unclipped pointer target");
            mouseClick(control, point.x, point.y);
            tryCompare(control, "checked", true, 2000, "Actual backlog navigation selects its requested page or tab");
        }
        function settled() {
            tryVerify(() => !Ui.moving(app.contentItem), 3000, "Real navigation completes before the no-view presentation count is observed");
            app.update();
            verify(waitForRendering(app.contentItem), "The backlog observation follows a real navigation frame");
        }
        function test_backlog_identity_and_no_view() {
            Preferences.resetToDefaults();
            Preferences.patternMeasuredStyle = "linePoints";
            app = factory.createObject(null);
            verify(app !== null, "The backlog gate opens the actual application");
            app.requestActivate();
            tryCompare(app, "active", true, 2000, "The backlog actor owns real application input");
            const root = SettingsProof.copyProject(Probe.repoUrl("docs/user/cli/pd-neut-cwl_cosio-d20_scan-162f/project"));
            verify(Session.openProject(root), "The backlog gate uses every independently saved file of the real scan");
            Ui.click(test, Probe, app, "appBar.tab.analysis");
            settled();
            const chart = Render.descendants(Ui.page(app)).find(item => item.objectName === "chart" && item.visible && item.shown);
            verify(chart !== undefined, "The backlog begins on the real Analysis Pattern chart");
            verify(typeof PatternProof.watchFollowFrames === "function", "The synchronized backlog observer is rebuilt before this actor runs");
            PatternProof.watchFollowFrames(app, Session.project, chart);
            const fit = Session.project.fit;
            // The stored identifier is read from the production enum, never menu position.
            const settingsTab = Ui.control(Probe, app, "sideBar.tab.settings");
            verify(settingsTab !== null, "The real Analysis sidebar offers Settings");
            Ui.click(test, Probe, app, "sideBar.tab.settings");
            Ui.expandGroup(test, Probe, app, "group.patternUpdates");
            const selector = Ui.control(Probe, app, "analysis.patternUpdates");
            verify(selector !== null, "The catch-up fixture reaches the real mode selector");
            const index = Array.from(selector.model).indexOf("Every pattern, display catches up");
            verify(index >= 0, "Catch-up is selected by the owner's exact label");
            selector.currentIndex = index; selector.activated(index);
            compare(selector.currentText, "Every pattern, display catches up", "The selected real mode is catch-up, not fit-waits");
            tryVerify(() => !Session.project.calculating && Probe.datasetReady(Session.project), 10000, "The initial real pattern is ready before the scientific scan");
            tryVerify(() => PatternProof.measured(chart).length > 0, 3000, "The backlog witness positively observes actual measured marker points before starting its synchronized scan");
            ChartBackendProof.watch(app.contentItem);
            ChartBackendProof.setFrameDelay(400);
            fit.start();
            tryCompare(fit, "running", true, 1000, "The catch-up gate starts the real scientific worker");
            tryCompare(fit, "running", false, 120000, "The worker completes independently of the deliberately slower display");
            compare(fit.scanFitted, 162, "All saved scientific files finish while presentation remains backlogged");
            verify(fit.scanPatternUpdates > 0 && fit.scanPatternUpdates < 150, "A genuine backlog retains enough undrawn files for interrupted navigation");
            ChartBackendProof.setFrameDelay(0);
            for (const target of ["home", "correlations", "evolution"]) {
                if (target === "home") click("appBar.tab.home");
                else {
                    click("appBar.tab.analysis");
                    click("mainArea.analysis.tab." + target);
                }
                settled();
                const before = fit.scanPatternUpdates;
                for (let frame = 0; frame < 8; ++frame) {
                    app.update();
                    verify(waitForRendering(app.contentItem), "The hidden-pattern backlog is exercised through actual completed frames");
                }
                compare(fit.scanPatternUpdates, before, "Home, Correlations and Evolution cannot count or drain queued pattern presentations");
                verify(before < 162, "No-view navigation preserves a real nonempty queue");
            }
            click("mainArea.analysis.tab.fitting");
            settled();
            tryCompare(fit, "scanPatternUpdates", 162, 90000, "Returning to the Pattern chart presents every queued file, without dropping or replaying any");
            settled();
            verify(waitForPolish(app, 2000), "The application stops requesting polish once the queued pattern presentations are complete");
            const frames = PatternProof.followFrames();
            verify(frames.length >= 162, "Every handover has a scene-synchronized identity and measured-point observation");
            const name = "backlog-" + Date.now() + "-" + Math.floor(Math.random() * 1000000000) + ".json";
            verify(SettingsProof.write(Probe.repoUrl("build"), name, JSON.stringify(frames)), "The complete synchronized frame receipt is published to an owned file without console truncation");
            console.log("BACKLOG_FRAMES_FILE " + JSON.stringify({name, count: frames.length}));
        }
    }
}
