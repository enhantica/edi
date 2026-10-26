// SPDX-License-Identifier: BSD-3-Clause
import QtQuick
import QtTest
import edi.app
import EdiAcceptance 1.0
import ReportAcceptance 1.0
import "../../unit/app/RenderedTable.js" as Render
import "../../unit/app/UiInteraction.js" as Ui
import "../../unit/app/ApprovedPalette.js" as Approved
import "../../fixtures/scan_views/input.js" as Input

Item {
    Component { id: factory; Main { visible: true; width: 1400; height: 900 } }
    TestCase {
        id: test
        name: "HiddenScanRedraws"
        when: windowShown
        property var app: null
        property var charts: []
        property url projectRoot
        function cleanup() {
            if (app) { app.close(); app.destroy(); }
            app = null; charts = [];
            Session.closeProject();
            Preferences.resetToDefaults();
        }
        function frame() {
            app.update();
            verify(waitForPolish(app.contentItem) && waitForRendering(app.contentItem), "Hidden-work observations follow actual completed application frames");
        }
        function settle() {
            tryVerify(() => !Ui.moving(app.contentItem), 3000, "Page and tab transitions finish before hidden-work counters are observed");
            frame();
        }
        function page(name) {
            return Render.descendants(app.contentItem).find(item => item.pageName === name);
        }
        function show(pageName, mode) {
            Ui.click(test, Probe, app, "appBar.tab." + pageName);
            settle();
            const tab = Array.from(page(pageName).mainTabs).find(item => item.text === (mode === "map" ? "Map" : "Stacked"));
            verify(tab !== undefined && tab.enabled, "Each real page offers the requested scan-view tab");
            Ui.click(test, Probe, app, tab.objectName);
            settle();
            const result = Render.descendants(page(pageName)).find(item => item.objectName === "scanView." + mode && item.shown && item.visible);
            verify(result !== undefined, "The redraw gate reaches the actual shown page-owned scan chart");
            tryCompare(result.scan, "loaded", 2, 8000, "Both independently authored datasets populate every scan view");
            frame();
            return result;
        }
        function traceLayer(chart) {
            const result = findChild(chart, "scanView." + chart.mode + ".layer");
            verify(result !== null && typeof result.traceBuildCount === "number", "Every page-owned scan layer exposes its actual reduced-dataset build count");
            return result;
        }
        function dataText(shape) {
            const knots = shape === "left" ? [[10,0], [20,255], [30,255], [40,0], [65,0], [80,0]] : shape === "middle" ? [[10,0], [25,0], [35,255], [45,255], [55,0], [80,0]] : [[10,0], [25,0], [40,0], [55,255], [65,255], [80,0]];
            return knots.map(point => point[0] + " " + (point[1] === 0 ? 10 : point[1]) + " 1").join("\n") + "\n";
        }
        function reload(shape) {
            for (let index = 0; index < 2; ++index) {
                const name = "observations-" + index + ".xy";
                verify(SettingsProof.write(projectRoot, name, dataText(shape)), "The data-change stimulus writes independently specified measured points to a private file");
                verify(Session.project.loadData(index, Qt.resolvedUrl(String(projectRoot) + "/" + name)), "Actual data loading replaces a joint experiment's measured points");
            }
            tryVerify(() => !Session.project.calculating, 15000, "The real measured-data edit and its calculation settle before the hidden view is exposed");
            compare(Session.project.currentExperiment.pattern.count, 6, "Every actual reloaded experiment retains all six independently supplied positive measured knots");
            frame();
        }
        function work() { return charts.map(chart => traceLayer(chart).traceBuildCount); }
        function assertHiddenUnchanged(before, target) {
            const wanted = charts.indexOf(target);
            const order = [wanted].concat(charts.map((chart, index) => index).filter(index => index !== wanted));
            for (const index of order) {
                verify(!charts[index].shown, "The hidden-work scenario leaves every warmed scan view unshown");
                compare(traceLayer(charts[index]).traceBuildCount, before[index], "A Stacked or Map view hidden by its page or tab performs no reduction or trace build on dataset changes");
            }
        }
        function sample(image, chart, xValue, yValue) {
            const drawing = traceLayer(chart), axes = findChild(chart, "scanView." + chart.mode + ".axes");
            const x = (xValue - axes.axisX.min) / (axes.axisX.max - axes.axisX.min) * drawing.width;
            const y = (axes.axisY.max - yValue) / (axes.axisY.max - axes.axisY.min) * drawing.height;
            const at = drawing.mapToItem(app.contentItem, x, y);
            const px = Math.floor(at.x * image.width / app.contentItem.width), py = Math.floor(at.y * image.height / app.contentItem.height);
            verify(Number.isFinite(px) && Number.isFinite(py) && px >= 0 && py >= 0 && px < image.width && py < image.height, "Independent current-point pixel coordinates are inside the actual captured plot: " + JSON.stringify({xValue, yValue, px, py, axes: [axes.axisX.min, axes.axisX.max, axes.axisY.min, axes.axisY.max], drawing: [drawing.width, drawing.height], image: [image.width, image.height]}));
            return image.pixel(px, py);
        }
        function sameRgb(actual, expected, tolerance) {
            return ["r", "g", "b"].every(channel => Math.abs(actual[channel] - expected[channel]) <= tolerance);
        }
        function assertLatestPixels(chart, shape) {
            const image = grabImage(app.contentItem), drawing = traceLayer(chart);
            const left = shape === "left";
            if (chart.mode === "map") {
                const colours = JSON.parse(SettingsProof.repoText("tests/fixtures/scan_views/viridis.json")).samples;
                const rgb = index => {
                    const values = colours.find(sample => sample.index === index).rgb;
                    return Qt.rgba(values[0], values[1], values[2], 1);
                };
                for (const row of [0, 1]) {
                    verify(sameRgb(sample(image, chart, left ? 25 : 60, row), rgb(255), 3 / 255), "Every newly shown Map band draws the latest independently specified plateau at the frozen Viridis high colour");
                    verify(sameRgb(sample(image, chart, left ? 60 : 25, row), rgb(0), 3 / 255), "Every newly shown Map band has no retained pre-hide peak at its former x coordinate");
                }
            } else {
                const palette = Approved.colours(SettingsProof, "ediNatural", "measured", 2, chart.colors.isDarkPalette);
                for (let row = 0; row < 2; ++row) {
                    const expected = Qt.rgba(parseInt(palette[row].slice(1,3),16)/255, parseInt(palette[row].slice(3,5),16)/255, parseInt(palette[row].slice(5,7),16)/255, 1);
                    const y = row / 2 + .25;
                    let current = false, stale = false;
                    for (let dy = -3; dy <= 3; ++dy) {
                        const shift = dy / drawing.height;
                        current = current || sameRgb(sample(image, chart, left ? 15 : 47.5, y + shift), expected, .09);
                        stale = stale || sameRgb(sample(image, chart, left ? 47.5 : 15, y + shift), expected, .09);
                    }
                    verify(current, "Every newly shown Stacked trace has ink on the latest independently specified rising edge");
                    verify(!stale, "Every newly shown Stacked trace removes the pre-hide rising edge rather than drawing cached old points");
                }
            }
        }
        function test_hidden_views_data() {
            const rows = [];
            for (const page of ["experiment", "analysis"])
                for (const mode of ["stacked", "map"]) rows.push({tag: page + "-" + mode, page, mode});
            return rows;
        }
        function test_hidden_views(data) {
            Preferences.resetToDefaults();
            Preferences.chartHighlightSelected = false;
            Preferences.scanRenderer = "gpu";
            Preferences.scanStackedPalette = "ediNatural";
            Preferences.scanMapColours = "viridis";
            Preferences.scanMapSmooth = false;
            Preferences.scanMapReversed = false;
            Preferences.scanStackedOffset = 100;
            Preferences.scanStackedSize = 0;
            app = factory.createObject(null);
            verify(app !== null, "The redraw rule is exercised in the actual Main application");
            app.requestActivate();
            tryCompare(app, "active", true, 2000, "Actual page and tab navigation reaches the active window");
            projectRoot = SettingsProof.copyProject(Probe.repoUrl("docs/user/cli/pd-neut-tof_ferrite-austenite-beer_joint/project"));
            Input.joint(SettingsProof, projectRoot, false, "cwl");
            verify(Session.openProject(projectRoot), "The hidden-redraw gate opens an independent two-experiment joint project");
            Session.project.patternDSpacing = false;
            reload("left");
            for (const name of ["experiment", "analysis"])
                for (const mode of ["stacked", "map"])
                    charts.push(show(name, mode));
            compare(new Set(charts).size, 4, "All four actual Stacked and Map views are instantiated and warmed on both pages");
            let target = show(data.page, data.mode);
            assertLatestPixels(target, "left");
            for (const context of ["page", "tab"]) {
                if (context === "page") Ui.click(test, Probe, app, "appBar.tab.home");
                else Ui.click(test, Probe, app, "mainArea." + data.page + ".tab." + (data.page === "experiment" ? "chart" : "fitting"));
                settle();
                const before = work();
                reload("middle");
                assertHiddenUnchanged(before, target);
                reload(context === "page" ? "right" : "left");
                assertHiddenUnchanged(before, target);
                // The view is still hidden after more completed frames than the edits require.
                frame(); frame();
                assertHiddenUnchanged(before, target);
                target = show(data.page, data.mode);
                const targetIndex = charts.indexOf(target);
                verify(targetIndex >= 0, "Reopening uses the warmed production view rather than replacing it with an empty one");
                const after = work();
                for (let index = 0; index < charts.length; ++index)
                    compare(after[index] - before[index], index === targetIndex ? 2 : 0, "Only the newly shown view builds exactly once per current dataset; all other hidden scan layers remain idle");
                assertLatestPixels(target, context === "page" ? "right" : "left");
                frame(); frame();
                compare(traceLayer(target).traceBuildCount, after[targetIndex], "Further unchanged frames do not repeat the deferred trace build");
                console.log("HIDDEN_REDRAW " + JSON.stringify({page: data.page, mode: data.mode, context, before, after, datasets: 2}));
            }
        }
    }
}
