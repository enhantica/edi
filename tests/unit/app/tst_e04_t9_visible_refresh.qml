import QtQuick
import QtTest
import edi.app
import EdiAcceptance 1.0
import EdiChartReference 1.0
import EdiRefreshReference 1.0
import "UiInteraction.js" as Ui
import "E04Review.js" as Review

// The owner instruction of 2026-10-02. Counts come from Qt's real series replacements;
// new curve values come independently from crysta, not from the app's own calculation.
TestCase {
    id: test
    name: "E04T9VisibleRefresh"
    when: windowShown
    property var appWindow
    Component { id: application; Main {} }
    Component {
        id: frameDriver
        Rectangle {
            width: 2; height: 2; color: "transparent"
            NumberAnimation on x { from: 0; to: 20; duration: 200; loops: Animation.Infinite }
        }
    }
    property var animation
    function init() {
        Session.closeProject();
        appWindow = application.createObject(null);
        verify(appWindow !== null, " owner redraw gate requires the production app window");
        animation = frameDriver.createObject(appWindow.contentItem);
    }
    function cleanup() {
        RefreshObserver.disarm();
        animation.destroy();
        Session.closeProject();
        appWindow.destroy();
    }
    function renderedFrames() {
        verify(waitForPolish(appWindow, 2000), " owner redraw gate drains queued layout before observing counts");
        for (let frame = 0; frame < 4; ++frame)
            verify(waitForRendering(appWindow.contentItem), " owner redraw gate observes complete rendered frames without sleeping");
    }
    function curveProblem(chart, expected) {
        const points = ChartOracle.points(ChartOracle.object(chart, "chart.series.calc"));
        if (!points.length) return "calculated curve absent";
        let high = -Infinity;
        for (const point of points) {
            if (!isFinite(point.x)) continue;
            const row = expected.x.indexOf(point.x);
            if (row < 0 || point.y !== expected.calc[row]) return "curve differs from independently requested crysta result";
            if (isFinite(point.y)) high = Math.max(high, point.y);
        }
        return high === expected.maximum ? "" : "curve loses the independently requested maximum";
    }
    function test_one_calculation_visible_once_hidden_zero_then_latest_once_data() {
        return ChartOracle.datasets();
    }
    function test_one_calculation_visible_once_hidden_zero_then_latest_once(data) {
        Session.openProject(Probe.repoUrl(data.path));
        verify(Session.hasProject, " owner redraw gate opens the independent dataset");
        tryVerify(() => !Session.project.calculating, 15000, " owner redraw gate excludes initial project calculation from edit counts");
        Ui.click(test, Probe, appWindow, "appBar.tab.experiment");
        const experiment = ChartOracle.object(Ui.page(appWindow), "chart");
        verify(experiment !== null, " owner redraw gate creates the real Experiment chart");
        renderedFrames();
        const initialPoints = JSON.stringify(ChartOracle.points(ChartOracle.object(experiment, "chart.series.calc")));
        Ui.click(test, Probe, appWindow, "appBar.tab.analysis");
        const analysis = ChartOracle.object(Ui.page(appWindow), "chart");
        verify(analysis !== null && analysis !== experiment, " owner redraw gate keeps two distinct production charts alive");
        renderedFrames();
        const slider = Ui.control(Probe, appWindow, "parameters.slider");
        const group = Review.findGroup(Ui.page(appWindow), "group.parameters");
        verify(slider !== null && slider.enabled && group && group.selected && group.selected.name === "length_a",
            " owner redraw gate changes the real selected length-a slider");
        // SwipeView can retain visible=true on an offscreen page. Clipping geometry, rather than
        // the controller's own active/visible property, independently identifies what users see.
        verify(Ui.rendered(analysis) && !Ui.rendered(experiment), " owner redraw gate starts with Analysis onscreen and Experiment outside the clipped viewport");
        verify(RefreshObserver.arm(Session.project, analysis, experiment), " owner redraw gate attaches to actual calc background residual series and publication");
        const problems = [];
        let expected;
        for (let edit = 1; edit <= 2; ++edit) {
            const before = group.selected.value;
            // One real pointer click, in the selected slider's actual handle geometry. The two
            // nearby fractions keep inputs physical while making the final hidden result distinct.
            const handle = slider.handle ? slider.handle.width : 0;
            const fraction = .52 + edit * .01;
            const x = slider.leftPadding + handle / 2 + fraction * (slider.availableWidth - handle);
            mouseClick(slider, x, slider.height / 2);
            verify(group.selected.value !== before, " owner redraw gate one input actually changes the selected parameter");
            expected = ChartOracle.reference(data.path, group.selected.value);
            tryVerify(() => RefreshObserver.counts().publications >= edit && !Session.project.calculating, 15000,
                " owner redraw gate waits for the changed request's real publication");
            renderedFrames();
            const counts = RefreshObserver.counts();
            console.log(" owner redraw edit " + edit + " " + data.tag + " " + JSON.stringify(counts));
            for (const curve of ["Calc", "Bkg", "Resid"]) {
                if (counts["analysis" + curve] !== edit) problems.push("visible " + curve + " replacements after edit " + edit + ": " + counts["analysis" + curve]);
                if (counts["experiment" + curve] !== 0) problems.push("hidden " + curve + " replacements after edit " + edit + ": " + counts["experiment" + curve]);
            }
            if (counts.publications !== edit) problems.push("publication count after edit " + edit + ": " + counts.publications);
            if (counts.traceAvailable && (counts.starts !== edit || counts.finishes !== edit))
                problems.push("actual calculations after edit " + edit + ": " + counts.starts + "/" + counts.finishes);
            if (JSON.stringify(ChartOracle.points(ChartOracle.object(experiment, "chart.series.calc"))) !== initialPoints)
                problems.push("hidden points changed before showing the page");
            const visibleProblem = curveProblem(analysis, expected);
            if (visibleProblem) problems.push("visible edit " + edit + ": " + visibleProblem);
        }
        const beforeShow = RefreshObserver.counts();
        Ui.click(test, Probe, appWindow, "appBar.tab.experiment");
        renderedFrames();
        verify(experiment === ChartOracle.object(Ui.page(appWindow), "chart"), " owner redraw gate shows the retained hidden chart rather than a replacement instance");
        const counts = RefreshObserver.counts();
        console.log(" owner redraw shown " + data.tag + " " + JSON.stringify(counts));
        for (const curve of ["Calc", "Bkg", "Resid"]) {
            const shownReplacements = counts["experiment" + curve] - beforeShow["experiment" + curve];
            if (shownReplacements !== 1) problems.push("showing hidden " + curve + " refresh delta: " + shownReplacements);
            if (counts["analysis" + curve] !== 2) problems.push("page switch redrew previous visible " + curve);
        }
        if (counts.publications !== 2) problems.push("showing a page recalculated the model");
        const latestProblem = curveProblem(experiment, expected);
        if (latestProblem) problems.push("shown latest result: " + latestProblem);
        if (!counts.traceAvailable) problems.push("missing actual calculation-entry/exit seam: calculationStarted()/calculationFinished() on ProjectViewModel");
        else if (counts.starts !== 2 || counts.finishes !== 2) problems.push("showing a page starts another calculation");
        verify(problems.length === 0, " owner redraw gate requires one actual calculation and one visible refresh per slider change, zero hidden refreshes, then exactly one latest-result refresh on show: " + problems.join("; "));
    }
}
