// SPDX-License-Identifier: BSD-3-Clause
import QtQuick
import QtTest
import edi.app
import EdiAcceptance 1.0
import ChartBackendAcceptance 1.0
import ReportAcceptance 1.0
import "../../unit/app/RenderedTable.js" as Render
import "../../unit/app/UiInteraction.js" as Ui

Item {
    Component { id: appFactory; Main { visible: true; width: 1280; height: 800 } }
    TestCase {
        id: test
        name: "ScanUpdates"
        when: windowShown
        property var app: null
        property bool tracking: false
        property var drawn: []
        property int frames: 0
        property double finishedAt: 0
        readonly property var labels: ({catchup: "Every pattern, display catches up", wait: "Every pattern, fit waits for the display", adaptive: "Adaptive"})
        Connections {
            target: test.app
            function onFrameSwapped() { if (test.tracking) test.frames += 1; }
        }
        Connections {
            target: Session.project ? Session.project.fit : null
            function onScanShownFileChanged() {
                const fit = Session.project.fit;
                if (test.tracking && fit.scanShownFile && (test.drawn.length === 0 || test.drawn[test.drawn.length - 1] !== fit.scanShownFile))
                    test.drawn.push(fit.scanShownFile);
            }
            function onRunningChanged() {
                if (test.tracking && !Session.project.fit.running) test.finishedAt = Date.now();
            }
        }
        function cleanup() {
            tracking = false;
            ChartBackendProof.setFrameDelay(0);
            if (Session.project && Session.project.fit.running) {
                Session.project.fit.cancel();
                tryCompare(Session.project.fit, "running", false, 10000, "The scan-update actor stops scientific work before closing its private project");
            }
            Session.closeProject();
            if (app) { app.close(); app.destroy(); }
            app = null;
            Preferences.resetToDefaults();
        }
        function open() {
            Preferences.resetToDefaults();
            app = appFactory.createObject(null);
            verify(app !== null, "Scan-update acceptance creates the real application window");
            app.requestActivate();
            tryCompare(app, "active", true, 2000, "Real scan-update input reaches the active app");
            ChartBackendProof.watch(app.contentItem);
            app.update();
            verify(waitForRendering(app.contentItem), "Qt renders before scan timing observes its actual backend");
            tryVerify(() => ChartBackendProof.facts(app.contentItem).api !== undefined, 2000, "Every timed scan has an independent actual Qt backend reference");
            const location = SettingsProof.copyProject(Qt.resolvedUrl("../../../docs/user/cli/pd-neut-cwl_cosio-d20_scan-162f/project"));
            verify(Session.openProject(location), "Scan-update acceptance opens a private saved 162-file scan");
            Ui.click(test, Probe, app, "appBar.tab.analysis");
            Ui.click(test, Probe, app, "sideBar.tab.settings");
            Ui.expandGroup(test, Probe, app, "group.patternUpdates");
            const selector = Ui.control(Probe, app, "analysis.patternUpdates");
            verify(selector !== null, "The actual Analysis Settings page exposes its pattern-update selector");
            const choices = Array.from(selector.model);
            for (const label of [labels.catchup, labels.wait, "Adaptive", "About once a second", "Only at the end"])
                compare(choices.filter(value => value === label).length, 1, "The real selector retains each separately named update mode: " + label);
            compare(selector.currentText, "Adaptive", "Adaptive remains the default update mode on a fresh store");
            return selector;
        }
        function select(selector, label) {
            app.requestActivate();
            tryCompare(app, "active", true, 2000, "Update-mode keyboard input returns to the active production window");
            Ui.click(test, Probe, app, "appBar.tab.analysis");
            Ui.click(test, Probe, app, "sideBar.tab.settings");
            Ui.expandGroup(test, Probe, app, "group.patternUpdates");
            selector = Ui.control(Probe, app, "analysis.patternUpdates");
            verify(selector !== null && Ui.rendered(selector), "The actual unfolded Settings group exposes the real update selector");
            tryCompare(selector.popup, "visible", false, 1500, "The prior update dropdown finishes closing before the next actual click");
            const index = Array.from(selector.model).indexOf(label);
            verify(index >= 0, "The selected update mode is identified by its exact real UI label");
            Ui.scrollIntoView(selector);
            Ui.click(test, Probe, app, "analysis.patternUpdates");
            tryCompare(selector.popup, "opened", true, 1000, "The real pattern-update dropdown opens for keyboard selection");
            mouseMove(app.contentItem, app.width - 1, app.height - 1);
            verify(SettingsProof.key(selector, Qt.Key_Home), "The real update selector receives Home");
            for (let i = 0; i < index; ++i)
                verify(SettingsProof.key(selector, Qt.Key_Down), "The real update selector receives each navigation key");
            verify(SettingsProof.key(selector, Qt.Key_Return), "The actual selected update mode is committed with Return");
            tryCompare(selector, "currentText", label, 1000, "The real selector displays the requested distinct update mode");
            tryCompare(Session.project.fit, "patternUpdates", Preferences.scanPatternUpdates, 1000, "The selected saved mode reaches the scientific worker independently of menu position");
            tryCompare(selector.popup, "opened", false, 1000, "The actual update dropdown closes after keyboard commitment");
            tryCompare(selector.popup, "visible", false, 1500, "The actual update dropdown completes its closing transition");
            return selector.currentText;
        }
        function test_choices_and_legacy() {
            const selector = open();
            select(selector, labels.catchup);
            select(selector, labels.wait);
            Preferences.scanPatternUpdates = 0;
            const fresh = SettingsProof.restart('import QtQuick; import edi.app; QtObject { property int savedMode: Preferences.scanPatternUpdates }');
            verify(fresh.error === undefined, "The fresh production engine reads the old stored choice without an orphan visual control");
            compare(fresh.savedMode, 0, "A fresh production engine retains the saved legacy Every pattern identifier");
            app.requestActivate();
            tryCompare(app, "active", true, 2000, "The original production window regains keyboard focus after the fresh-engine read");
            Ui.click(test, Probe, app, "appBar.tab.analysis");
            Ui.click(test, Probe, app, "sideBar.tab.settings");
            Ui.expandGroup(test, Probe, app, "group.patternUpdates");
            const visibleSelector = Ui.control(Probe, app, "analysis.patternUpdates");
            verify(visibleSelector !== null, "Legacy migration is observed in the visible actual Settings control");
            tryCompare(visibleSelector, "currentText", labels.wait, 1000, "A saved old Every pattern value maps to fit waits for the display");
            select(selector, labels.adaptive);
            const finalChoices = Array.from(visibleSelector.model);
            compare(finalChoices.indexOf(labels.catchup), finalChoices.indexOf(labels.wait) + 1, "Display catches up follows fit waits in the real menu independently of saved identifiers");
        }
        function exercise(mode, tab, inspectBacklog) {
            const selector = open();
            const selection = select(selector, labels[mode]);
            const tabName = "mainArea.analysis.tab." + (tab === "pattern" ? "fitting" : "stacked");
            Ui.click(test, Probe, app, tabName);
            tryCompare(Ui.control(Probe, app, tabName), "checked", true, 1000, "The timing receipt names the actual selected chart tab");
            const fit = Session.project.fit;
            tryVerify(() => !Session.project.calculating && Probe.datasetReady(Session.project), 10000, "The saved scan's first calculated pattern is ready before fitting");
            compare(fit.scanTotal, 162, "Every mode performs the complete independently saved scientific scan");
            drawn = [];
            frames = 0;
            finishedAt = 0;
            tracking = true;
            if (inspectBacklog) ChartBackendProof.setFrameDelay(400);
            const started = Date.now();
            fit.start();
            tryCompare(fit, "running", true, 1000, "The requested UI mode starts real scientific fitting");
            tryCompare(fit, "running", false, 120000, "The scientific worker completes its whole scan independently of display draining");
            verify(finishedAt > started, "Fit duration ends at the real worker-completion signal");
            const milliseconds = finishedAt - started;
            compare(fit.scanFitted, 162, "The timed worker fits every file without dropping scientific work");
            compare(fit.outcome, "success", "The timed scientific scan completes successfully");
            if (inspectBacklog) {
                verify(fit.scanPatternUpdates < 162, "The worker finishes while an independently slowed display still has queued patterns");
                const status = findChild(app, "statusBar.fit");
                verify(status !== null, "The real status bar exposes scan progress while the display catches up");
                tryVerify(() => {
                    const text = Render.texts(status).filter(item => Ui.rendered(item)).map(item => item.text).join(" ");
                    const match = /Showing\s*:?\s+(\d+)\s+of\s+(\d+)/i.exec(text);
                    return match !== null && Number(match[1]) === fit.scanPatternUpdates && Number(match[2]) === 162;
                }, 3000, "While behind, the actual status bar says Showing N of M with the real drawn and total counts");
            }
            ChartBackendProof.setFrameDelay(0);
            if (mode === "catchup" || mode === "wait") {
                tryCompare(fit, "scanPatternUpdates", 162, 120000, "Every pattern is actually presented before display completion");
                compare(drawn.length, 162, "Every file produces a distinct shown-file receipt");
                compare(new Set(drawn).size, 162, "Every-pattern display neither duplicates nor drops a saved file");
                verify(drawn.every((file, index) => index === 0 || drawn[index - 1] < file), "Every-pattern display preserves the independently saved ascending filename order");
                verify(frames >= 162, "Every-pattern receipts are accompanied by actual rendered frames");
            }
            tryCompare(Session.project, "currentExperimentIndex", 161, 10000, "The display ultimately reaches the saved scan's final dataset");
            tracking = false;
            return {selection: selection, tab: tab, fitted: fit.scanFitted, milliseconds: milliseconds};
        }
        function test_catchup_data() { return ["pattern", "stacked"].map(tab => ({tag: tab, tab: tab})); }
        function test_catchup(data) { exercise("catchup", data.tab, true); }
        function test_timing_data() {
            const rows = [];
            for (const tab of ["pattern", "stacked"])
                for (const mode of ["catchup", "wait", "adaptive"])
                    rows.push({tag: tab + "-" + mode, tab: tab, mode: mode});
            return rows;
        }
        function test_timing(data) { console.log("FIT_TIMING " + JSON.stringify(exercise(data.mode, data.tab, false))); }
    }
}
