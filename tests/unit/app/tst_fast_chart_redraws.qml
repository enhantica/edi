// SPDX-License-Identifier: BSD-3-Clause
import QtQuick
import QtQuick.Controls
import QtQuick.Window
import QtTest
import edi.app
import EdiAcceptance 1.0
import ChartBackendAcceptance 1.0
import ReportAcceptance 1.0
import EasyApplication.Gui.Globals as Globals
import EasyApplication.Gui.Style as Style
import "RenderedTable.js" as Render
import "ApprovedPalette.js" as Approved
import "UiInteraction.js" as Ui
import "../../fixtures/scan_views/input.js" as Input
import "../../system/app/RendererPath.js" as RendererPath

Item {
    id: surface
    width: 1280
    height: 768
    Component {
        id: scanFactory
        ScanViewChart {
            width: 1100
            height: 650
            shown: false
        }
    }
    Component {
        id: appFactory
        Main {
            visible: true
        }
    }
    Component {
        id: emptyFactory
        EmptyStateLabel {
            text: "No structure loaded"
        }
    }
    TestCase {
        id: test
        name: "FastChartRedraws"
        when: windowShown
        property var chart: null
        property var app: null
        property int frames: 0
        property var adaptiveDraws: []
        Connections {
            target: Session.project ? Session.project.fit : null
            function onScanShownFileChanged() {
                const fit = Session.project.fit;
                if (fit.running && fit.scanShownFile)
                    test.adaptiveDraws.push({file: fit.scanShownFile, ms: Date.now()});
            }
        }
        Connections {
            target: surface.Window.window
            function onFrameSwapped() {
                test.frames += 1;
            }
        }
        function cleanup() {
            if (Session.project && Session.project.fit.running) {
                Session.project.fit.cancel();
                tryCompare(Session.project.fit, "running", false, 10000, "The chart actor stops its real scan before closing the project");
            }
            if (chart && !app)
                chart.destroy();
            chart = null;
            if (app) {
                app.close();
                app.destroy();
            }
            app = null;
            Session.closeProject();
            Preferences.resetToDefaults();
        }
        function settled(item) {
            if (app)
                app.update();
            else
                surface.Window.window.update();
            verify(waitForPolish(item) && waitForRendering(item), "Chart acceptance observes a completed production frame");
        }
        function open(mode, count = 3) {
            Preferences.resetToDefaults();
            Style.Colors.theme = Style.Colors.LightTheme;
            const location = SettingsProof.copyProject(Qt.resolvedUrl("../../fixtures/scan_template/project"));
            Input.dense(SettingsProof, location, false, count);
            for (let row = 0; row < count; ++row) {
                const text = "XYDATA independent triangle\nTEMP " + (100 + row * 7) + "\n10 0 1\n40 255 1\n80 0 1\n";
                verify(SettingsProof.write(location, "experiments/d20_scan/row_" + String(row).padStart(3, "0") + ".dat", text), "The placement fixture writes independently specified unequal x knots");
            }
            verify(Session.openProject(location), "Chart acceptance opens its private analytic scan project");
            chart = scanFactory.createObject(surface, {
                project: Session.project,
                mode: mode
            });
            verify(chart !== null, "Chart acceptance creates the production scan view");
            chart.shown = true;
            tryCompare(chart.scan, "loaded", count, 8000, "Every independently generated pattern is loaded before observing placement");
            settled(chart);
        }
        function named(name) {
            const found = findChild(chart, "scanView." + chart.mode + "." + name);
            verify(found !== null, "The production scan view exposes its existing " + name + " control");
            return found;
        }
        function choose(box, value) {
            const entries = Array.from(box.model);
            const index = entries.findIndex(entry => String(entry).replace(/\s/g, "").toLowerCase() === value.toLowerCase());
            verify(index >= 0, "The actual selector offers the required relative choice " + value);
            box.currentIndex = index;
            box.activated(index);
            settled(chart);
        }
        function closeEnough(actual, expected, message) {
            verify(Number.isFinite(actual) && Math.abs(actual - expected) < 0.00001, "Relative placement matches the independent formula: " + message + "; actual=" + actual + "; expected=" + expected);
        }
        function test_gpu_backend() {
            open("stacked");
            const layer = named("layer");
            verify(ChartBackendProof.gpu(layer), "The real chart capture runs on an actual GPU rendering API");
            ChartBackendProof.watch(layer);
            settled(layer);
            tryVerify(() => ChartBackendProof.facts(layer).api !== undefined, 1000, "The default-renderer witness reads Qt's actual backend after a completed frame");
            const observed = ChartBackendProof.facts(layer);
            if (observed.api === "OpenGL")
                verify(observed.renderer.length > 0, "The default-renderer witness reads Qt's actual OpenGL renderer");
            RendererPath.check(test, ChartBackendProof, layer, RendererPath.effectiveGpu(observed, "auto"), () => settled(layer));
        }
        function test_adaptive_is_retained() {
            Preferences.resetToDefaults();
            const location = SettingsProof.copyProject(Qt.resolvedUrl("../../../docs/user/cli/pd-neut-cwl_cosio-d20_scan-162f/project"));
            verify(Session.openProject(location), "Adaptive acceptance opens a private copy of the saved 162-file scan");
            const win = window();
            Ui.click(test, Probe, win, "appBar.tab.analysis");
            Ui.click(test, Probe, win, "sideBar.tab.settings");
            Ui.expandGroup(test, Probe, win, "group.patternUpdates");
            const selector = Ui.control(Probe, win, "analysis.patternUpdates");
            verify(selector !== null, "The Analysis Settings page retains its real pattern-update selector");
            Ui.scrollIntoView(selector);
            Ui.click(test, Probe, win, "analysis.patternUpdates");
            tryCompare(selector.popup, "opened", true, 1000, "The pattern-update choices open through actual pointer input");
            const choices = Array.from(selector.model);
            const adaptive = choices.indexOf("Adaptive"), every = choices.indexOf("Every pattern");
            verify(adaptive >= 0 && every >= 0 && adaptive !== every, "Adaptive remains a distinct selectable choice alongside Every pattern");
            mouseMove(win.contentItem, win.width - 1, win.height - 1);
            verify(SettingsProof.key(selector, Qt.Key_Home), "The open pattern-update selector receives Home through its actual window");
            verify(SettingsProof.key(selector, Qt.Key_Return), "The open pattern-update selector commits Every pattern through real keyboard input");
            tryCompare(Session.project.fit, "patternUpdates", every, 1000, "Real keyboard input can choose Every pattern before returning to Adaptive");
            Ui.click(test, Probe, win, "analysis.patternUpdates");
            mouseMove(win.contentItem, win.width - 1, win.height - 1);
            verify(SettingsProof.key(selector, Qt.Key_Home), "The reopened pattern-update selector receives Home through its actual window");
            for (let i = 0; i < adaptive; ++i)
                verify(SettingsProof.key(selector, Qt.Key_Down), "The open pattern-update selector receives each real navigation key");
            verify(SettingsProof.key(selector, Qt.Key_Return), "The open pattern-update selector commits Adaptive through real keyboard input");
            tryCompare(selector, "currentText", "Adaptive", 1000, "Real keyboard input selects Adaptive after Every pattern");
            tryCompare(Session.project.fit, "patternUpdates", adaptive, 1000, "The selected Adaptive choice reaches the actual fit worker");
            tryCompare(Preferences, "scanPatternUpdates", adaptive, 1000, "Adaptive remains a machine setting");
            const project = Session.project, fit = project.fit;
            tryVerify(() => !project.calculating && Probe.datasetReady(project), 10000, "The saved scan's first pattern is ready before starting Adaptive");
            compare(fit.scanTotal, 162, "Adaptive behaviour uses every independently saved input file");
            adaptiveDraws = [];
            fit.start();
            tryCompare(fit, "running", true, 1000, "Adaptive starts a real sequential fit");
            tryCompare(fit, "running", false, 65000, "Adaptive completes without waiting for every pattern drawing");
            compare(fit.scanFitted, 162, "Adaptive retains all fitted files rather than dropping scientific work");
            compare(fit.outcome, "success", "The full Adaptive scan completes successfully");
            verify(adaptiveDraws.length >= 2 && adaptiveDraws.length < 162, "Adaptive draws changing files during a fast scan and coalesces intermediate files");
            const files = adaptiveDraws.map(row => row.file);
            verify(new Set(files).size === files.length, "Adaptive never replays an older drawn scan file");
            verify(files.every((file, index) => index === 0 || files[index - 1] < file), "Adaptive follows the saved scan's independent ascending filename order");
            for (let i = 1; i < adaptiveDraws.length; ++i)
                verify(adaptiveDraws[i].ms - adaptiveDraws[i - 1].ms >= 500, "ADR-0029 keeps at least half a second between live Adaptive pattern drawings");
            tryCompare(project, "currentExperimentIndex", 161, 10000, "Adaptive still settles on the last independently enumerated scan file");
            tryVerify(() => !project.calculating && Probe.datasetReady(project), 10000, "The final Adaptive pattern finishes loading after the scan ends");
            settled(win.contentItem);
        }
        function test_placement_data() {
            return [1, 3, 324].map(n => ({
                        tag: String(n),
                        n: n
                    }));
        }
        function test_placement(data) {
            open("stacked", data.n);
            const offset = named("toolbar.offset"), height = named("toolbar.height");
            compare(String(offset.currentText).replace(/\s/g, ""), "10%", "The offset defaults to ten percent of one trace's height");
            compare(String(height.currentText).toLowerCase(), "fit", "The relative height defaults to Fit");
            const layer = named("layer"), axes = named("axes");
            for (let percent = 0; percent <= 100; percent += 10) {
                choose(offset, percent + "%");
                choose(height, "Fit");
                closeEnough(axes.axisY.min, 0, "The unzoomed Stacked axis starts at zero plot share");
                closeEnough(axes.axisY.max, 1, "The unzoomed Stacked axis ends at one plot share");
                const expectedHeight = 1 / (1 + (data.n - 1) * percent / 100);
                for (let i = 0; i < data.n; ++i) {
                    closeEnough(layer.rowOf(i), i * expectedHeight * percent / 100, "Stack baselines obey the closed-form relative offset");
                    closeEnough(layer.peakOf(i) - layer.rowOf(i), expectedHeight, "Each independently equal triangle has exactly the Fit height");
                    if (percent === 100 && i > 0)
                        verify(layer.peakOf(i - 1) <= layer.rowOf(i) + 0.00001, "At full offset adjacent traces have no vertical overlap");
                }
                closeEnough(layer.peakOf(data.n - 1), axes.axisY.max, "Fit places the whole stack's top exactly at the plot top");
                for (let fixed = 10; fixed <= 100; fixed += 10) {
                    choose(height, fixed + "%");
                    for (const i of [0, data.n - 1]) {
                        closeEnough(layer.rowOf(i), i * fixed / 100 * percent / 100, "A fixed height retains the independent relative baseline spacing");
                        closeEnough(layer.peakOf(i) - layer.rowOf(i), fixed / 100, "A fixed relative height is a fraction of the unzoomed plot height");
                    }
                }
            }
        }
        function test_highlight_data() {
            return ["stacked", "map"].map(mode => ({
                        tag: mode,
                        mode: mode
                    }));
        }
        function test_highlight(data) {
            open(data.mode);
            const toggle = named("toolbar.highlight");
            verify(Preferences.chartHighlightSelected && toggle.checked, "Powder uses the single-crystal highlight setting, enabled by default");
            const layer = named("layer"), axes = named("axes");
            Session.project.currentExperimentIndex = 1;
            if (data.mode === "stacked") {
                choose(named("toolbar.offset"), "100%");
                choose(named("toolbar.height"), "Fit");
            }
            settled(chart);
            const before = grabImage(layer);
            mouseClick(toggle, toggle.width / 2, toggle.height / 2);
            tryCompare(Preferences, "chartHighlightSelected", false, 1000, "Actual toolbar input writes the one shared highlight preference");
            settled(chart);
            const equal = grabImage(layer);
            verify(!before.equals(equal), "Disabling highlight changes actual rendered ink rather than only a preference");
            const background = chart.colors.chartBackground;
            function sample(image, x, y) {
                return image.pixel(Math.floor(x * image.width / layer.width), Math.floor(y * image.height / layer.height));
            }
            function distance(colour) {
                return Math.sqrt(["r", "g", "b"].reduce((sum, channel) => sum + Math.pow(colour[channel] - background[channel], 2), 0));
            }
            for (let row = 0; row < 3; ++row) {
                const level = data.mode === "map" ? chart.scan.rowOf(row) : layer.peakOf(row);
                const py = (axes.axisY.max - level) / (axes.axisY.max - axes.axisY.min) * layer.height;
                const px = (40 - axes.axisX.min) / (axes.axisX.max - axes.axisX.min) * layer.width;
                let best = null;
                for (let dy = -3; dy <= 3; ++dy) {
                    const y = Math.max(2, Math.min(layer.height - 3, Math.round(py) + dy));
                    const ink = distance(sample(equal, px, y));
                    if (best === null || ink > best.ink)
                        best = {
                            y: y,
                            ink: ink
                        };
                }
                verify(best !== null && best.ink > .05, "Every independently supplied pattern has actual visible ink with highlight disabled");
                const ratio = distance(sample(before, px, best.y)) / best.ink;
                if (row === 1)
                    verify(ratio > .85 && ratio < 1.15, "Highlight retains the selected dataset's full rendered colour");
                else
                    verify(ratio > .12 && ratio < .5, "Highlight blends every other dataset toward the background to about thirty percent");
            }
            if (data.mode === "stacked") {
                choose(named("toolbar.offset"), "0%");
                mouseClick(toggle, toggle.width / 2, toggle.height / 2);
                tryCompare(Preferences, "chartHighlightSelected", true, 1000, "Real toolbar input restores highlighting for the overlap witness");
                settled(chart);
                const hex = Approved.colours(SettingsProof, "ediNatural", "measured", 3, false)[1];
                const expected = [1, 3, 5].map(start => parseInt(hex.substr(start, 2), 16) / 255);
                const x = (30 - axes.axisX.min) / (axes.axisX.max - axes.axisX.min) * layer.width;
                const peak = layer.peakOf(1), base = layer.rowOf(1), value = base + (peak - base) * 2 / 3;
                const y = (axes.axisY.max - value) / (axes.axisY.max - axes.axisY.min) * layer.height;
                const overlap = grabImage(layer);
                let error = Infinity;
                for (let dy = -3; dy <= 3; ++dy) {
                    const pixel = sample(overlap, x, Math.max(1, Math.min(layer.height - 2, y + dy)));
                    error = Math.min(error, Math.max(...["r", "g", "b"].map((channel, index) => Math.abs(pixel[channel] - expected[index]))));
                }
                verify(error <= 3 / 255, "With fully overlapping traces the selected middle dataset is drawn on top in its independently frozen palette colour");
                mouseClick(toggle, toggle.width / 2, toggle.height / 2);
                tryCompare(Preferences, "chartHighlightSelected", false, 1000, "The overlap witness restores equal-dataset rendering before row selection");
                choose(named("toolbar.offset"), "100%");
            }
            compare(findChild(chart, "scanView." + data.mode + ".current"), null, "The retired selected-pattern rectangle has no remaining runtime instance");
            Session.project.currentExperimentIndex = 1;
            settled(chart);
            const label = named("rowLabel.1");
            const bold = Render.texts(label).find(item => item.font.bold);
            verify(bold !== undefined, "With highlight off the selected dataset retains its bold row label");
            const pointer = named("pointer");
            const row = data.mode === "map" ? chart.scan.rowOf(2) : layer.rowOf(2);
            const y = (axes.axisY.max - row) / (axes.axisY.max - axes.axisY.min) * pointer.height;
            mouseClick(pointer, pointer.width * .3, Math.max(1, Math.min(pointer.height - 1, y - 1)));
            tryCompare(Session.project, "currentExperimentIndex", 2, 1000, "Actual plot input selects the dataset at its independently observed row");
        }
        function combo(item) {
            return typeof item.currentIndex === "number" && typeof item.currentText === "string" && item.model !== undefined;
        }
        function controls(root) {
            return Render.descendants(root).filter(item => item.visible && item.width > 0 && item.height > 0 && typeof item.toolTip === "string" && (combo(item) || (typeof item.checked === "boolean" && typeof item.fontIcon === "string")));
        }
        function pageBody(name) {
            return Render.descendants(app.contentItem).find(item => item.pageName === name);
        }
        function test_toolbar_data() {
            let rows = [];
            for (const page of ["experiment", "analysis"])
                for (const mode of ["pattern", "stacked", "map"])
                    for (const width of [1200, 740, 420])
                        rows.push({
                            tag: page + "-" + mode + "-" + width,
                            page: page,
                            mode: mode,
                            width: width
                        });
            return rows;
        }
        function test_toolbar(data) {
            open("stacked");
            chart.destroy();
            chart = null;
            const win = window();
            Ui.click(test, Probe, win, "appBar.tab." + data.page);
            tryVerify(() => pageBody(data.page) && pageBody(data.page).current && !Ui.moving(win.contentItem), 3000, "The toolbar witness reaches the actual settled chart page");
            const body = pageBody(data.page), title = data.mode[0].toUpperCase() + data.mode.slice(1);
            const tab = Array.from(body.mainTabs).find(item => item.text === title);
            verify(tab !== undefined && tab.enabled, "Every chart page offers the required " + title + " view");
            Ui.click(test, Probe, win, tab.objectName);
            tryCompare(tab, "checked", true, 1000, "Real tab input exposes the production toolbar");
            tryVerify(() => !Ui.moving(win.contentItem), 2000, "The chart tab finishes moving before toolbar observation");
            const targetName = data.mode === "pattern" ? "chart" : "scanView." + data.mode;
            chart = Render.descendants(body).find(item => item.objectName === targetName && item.visible && item.shown);
            verify(chart !== undefined && chart !== null, "Toolbar acceptance observes the actual page's live chart instance");
            const chartHeight = chart.height;
            chart.anchors.fill = null;
            chart.width = data.width;
            chart.height = chartHeight;
            tryVerify(() => Math.abs(chart.width - data.width) <= 1, 1000, "The production chart receives the requested toolbar viewport width");
            settled(chart);
            const items = controls(chart).filter(item => String(item.objectName).includes("toolbar."));
            verify(items.length >= 6, "Toolbar grouping observes all production controls, including selectors and buttons; observed=" + JSON.stringify(items.map(item => item.objectName)));
            const lines = {};
            for (const item of items) {
                const point = item.mapToItem(chart, 0, 0), y = Math.round(point.y);
                if (!lines[y])
                    lines[y] = [];
                lines[y].push({
                    left: point.x,
                    right: point.x + item.width,
                    combo: combo(item)
                });
                verify(point.x >= 0 && point.x + item.width <= chart.width + 1, "Every whole toolbar control stays inside the chart");
            }
            const ys = Object.keys(lines).map(Number).sort((a, b) => a - b);
            if (ys.length > 1) {
                for (const y of ys.slice(0, -1))
                    verify(lines[y].every(item => item.combo), "Every wrapped line above the last contains only comboboxes");
                verify(lines[ys[ys.length - 1]].every(item => !item.combo), "Wrapped buttons occupy the final line below every combobox");
            }
            const plot = data.mode === "pattern" ? findChild(chart, "chart.frame.main") : findChild(chart, "scanView." + data.mode + ".layer");
            verify(plot !== null, "Toolbar centring is measured against the actual production plot");
            const centre = plot.mapToItem(chart, plot.width / 2, 0).x;
            for (const y of ys) {
                const row = lines[y];
                const left = Math.min(...row.map(item => item.left)), right = Math.max(...row.map(item => item.right));
                const margin = AppSizes.mainAreaMargin;
                const expected = Math.max(margin + (right - left) / 2, Math.min(chart.width - margin - (right - left) / 2, centre));
                verify(Math.abs((left + right) / 2 - expected) <= 1, "Each actual toolbar line is horizontally centred above the plot");
            }
            if (data.width === 1200)
                compare(ys.length, 1, "A wide chart puts all toolbar controls on one centred line");
            if (data.width === 420)
                verify(ys.length >= 3, "A narrow chart wraps the comboboxes onto multiple lines above the buttons");
        }
        function test_cache_and_pacing_data() {
            return ["stacked", "map"].map(mode => ({
                        tag: mode,
                        mode: mode
                    }));
        }
        function test_cache_and_pacing(data) {
            open(data.mode);
            const layer = named("layer");
            verify(typeof layer.traceBuildCount === "number" && typeof layer.redrawCount === "number", "The real renderer exposes trace-work and rendered-update observations");
            const traces = layer.traceBuildCount;
            chart.width += 37;
            settled(chart);
            verify(layer.traceBuildCount > traces, "Changing the plot width positively invalidates the real reduced trace cache");
            const cached = layer.traceBuildCount, draws = layer.redrawCount, startFrames = frames;
            for (let i = 0; i < 31; ++i) {
                if (data.mode === "map")
                    Preferences.scanMapReversed = !Preferences.scanMapReversed;
                else {
                    Preferences.scanStackedReversed = !Preferences.scanStackedReversed;
                    Preferences.scanStackedPalette = chart.stackedChoices[i % chart.stackedChoices.length];
                }
                Preferences.chartHighlightSelected = !Preferences.chartHighlightSelected;
                Session.project.currentExperimentIndex = i % 3;
                if (data.mode === "stacked") {
                    const offset = named("toolbar.offset"), height = named("toolbar.height");
                    offset.activated(i % 11);
                    height.activated(i % 11);
                }
            }
            settled(chart);
            compare(layer.traceBuildCount, cached, "Colour reversal and highlight never recompute a reduced trace");
            verify(layer.redrawCount > draws, "A changed style actually redraws the renderer");
            verify(layer.redrawCount - draws <= frames - startFrames, "Many synchronous changes redraw at most once per observed frame");
        }
        function test_pages_at_minimum_data() {
            return ["home", "project", "structure", "experiment", "analysis", "report"].map((page, index) => ({
                        tag: page,
                        page: page,
                        index: index
                    }));
        }
        function test_pages_at_minimum(data) {
            open("stacked");
            chart.destroy();
            chart = null;
            const win = window();
            verify(win.minimumWidth >= win.appBarCentralTabs.width && win.minimumHeight > 2 * AppSizes.toolbarControlSize, "Every-page reachability uses the production supported minimum");
            win.width = win.minimumWidth;
            win.height = win.minimumHeight;
            Ui.click(test, Probe, win, "appBar.tab." + data.page);
            tryVerify(() => pageBody(data.page) && pageBody(data.page).current, 2000, "The minimum-size witness reaches the actual selected workflow page");
            tryVerify(() => !Ui.moving(win.contentItem), 2000, "Page movement finishes before minimum-size geometry is inspected");
            verify(waitForPolish(win.contentItem) && waitForRendering(win.contentItem), "Every page at exactly the minimum has a completed frame");
            const current = pageBody(data.page), image = grabImage(win.contentItem);
            verify(current !== undefined && current !== null && current.current && image.width > 0, "Every real page produces a minimum-size capture");
            const fields = Render.descendants(current).filter(item => item.visible && item.width > 0 && item.height > 0 && (combo(item) || (typeof item.cursorPosition === "number" && typeof item.readOnly === "boolean") || item.objectName.startsWith("group.")) && Ui.inPane(item));
            if (data.index > 0)
                verify(fields.length > 0, "Loaded workflow pages retain reachable real inputs at the minimum");
            for (const field of fields) {
                Ui.scrollIntoView(field);
                const at = field.mapToItem(win.contentItem, 0, 0);
                verify(at.x >= -1 && at.x + field.width <= win.width + 1, "No actual input field or whole group is clipped horizontally at the minimum");
                verify(Ui.exposed(field), "Vertical scrolling reaches each actual input at the minimum");
            }
        }
        function window() {
            app = appFactory.createObject(null);
            verify(app !== null, "Minimum-size acceptance uses the production Main window");
            app.width = 1280;
            app.height = 768;
            app.requestActivate();
            tryCompare(app, "active", true, 2000, "The actual application window receives native pointer input");
            verify(waitForRendering(app.contentItem), "The production application completes its initial frame");
            return app;
        }
        function test_desktop_minimum() {
            const win = window();
            compare(win.minimumWidth, Style.Sizes.appWindowMinimumWidth, "The native window publishes the shared supported minimum width to its window manager");
            compare(win.minimumHeight, Style.Sizes.appWindowMinimumHeight, "The native window publishes the shared supported minimum height to its window manager");
            verify(win.minimumWidth >= win.appBarCentralTabs.width && win.minimumHeight > 2 * AppSizes.toolbarControlSize, "The published native minimum leaves room for the workflow controls");
        }
        function test_placeholder_boundary_and_state() {
            open("stacked");
            chart.destroy();
            chart = null;
            const win = window(), w = win.minimumWidth, h = win.minimumHeight;
            Ui.click(test, Probe, win, "appBar.tab.analysis");
            tryVerify(() => !Ui.moving(win.contentItem), 2000, "The restored-state witness starts on a settled nondefault page");
            Session.project.currentExperimentIndex = 1;
            const retainedPage = pageBody("analysis");
            const tabs = Array.from(retainedPage.mainTabs || []);
            const stacked = tabs.find(tab => tab.text === "Stacked");
            verify(stacked !== undefined, "The loaded scan offers a real Stacked tab for resize restoration");
            Ui.click(test, Probe, win, stacked.objectName);
            const viewports = Render.descendants(retainedPage).filter(item => typeof item.contentY === "number" && item.contentHeight > item.height);
            for (const viewport of viewports)
                viewport.contentY = Math.min(53, viewport.contentHeight - viewport.height);
            const scrolls = viewports.map(item => item.contentY);
            verify(w >= win.appBarCentralTabs.width && h > 2 * AppSizes.toolbarControlSize, "The undersize predicate shares a usable desktop minimum");
            const reference = emptyFactory.createObject(surface);
            const project = Session.project, page = Globals.Vars.appBarCurrentIndex;
            win.minimumWidth = 0;
            win.minimumHeight = 0;
            for (const size of [[w - 1, h], [w, h - 1], [w, h], [w + 1, h + 1]]) {
                win.width = size[0];
                win.height = size[1];
                verify(waitForPolish(win.contentItem) && waitForRendering(win.contentItem), "A resize reaches its completed content layout");
                const labels = Render.texts(win.contentItem).filter(item => /increase.*window.*size/i.test(item.text));
                const small = size[0] < w || size[1] < h;
                compare(labels.length, small ? 1 : 0, "The placeholder appears below either threshold and disappears exactly at the minimum");
                if (small) {
                    const label = labels[0], at = label.mapToItem(win.contentItem, label.width / 2, label.height / 2);
                    compare(label.font.family, reference.font.family, "The placeholder reuses the empty-view font family");
                    compare(label.font.pixelSize, reference.font.pixelSize, "The placeholder reuses the empty-view font size");
                    compare(label.font.weight, reference.font.weight, "The placeholder reuses the empty-view font weight");
                    compare(controls(win.contentItem).length, 0, "Below the minimum only the placeholder remains, with all application controls hidden");
                    const image = grabImage(win.contentItem), colour = image.pixel(5, 5), expected = Style.Colors.contentBackground;
                    verify(["r", "g", "b"].every(channel => Math.abs(colour[channel] - expected[channel]) <= 1 / 255), "The undersize area reuses the empty view's grey background");
                    verify(Math.abs(at.x - win.width / 2) <= 1 && Math.abs(at.y - win.height / 2) <= 1, "The undersize message is centred in the complete application area");
                }
            }
            compare(Session.project, project, "Resizing across the minimum preserves the current project instance");
            compare(Globals.Vars.appBarCurrentIndex, page, "Resizing across the minimum preserves navigation state");
            compare(pageBody("analysis"), retainedPage, "Resize restoration retains the original page object rather than recreating it");
            compare(Session.project.currentExperimentIndex, 1, "Resize restoration retains the selected dataset");
            verify(stacked.checked, "Resize restoration retains the selected chart tab");
            for (let index = 0; index < viewports.length; ++index)
                compare(viewports[index].contentY, scrolls[index], "Resize restoration retains each existing scroll position");
            reference.destroy();
        }
    }
}
