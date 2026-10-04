import QtQuick
import QtQuick.Controls
import QtTest
import edi.app
import EdiAcceptance 1.0
import EdiChartReference 1.0
import EasyApplication.Gui.Style as Style
import "UiInteraction.js" as Ui
import "E04Review.js" as Review

//  gates 3-5, O1-O3. Values come from the test-only crysta oracle.
// The observer associates synchronised point state with its own frame-swap clock.
TestCase {
    id: test
    name: "E04T9PatternChart"
    when: windowShown
    property var appWindow
    property var chart
    property int savedTheme
    Component {
        id: application
        Main {}
    }
    Component {
        id: flightControl
        Rectangle {
            width: 2
            height: 2
            color: "transparent"
            NumberAnimation on x {
                from: 0
                to: 20
                duration: 200
                loops: Animation.Infinite
            }
        }
    }
    property var animation
    function init() {
        savedTheme = Style.Colors.theme;
        Style.Colors.theme = Style.Colors.Themes.LightTheme;
        Session.closeProject();
        appWindow = application.createObject(null);
        verify(appWindow !== null, " gate 5 requires the production app window");
        animation = flightControl.createObject(appWindow.contentItem);
    }
    function cleanup() {
        ChartOracle.disarm();
        animation.destroy();
        Session.closeProject();
        appWindow.destroy();
        Style.Colors.theme = savedTheme;
    }
    function open(path, page) {
        Session.openProject(Probe.repoUrl(path));
        verify(Session.hasProject, " gate 5 opens its independently declared dataset");
        Ui.click(test, Probe, appWindow, "appBar.tab." + page);
        tryVerify(() => Review.find(Ui.page(appWindow), "chart") !== null, 5000, " gate 5 the selected page shows the real chart");
        chart = Review.find(Ui.page(appWindow), "chart");
        tryVerify(() => ChartOracle.points(ChartOracle.object(chart, "chart.series.calc")).length > 0, 10000, " gate 5 waits for actual asynchronous calculated points");
        tryVerify(() => Ui.rendered(chart), 5000, " gate 5 pointer input starts on the selected rendered chart");
        for (let frame = 0; frame < 2; ++frame)
            verify(waitForRendering(appWindow.contentItem, 5000), " gate 5 layout and plot geometry settle in actual rendered frames before input");
    }
    function object(name) {
        const result = ChartOracle.object(chart, name);
        verify(result !== null, " P5 chart contract exposes " + name);
        return result;
    }
    function chooseYScale(index, label) {
        const combo = object("chart.toolbar.yscale");
        mouseClick(combo, combo.width / 2, combo.height / 2);
        tryCompare(combo.popup, "opened", true, 2000, " owner y-scale drop-down opens through real pointer input");
        const list = combo.popup.contentItem;
        tryVerify(() => list.itemAtIndex(index) !== null, 2000, " owner y-scale popup materialises the requested entry");
        const entry = list.itemAtIndex(index);
        compare(entry.text, label, " owner y-scale popup names the independently requested transformation");
        mouseClick(entry, entry.width / 2, entry.height / 2);
        tryCompare(combo, "currentIndex", index, 2000, " owner y-scale popup input selects the requested transformation");
        tryCompare(combo.popup, "opened", false, 2000, " owner y-scale popup closes after selection");
        tryCompare(combo.popup, "visible", false, 2000, " owner y-scale popup finishes its closing transition before the next real input");
    }
    function maximum(points) {
        return Math.max(...points.filter(p => isFinite(p.y)).map(p => p.y));
    }
    function corpusPages() {
        const result = [];
        ChartOracle.datasets().forEach(row => ["experiment", "analysis"].forEach(page => result.push({
                    tag: row.tag + "-" + page,
                    path: row.path,
                    page: page
                })));
        return result;
    }
    function test_series_toolbar_and_uncertainties_data() {
        return corpusPages();
    }
    function test_series_toolbar_and_uncertainties(data) {
        const expected = ChartOracle.reference(data.path);
        open(data.path, data.page);
        ["meas", "calc", "bkg", "resid"].forEach(key => {
            const points = ChartOracle.points(object("chart.series." + key));
            verify(points.length > 0, " I16 all measured and calculated category series are drawn");
            points.filter(p => isFinite(p.x)).forEach(p => {
                const r = expected.x.indexOf(p.x);
                verify(r >= 0, " gate 1 drawn x has provenance in independently loaded crysta data");
                compare(p.y, expected[key][r], " gate 1 drawn value equals independent crysta category");
            });
        });
        ["yscale", "legend", "hover", "pan", "zoom", "reset"].forEach(key => {
            const button = object("chart.toolbar." + key);
            verify(button.visible && button.width > 0 && button.height > 0, " I27 each toolbar command has a visible pointer target");
            if (key !== "yscale")
                verify(Math.abs(button.width - button.height) < 1, " I27 toolbar buttons are square");
        });
        const reset = object("chart.toolbar.reset");
        compare(reset.fontIcon, "home", " owner chart item 2 uses the Home reset icon");
        compare(object("chart.title.residual").text, "Residual", " owner chart item 4 names the drawn residual axis Residual");
        verify(chart.topMargin > 0, " owner chart margins keep a positive gap around the toolbar and x title");
        compare(chart.bottomMargin, chart.topMargin, " owner chart margins reserve the same gap below the x-title band as above the toolbar");
        compare(chart.toolbarGap, chart.topMargin, " owner chart margins reserve the same gap below and above the toolbar");
        const resetAt = reset.mapToItem(chart, 0, 0);
        const main = object("chart.view.main");
        const mainAt = main.mapToItem(chart, 0, 0);
        verify(Math.abs(resetAt.y - chart.topMargin) < 1, " owner chart margin is realised above the actual toolbar button");
        verify(Math.abs(mainAt.y + main.plotArea.y - resetAt.y - reset.height - chart.toolbarGap) < 1, " owner chart margin is realised between the toolbar button and actual top plot border");
        const title = object("chart.title.x");
        // The label is centred in its reserved title band; its normal leading
        // is distinct from the owner's equal margin outside that band.
        const titleAt = title.mapToItem(chart, 0, 0);
        verify(Math.abs(chart.height - (titleAt.y + title.height / 2 + chart.xTitleHeight / 2) - chart.bottomMargin) < 1, " owner chart margin is realised below the actual centred x-title band");
        const scale = object("chart.toolbar.yscale");
        compare(scale.count, 3, " owner y-scale drop-down retains linear, square root and log choices");
        ["linear", "square root", "log"].forEach((name, index) => compare(scale.textAt(index), name, " owner y-scale choices keep their independently declared order"));
        verify(Math.abs(scale.height - object("chart.toolbar.reset").height) < 1, " owner y-scale drop-down shares the toolbar buttons' height");
        const scaleAt = scale.mapToItem(chart, 0, 0);
        ["legend", "hover", "pan", "zoom", "reset"].forEach(key => {
            const button = object("chart.toolbar." + key);
            const point = button.mapToItem(chart, 0, 0);
            verify(scaleAt.x > point.x + button.width, " owner y-scale drop-down follows every button at the toolbar's far right");
        });
        verify(object("chart.toolbar.zoom").checked, " I27 box zoom starts active");
        verify(!object("chart.toolbar.pan").checked, " I27 pan and box zoom exclude each other");
        compare(maximum(ChartOracle.points(object("chart.series.calc"))), expected.maximum, " I18 calculated maximum survives chart decimation");
        verify(object("chart.measured") !== null, " I26 selected measured layer draws uncertainty bars and markers");
        [false, true].forEach(dark => {
            Style.Colors.theme = dark ? Style.Colors.Themes.DarkTheme : Style.Colors.Themes.LightTheme;
            const colors = dark ? {
                calc: "#ef9a9a",
                bkg: "#b0bec5",
                resid: "#c5e1a5",
                meas: "#81d4fa"
            } : {
                calc: "#f44336",
                bkg: "#607d8b",
                resid: "#8bc34a",
                meas: "#03a9f4"
            };
            ["calc", "bkg", "resid", "meas"].forEach(key => tryVerify(() => String(object("chart.series." + key).color).toLowerCase() === colors[key], 2000, " I23 Qt series colors equal independently committed light and dark palettes"));
        });
    }
    function test_pointer_ranges_and_scaled_axis_labels_data() {
        return corpusPages();
    }
    function test_pointer_ranges_and_scaled_axis_labels(data) {
        open(data.path, data.page);
        const axis = object("chart.axis.x");
        const graph = ChartOracle.graph(chart);
        const plot = ChartOracle.plot(chart);
        verify(graph !== null && plot.width > 0, " I27 pointer tests reach the actual Graphs plot area");
        const left = axis.min, right = axis.max, span = right - left;
        mouseWheel(graph, plot.x + plot.width / 4, plot.y + plot.height / 2, 0, 120);
        tryVerify(() => Math.abs(axis.min - (left + .05 * span)) < 1e-6 && Math.abs(axis.max - (left + .85 * span)) < 1e-6, 2000, " seam 19 wheel zoom keeps pointer anchor fixed and scales span by point eight");
        mouseClick(object("chart.toolbar.reset"));
        tryVerify(() => Math.abs(axis.min - left) < 1e-6 && Math.abs(axis.max - right) < 1e-6, 2000, " I27 reset restores the entire shared x range");
        mouseClick(object("chart.toolbar.pan"));
        verify(!object("chart.toolbar.zoom").checked, " I27 enabling pan switches box zoom off");
        const panStart = Math.round(plot.x + plot.width / 2);
        const panEnd = Math.round(plot.x + plot.width * .6);
        const panDistance = (panEnd - panStart) / plot.width * span;
        mousePress(graph, panStart, plot.y + plot.height / 2);
        mouseMove(graph, panEnd, plot.y + plot.height / 2);
        mouseRelease(graph, panEnd, plot.y + plot.height / 2);
        tryVerify(() => Math.abs(axis.min - (left - panDistance)) < 1e-6, 2000, " seam 19 a rightward pan shifts the range left by its integer pointer data distance");
        mouseClick(object("chart.toolbar.reset"));
        chooseYScale(1, "square root");
        const sqrtPoints = ChartOracle.points(object("chart.series.calc"));
        const expected = ChartOracle.reference(data.path);
        compare(maximum(sqrtPoints), Math.sqrt(expected.maximum), " I21 sqrt selection transforms rendered values");
        chooseYScale(2, "log");
        compare(maximum(ChartOracle.points(object("chart.series.calc"))), Math.log10(expected.maximum), " I21 log selection transforms rendered values");
        const residual = ChartOracle.points(object("chart.series.resid"));
        compare(maximum(residual), Math.max(...expected.resid.filter(v => isFinite(v))), " I21 residual stays linear under main-axis scale changes");
    }
    function test_real_slider_publication_and_requested_frame_data() {
        return ChartOracle.datasets();
    }
    function test_real_slider_publication_and_requested_frame(data) {
        open(data.path, "analysis");
        let slider;
        tryVerify(() => {
            slider = Ui.control(Probe, appWindow, "parameters.slider");
            return slider !== null && slider.enabled;
        }, 5000, " O1 latency starts from a real enabled Analysis slider");
        const selected = Review.descendants(Ui.page(appWindow)).find(item => item.selected && item.objectName === "group.parameters").selected;
        verify(selected !== null && selected.name === "length_a", " O2 requested-state reference is the selected first cell parameter");
        // Keep the pointer down so slider limits stay fixed throughout each burst.
        const baselineLength = selected.value;
        ["S1", "S2"].forEach(scenario => {
            const samples = [], calculationBaselines = [];
            for (let sample = 0; sample < 55; ++sample) {
                // Alternate two distinct physical targets; S2 starts opposite S1's final value.
                // QtTest dispatches integer mouse coordinates, so derive the reference from
                // the requested pixel before input rather than from a subpixel movement.
                const value = baselineLength + .1 * ((sample + (scenario === "S2" ? 1 : 0)) % 2 === 0 ? 1 : -1);
                const fraction = (value - slider.from) / (slider.to - slider.from);
                const handle = slider.handle ? slider.handle.width : 0;
                const x = Math.round(slider.leftPadding + handle / 2 + fraction * (slider.availableWidth - handle));
                const requested = slider.from + ((x - slider.leftPadding - handle / 2) / (slider.availableWidth - handle)) * (slider.to - slider.from);
                const expected = ChartOracle.reference(data.path, requested);
                verify(ChartOracle.arm(appWindow, chart, expected.maximum), " O2 independent frame observer attaches to actual Qt series and shared axis");
                verify(ChartOracle.publicationThreadIsGui(Session.project), " I5 observer connects directly to actual publication signal");
                ChartOracle.start();

                mousePress(slider, x, slider.height / 2);
                if (scenario === "S2") {
                    mouseMove(slider, slider.leftPadding + handle / 2 + .3 * (slider.availableWidth - handle), slider.height / 2);
                    mouseMove(slider, slider.leftPadding + handle / 2 + .7 * (slider.availableWidth - handle), slider.height / 2);
                }
                mouseMove(slider, x, slider.height / 2);
                const finalValue = selected.value;
                // Qt's handle geometry determines the exact value of real input. Compute its
                // independent reference before releasing, then use that final requested state.
                mouseRelease(slider, x, slider.height / 2);
                verify(Math.abs(finalValue - requested) < 1e-8, " O1 real pointer dispatch reaches the precomputed distinct requested slider value");
                tryVerify(() => ChartOracle.result().complete, 15000, " O2 completion is the swapped frame that synchronised the requested calculated maximum");
                if (sample === 0)
                    verify(ChartOracle.result().oldFrameAfterInput, " O2 old-frame control witnesses an obsolete frame after input before counting requested completion");
                verify(ChartOracle.guiPublication(), " I5 actual published signal is emitted on the GUI thread");
                compare(maximum(ChartOracle.points(object("chart.series.calc"))), expected.maximum, " L10 final slider position is actually presented");
                if (sample >= 5) {
                    samples.push(ChartOracle.result().latency_ms);
                    calculationBaselines.push(ChartOracle.calculationBaselineMs(data.path, requested));
                }
                const row = expected.calc.indexOf(expected.maximum);
                verify(ChartOracle.chartPixel(appWindow, chart, expected.x[row], expected.maximum, "#F44336"), " O3 grabbed final frame shows the independently requested maximum in calculated-series color");
            }
            samples.sort((a, b) => a - b);
            calculationBaselines.sort((a, b) => a - b);
            console.log(JSON.stringify({
                dataset: data.tag,
                scenario: scenario,
                samples: 50,
                warmups: 5,
                median_ms: samples[24],
                p95_ms: samples[47],
                direct_calculation_baseline_median_ms: calculationBaselines[24],
                direct_calculation_baseline_p95_ms: calculationBaselines[47],
                calculation_share: "separately timed direct-path baseline; not observed worker decomposition"
            }));
        });
    }
    function test_zoom_requested_frame_data() {
        return ChartOracle.datasets();
    }
    function test_zoom_requested_frame(data) {
        open(data.path, "analysis");
        const graph = ChartOracle.graph(chart), plot = ChartOracle.plot(chart), axis = object("chart.axis.x");
        verify(graph !== null && plot.width > 0, " S3 measurement reaches the real Graphs plot");
        const samples = [];
        const homeLeft = axis.min, homeRight = axis.max;
        const yAxis = object("chart.axis.y"), homeBottom = yAxis.min, homeTop = yAxis.max;
        for (let sample = 0; sample < 55; ++sample) {
            mouseClick(object("chart.toolbar.reset"));
            tryVerify(() => axis.min === homeLeft && axis.max === homeRight && yAxis.min === homeBottom && yAxis.max === homeTop, 5000,
                      " O2 S3 reset reaches its endpoint before the next wheel target and timing start");
            const left = axis.min, span = axis.max - left;
            verify(ChartOracle.arm(appWindow, chart, 0, true, left + .05 * span, left + .85 * span), " O2 S3 observer expects independently derived pointer axis ranges");
            ChartOracle.start();
            mouseWheel(graph, plot.x + plot.width / 4, plot.y + plot.height / 2, 0, 120);
            tryVerify(() => ChartOracle.result().complete, 5000, " O2 S3 completion is the requested range in a synchronised swapped frame");
            if (sample >= 5)
                samples.push(ChartOracle.result().latency_ms);
        }
        samples.sort((a, b) => a - b);
        console.log(JSON.stringify({
            dataset: data.tag,
            scenario: "S3",
            samples: 50,
            warmups: 5,
            median_ms: samples[24],
            p95_ms: samples[47]
        }));
    }
}
