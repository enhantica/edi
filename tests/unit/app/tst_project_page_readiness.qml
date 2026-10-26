import QtQuick
import QtQuick.Controls
import QtTest
import "UiInteraction.js" as Ui
import "RenderedTable.js" as Render
import edi.app
import EdiAcceptance 1.0
import ReportAcceptance 1.0

TestCase {
    id: test
    name: "ProjectPageReadiness"
    when: windowShown
    property var app: null
    property bool recording: false
    property double started: 0
    property var frames: []
    property var snapshots: []
    property var built: []
    property var enabledAt: []
    property var order: []
    property var tooltip: []
    property var tabs: []
    property double firstDisplay: -1
    property double firstUsable: -1
    readonly property var pages: ["project", "structure", "experiment", "analysis", "report"]
    Component {
        id: factory
        Main {}
    }
    // Keep asking the real window to draw. A timer callback alone is not frame evidence.
    Timer {
        interval: 16
        repeat: true
        running: test.recording
        onTriggered: test.app.update()
    }
    Connections {
        target: test.app
        function onFrameSwapped() {
            if (!test.recording)
                return;
            test.frames.push(Date.now() - test.started);
            test.capture(true);
        }
    }
    Repeater {
        model: test.app ? 5 : 0
        delegate: Item {
            id: watcher
            required property int index
            readonly property var loader: test.app.contentArea[index + 1]
            Connections {
                target: watcher.loader
                function onStatusChanged() {
                    if (!test.recording)
                        return;
                    if (watcher.loader.status === Loader.Ready && watcher.loader.item && test.built[index] < 0) {
                        test.built[index] = Date.now() - test.started;
                        test.order.push(index);
                    }
                    Qt.callLater(test.capture);
                }
            }
        }
    }
    function capture(painted = false) {
        if (!recording || !Session.hasProject)
            return;
        const ready = [], enabled = [], busy = [];
        for (let i = 0; i < pages.length; ++i) {
            const loader = app.contentArea[i + 1];
            const tab = tabs[i];
            const isReady = loader && loader.status === Loader.Ready && loader.item !== null;
            ready.push(Boolean(isReady));
            enabled.push(Boolean(tab && tab.enabled));
            if (tab && tab.enabled && enabledAt[i] < 0)
                enabledAt[i] = Date.now() - started;
            busy.push(Boolean(tab && Render.descendants(tab).some(item => item.visible && item.running === true && String(item).includes("BusyIndicator"))));
        }
        const status = Render.texts(app.statusBar).map(item => item.text).filter(text => /^Opening project/.test(text));
        // A page placeholder is in the page shell; do not traverse thousands of table cells per frame.
        const placeholders = [];
        let shell = [Ui.page(app)];
        for (let depth = 0; depth < 3; ++depth) {
            const next = [];
            for (const item of shell) {
                if (!item)
                    continue;
                if (item.visible && typeof item.text === "string" && /^Opening this page/.test(item.text))
                    placeholders.push(item.text);
                for (const child of item.children || [])
                    next.push(child);
            }
            shell = next;
        }
        const statusText = Render.texts(app.statusBar).map(item => item.text).join(" ");
        const bars = Render.descendants(app.statusBar).filter(item => item.visible && typeof item.fraction === "number" && typeof item.indeterminate === "boolean").map(item => ({
                    fraction: item.fraction,
                    indeterminate: item.indeterminate
                }));
        if (painted && ready[0] && firstDisplay < 0)
            firstDisplay = Date.now() - started;
        if (painted && ready[0] && !Session.project.calculating && firstUsable < 0)
            firstUsable = Date.now() - started;
        snapshots.push({
            statusText,
            bars,
            painted,
            ms: Date.now() - started,
            ready,
            enabled,
            busy,
            status,
            placeholders
        });
    }
    function begin() {
        frames = [];
        snapshots = [];
        built = [-1, -1, -1, -1, -1];
        enabledAt = [-1, -1, -1, -1, -1];
        order = [];
        tooltip = [];
        firstDisplay = -1;
        firstUsable = -1;
        started = Date.now();
        recording = true;
    }
    function runOpening(route, phase) {
        const source = Probe.repoUrl("docs/user/cli/sc-neut-tof_taurine-senju/project");
        const input = route === "folder" ? source : route === "project.edi" ? source + "/project.edi" : Probe.repoUrl("tests/fixtures/project_archive/sc-neut-tof_taurine-senju.zip");
        begin();
        const opened = route === "example" ? Session.openExample("sc-neut-tof_taurine-senju") : Session.openProject(input);
        verify(opened, "Every readiness measurement opens the independently committed taurine project");
        capture();
        // Hover an actual disabled tab while it is being prepared, without activating it.
        const report = tabs[4];
        verify(report !== null, "The actual application exposes its Report tab");
        mouseMove(report, report.width / 2, report.height / 2);
        tryVerify(() => {
            capture();
            const tip = findChild(app, "appBar.preparingToolTip");
            if (tip && tip.visible && !tooltip.includes(tip.text))
                tooltip.push(tip.text);
            return built.every(ms => ms >= 0) && enabledAt.every(ms => ms >= 0) && !Session.project.calculating;
        }, 15000, "All five actual pages finish building and their tabs become enabled without being visited");
        app.update();
        verify(waitForRendering(app.contentItem), "The readiness receipt includes the frame after the final page is built");
        capture();
        recording = false;
        console.log("PAGE_READINESS_EVIDENCE " + JSON.stringify({
            route,
            phase,
            frames,
            snapshots,
            built,
            enabledAt,
            order,
            tooltip,
            firstDisplay,
            firstUsable
        }));
    }
    function test_routes_data() {
        return ["folder", "project.edi", "zip", "example"].map(route => ({
                    tag: route,
                    route
                }));
    }
    function test_routes(data) {
        app = factory.createObject(null, {
            width: Math.min(1280, SettingsProof.screen().width),
            height: Math.min(720, SettingsProof.screen().height - 60),
            visible: true
        });
        verify(app !== null, "Readiness gates use the actual application Main window");
        app.requestActivate();
        tryCompare(app, "active", true, 2000, "Readiness gates deliver input to the actual active window");
        // Display Project before the measured request, as in the retained baseline.
        const start = Ui.control(Probe, app, "home.start");
        if (start)
            mouseClick(start, start.width / 2, start.height / 2);
        let tab;
        tryVerify(() => {
            tab = Ui.control(Probe, app, "appBar.tab.project");
            return tab && tab.enabled && Ui.clickPoint(tab) !== null;
        }, 4000, "The initial Project page is actionable before opening");
        mouseClick(tab, tab.width / 2, tab.height / 2);
        app.update();
        verify(waitForRendering(app.contentItem), "Opening starts from a real rendered application frame");
        tabs = pages.map(name => Ui.control(Probe, app, "appBar.tab." + name));
        verify(tabs.every(tab => tab !== null), "Every measured tab is the actual application tab");
        runOpening(data.route, "cold");
        runOpening(data.route, "warm");
    }
    function cleanup() {
        recording = false;
        if (app) {
            app.close();
            app.destroy();
        }
        app = null;
        Session.closeProject();
    }
}
