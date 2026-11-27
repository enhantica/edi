// SPDX-License-Identifier: BSD-3-Clause
import QtQuick
import QtTest
import edi.app
import EdiAcceptance 1.0
import ReportAcceptance 1.0
import "UiInteraction.js" as Ui
import "RenderedTable.js" as Render

TestCase {
    id: test
    name: "DataFileOpen"
    when: windowShown
    property var app
    property var savedRecent
    property string savedLast
    SignalSpy {
        id: settlements
        signalName: "dataLoadSettled"
    }
    Component { id: application; Main {} }

    function init() {
        savedRecent = RecentProjects.settings.recent.slice();
        savedLast = RecentProjects.settings.last;
        Session.closeProject();
        AppState.reset();
    }

    function cleanup() {
        settlements.target = null;
        settlements.clear();
        if (app)
            app.destroy();
        app = null;
        Session.closeProject();
        RecentProjects.settings.recent = savedRecent;
        RecentProjects.settings.last = savedLast;
        RecentProjects.refresh();
    }

    function openWindow() {
        app = application.createObject(null, { width: 1280, height: 900, visible: true });
        verify(app && waitForRendering(app.contentItem), "The file tests use the rendered application window");
    }

    function loadProgress() {
        return Render.descendants(app.contentItem).some(item =>
            Ui.rendered(item) && item.Accessible.role === Accessible.ProgressBar &&
            /data/i.test(item.Accessible.name + " " + item.Accessible.description));
    }

    function test_file_chooser_leaves_the_gui_live_during_load() {
        const directory = "tests/fixtures/ui_responsiveness/scan/44k_data/";
        const fileName = "scan-0514_pilatus_integrated_0000.xy";
        const relative = directory + fileName;
        const expected = SettingsProof.repoText(relative).split(/\r?\n/)
            .map(line => line.trim())
            .filter(line => line && !line.startsWith("#"))
            .map(line => line.split(/\s+/).map(Number))
            .filter(row => row[1] > 0);
        verify(expected.length > 0, "The committed scan member supplies positive Bragg observations");

        openWindow();
        const input = Probe.repoUrl("tests/fixtures/loop_parameter_ids/line-segment");
        verify(Session.openProject(SettingsProof.copyProject(input)), "The GUI opens the existing powder project before replacing data");
        tryCompare(Session.project, "calculating", false, 15000, "The starting calculation settles before the probe");
        const previousFile = Session.project.currentExperiment.dataFile;
        verify(previousFile !== fileName, "The destination initially has different data");
        Ui.click(test, Probe, app, "appBar.tab.experiment");
        Ui.click(test, Probe, app, "sideBar.tab.basic");
        Ui.expandGroup(test, Probe, app, "group.experiments");
        Ui.click(test, Probe, app, "experiments.dataMore.0");
        let menu;
        tryVerify(() => {
            menu = Probe.objectsWithProperty(app, "objectName")
                .find(item => item.objectName === "experiments.load.dataFile" && Ui.exposed(item));
            return !!menu;
        }, 2000, "The existing experiment's menu shows the From file action");
        const point = Ui.clickPoint(menu);
        mouseClick(menu, point.x, point.y);
        let dialogs;
        tryVerify(() => {
            dialogs = Array.from(SettingsProof.projectFileDialogs(app, false));
            return dialogs.length === 1;
        }, 2000, "From file opens one native chooser");

        const project = Session.project;
        let between = null;
        Qt.callLater(() => {
            if (Session.project === project)
                between = { file: project.currentExperiment.dataFile, progress: loadProgress() };
        });
        verify(SettingsProof.chooseProjectLocation(dialogs[0], Probe.repoUrl(relative), false),
               "The chooser delivers the committed scan member");
        const onReturn = project.currentExperiment.dataFile;
        tryVerify(() => between !== null, 15000, "The GUI dispatches the queued event");

        tryVerify(() => Session.project.currentExperiment.dataFile === fileName, 15000,
                  "The requested measured-data file becomes the experiment's source");
        tryVerify(() => Session.project.currentExperiment.measCalcPoints().meas.length === expected.length,
                  15000, "The plot receives all positive intensity rows in the source file");
        const measured = Session.project.currentExperiment.measCalcPoints().meas;
        compare(measured[0], expected[0][1], "The plot starts with the first admitted source intensity");
        compare(measured[measured.length - 1], expected[expected.length - 1][1],
                "The plot reaches the final admitted source intensity");
        compare(onReturn, previousFile, "Accepting the chooser returns before the replacement is published");
        compare(between.file, previousFile, "The GUI event runs before the read's result reaches the experiment");
        verify(between.progress, "The window shows accessible data-loading progress during the pending read");
        verify(!loadProgress(), "The data-loading progress retires after the result reaches the window");
    }

    function test_dropped_load_reports_its_own_number_data() {
        return [{ tag: "replacement" }, { tag: "cancel" }, { tag: "remove-experiment" }];
    }

    function test_dropped_load_reports_its_own_number(data) {
        const input = Probe.repoUrl("tests/fixtures/loop_parameter_ids/line-segment");
        verify(Session.openProject(SettingsProof.copyProject(input)),
               "The data load tests start from a committed powder project");
        const project = Session.project;
        tryCompare(project, "calculating", false, 15000, "The starting calculation settles");
        const original = project.currentExperiment.dataFile;
        const firstPath = "tests/fixtures/ui_responsiveness/scan/44k_data/scan-0514_pilatus_integrated_0000.xy";
        const secondPath = "tests/fixtures/online_sources/three_points.xye";
        settlements.target = project;
        verify(settlements.valid, "A started load emits a numbered settlement");
        verify(project.loadData(0, Probe.repoUrl(firstPath)), "The first file is admitted");
        const firstId = project.startedDataLoad();
        verify(firstId > 0, "The first load gets a positive identifier");
        compare(settlements.count, 0, "The first call returns before publishing a settlement");

        if (data.tag === "replacement") {
            verify(project.loadData(0, Probe.repoUrl(secondPath)), "The replacement file is admitted");
            const secondId = project.startedDataLoad();
            verify(secondId > 0 && secondId !== firstId, "The replacement gets a different identifier");
            tryCompare(settlements, "count", 2, 15000, "Both load identifiers settle");
            compare(settlements.signalArguments, [[firstId, false], [secondId, true]],
                    "The discarded read and the applied read each get their own outcome");
            compare(project.currentExperiment.dataFile, "three_points.xye",
                    "Only the replacement file reaches the experiment");
            const rows = Probe.rows(project.currentExperiment.pattern).map(
                row => [row.x, row.intensityMeas, row.intensityMeasSu]);
            compare(rows, [[21.5, 17.25, 0.75], [22.75, 31.75, 1.25], [25.125, 23.5, 1.5]],
                    "Published measurements equal the replacement fixture's independent columns");
        } else {
            if (data.tag === "cancel")
                project.cancelDataLoad();
            else
                project.removeExperiment(0);
            tryCompare(settlements, "count", 1, 15000, "A discarded read settles once");
            compare(settlements.signalArguments, [[firstId, false]],
                    "The discarded identifier reports that no data was applied");
            if (data.tag === "cancel")
                compare(project.currentExperiment.dataFile, original, "Cancel retains the previous data file");
            else
                compare(project.experiments.count, 0, "Dropping the old read leaves its target removed");
        }
    }

    function test_recent_paths_at_start_data() {
        return [{ tag: "Université", missing: "Łódź" }, { tag: "Łódź", missing: "Université" }];
    }

    function test_recent_paths_at_start(data) {
        const root = SettingsProof.localPath(SettingsProof.emptyDirectory());
        const target = root + "/" + data.tag;
        const missing = root + "/" + data.missing;
        verify(Session.openProject(SettingsProof.copyProject(Probe.repoUrl("tests/fixtures/loop_parameter_ids/line-segment"))),
               "The Unicode save begins from an independently committed project");
        verify(Session.saveAs(Session.projectDirectoryUrl(target)), "The app saves the project under its exact Unicode name");
        Session.closeProject();
        RecentProjects.settings.recent = [missing, target];

        openWindow();
        AppState.open(AppState.Page.Project);
        Ui.expandGroup(test, Probe, app, "group.recentProjects");
        const absent = Ui.control(Probe, app, "recentProjects.status.0");
        const present = Ui.control(Probe, app, "recentProjects.status.1");
        verify(absent && present, "Both Unicode paths appear in Recent Projects when the window starts");
        compare(absent.toolTip, "Missing", "A missing Unicode folder is reported without closing the app");
        compare(present.toolTip, "Found", "The saved Unicode folder is available under its original name");
        Ui.click(test, Probe, app, "recentProjects.path.1");
        tryVerify(() => Session.hasProject, 15000, "The Found Unicode row reopens the real project");
        compare(Session.projectLocation, target, "Recent Projects opens the exact file-system path");
    }
}
