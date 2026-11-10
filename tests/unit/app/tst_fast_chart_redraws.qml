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
                    test.adaptiveDraws.push({
                        file: fit.scanShownFile,
                        ms: Date.now()
                    });
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
            compare(selector.currentText, "Adaptive", "The real selector identifies the declared default before the saved-mode round trip");
            const defaultMode = Preferences.scanPatternUpdates;
            const adaptive = choices.indexOf("Adaptive"), every = choices.indexOf("Every pattern, fit waits for the display");
            verify(adaptive >= 0 && every >= 0 && adaptive !== every, "Adaptive remains a distinct selectable choice alongside Every pattern, fit waits for the display");
            mouseMove(win.contentItem, win.width - 1, win.height - 1);
            verify(SettingsProof.key(selector, Qt.Key_Home), "The open pattern-update selector receives Home through its actual window");
            for (let i = 0; i < every; ++i)
                verify(SettingsProof.key(selector, Qt.Key_Down), "The real selector navigates to fit waits independently of its menu position");
            verify(SettingsProof.key(selector, Qt.Key_Return), "The open pattern-update selector commits Every pattern through real keyboard input");
            tryCompare(Session.project.fit, "patternUpdates", 0, 1000, "Real keyboard input can choose Every pattern before returning to Adaptive");
            Ui.click(test, Probe, win, "analysis.patternUpdates");
            mouseMove(win.contentItem, win.width - 1, win.height - 1);
            verify(SettingsProof.key(selector, Qt.Key_Home), "The reopened pattern-update selector receives Home through its actual window");
            for (let i = 0; i < adaptive; ++i)
                verify(SettingsProof.key(selector, Qt.Key_Down), "The open pattern-update selector receives each real navigation key");
            verify(SettingsProof.key(selector, Qt.Key_Return), "The open pattern-update selector commits Adaptive through real keyboard input");
            tryCompare(selector, "currentText", "Adaptive", 1000, "Real keyboard input selects Adaptive after Every pattern");
            tryCompare(Session.project.fit, "patternUpdates", defaultMode, 1000, "The selected Adaptive choice reaches the actual fit worker");
            tryCompare(Preferences, "scanPatternUpdates", defaultMode, 1000, "Adaptive remains a machine setting");
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
            const spacing = named("toolbar.spacing"), layer = named("layer"), axes = named("axes");
            compare(spacing.currentText, "Wide", "New Stacked views default to the approved Wide spacing");
            for (let step = 0; step < 5; ++step) {
                spacing.currentIndex = step;
                spacing.activated(step);
                settled(chart);
                const share = step / 4, height = 1 - share + share / data.n;
                closeEnough(axes.axisY.min, 0, "The unzoomed Stacked axis starts at zero plot share");
                closeEnough(axes.axisY.max, 1, "The unzoomed Stacked axis ends at one plot share");
                for (let i = 0; i < data.n; ++i) {
                    closeEnough(layer.rowOf(i), data.n === 1 ? 0 : i * (1 - height) / (data.n - 1), "Every baseline obeys the independent linear spacing rule");
                    closeEnough(layer.peakOf(i) - layer.rowOf(i), height, "Each equal triangle has the independently specified spacing height");
                    if (step === 4 && i > 0)
                        verify(layer.peakOf(i - 1) <= layer.rowOf(i) + .00001, "Separate leaves adjacent traces nonoverlapping");
                }
                closeEnough(layer.peakOf(data.n - 1), 1, "Every spacing places the complete stack inside the plot");
            }
        }

        function test_wheel_reaches_last_dataset_data() {
            return ["experiment", "analysis"].map(page => ({
                        tag: page,
                        page
                    }));
        }
        function test_wheel_reaches_last_dataset(data) {
            open("stacked", 12);
            chart.destroy();
            chart = null;
            const win = window();
            Ui.click(test, Probe, win, "appBar.tab." + data.page);
            tryVerify(() => pageReady(data.page) && !Ui.moving(win.contentItem), 3000, "Wheel navigation reaches the actual settled Experiment or Analysis page");
            const body = pageBody(data.page);
            const tab = Array.from(body.mainTabs).find(item => item.text === "Stacked");
            verify(tab !== undefined && tab.enabled, "Both pages expose the actual Stacked chart tab");
            Ui.click(test, Probe, win, tab.objectName);
            tryVerify(() => tab.checked && !Ui.moving(win.contentItem), 2000, "Real tab input exposes the settled Stacked chart");
            chart = Render.descendants(body).find(item => item.objectName === "scanView.stacked" && item.visible && item.shown);
            verify(chart !== undefined, "Wheel reachability observes the live page-owned Stacked chart");
            tryCompare(chart.scan, "loaded", 12, 8000, "Every independently supplied triangle is loaded on the shown page");
            choose(named("toolbar.spacing"), "Separate");
            chart.zoomY = [0, .25];
            settled(chart);
            const axes = named("axes"), pointer = named("pointer"), layer = named("layer");
            closeEnough(axes.axisY.min, 0, "Fixed-height stack starts at its default lower viewport");
            closeEnough(axes.axisY.max, .25, "Zoomed stack starts with one plot-height viewport");
            for (let step = 0; step < 35; ++step)
                mouseWheel(pointer, pointer.width / 2, pointer.height / 2, 0, 120);
            settled(chart);
            closeEnough(axes.axisY.min, .75, "Real wheel input reaches the independently computed top viewport of twelve half-height traces");
            closeEnough(axes.axisY.max, 1, "The complete fixed-height stack is reachable beyond zero to one");
            closeEnough(layer.peakOf(11) - layer.rowOf(11), 1 / 12, "Wheel scrolling preserves the last trace's specified relative height");
            const x = (25 - axes.axisX.min) / (axes.axisX.max - axes.axisX.min) * pointer.width;
            const y = (axes.axisY.max - (11.5 / 12)) / (axes.axisY.max - axes.axisY.min) * pointer.height;
            mouseClick(pointer, x, y);
            tryCompare(Session.project, "currentExperimentIndex", 11, 1500, "The last independently placed triangle is selectable by real pointer input after wheel scrolling");
            for (let step = 0; step < 35; ++step)
                mouseWheel(pointer, pointer.width / 2, pointer.height / 2, 0, -120);
            settled(chart);
            closeEnough(axes.axisY.min, 0, "Reverse wheel input returns to the first trace without losing the stack's lower end");
            closeEnough(axes.axisY.max, .25, "Wheel navigation preserves the viewport span in both directions");
        }
        function test_joint_exclusions_follow_placement_data() {
            return ["gpu", "software"].map(renderer => ({
                        tag: renderer,
                        renderer
                    }));
        }
        function test_joint_exclusions_follow_placement(data) {
            Preferences.resetToDefaults();
            Preferences.chartHighlightSelected = false;
            Preferences.scanRenderer = data.renderer;
            Style.Colors.theme = Style.Colors.LightTheme;
            const location = SettingsProof.copyProject(Probe.repoUrl("docs/user/cli/pd-neut-tof_ferrite-austenite-beer_joint/project"));
            Input.joint(SettingsProof, location, false);
            const bands = [[1213, 1513], [5481, 6231]];
            for (const [row, name] of [[0, "expt_n2"], [1, "expt_s2"]]) {
                const file = "experiments/" + name + ".edi";
                const old = SettingsProof.text(location, file);
                const changed = old.replace(/loop_\n_excluded_region\.id[\s\S]*?\n\n/, "loop_\n_excluded_region.id\n_excluded_region.start\n_excluded_region.end\n1 " + bands[row].join(" ") + "\n\n");
                verify(changed !== old && SettingsProof.write(location, file, changed), "Each independent joint experiment receives its own distinct native excluded interval");
            }
            verify(Session.openProject(location), "Joint exclusion placement opens the independently authored real two-bank project");
            chart = scanFactory.createObject(surface, {
                project: Session.project,
                mode: "stacked",
                shown: true
            });
            verify(chart !== null, "Joint exclusion pixels come from the production Stacked component");
            tryCompare(chart.scan, "loaded", 2, 8000, "Both distinct joint experiments load before checking their exclusion extents");
            const layer = named("layer"), axes = named("axes");
            tryCompare(layer, "gpu", data.renderer === "gpu", 2000, "The joint exclusion matrix exercises the actual GPU and painter Stacked paths");
            const selector = named("toolbar.xaxis");
            if (chart.scan.dShown) {
                selector.currentIndex = 0;
                selector.activated(0);
                tryCompare(chart.scan, "dShown", false, 2000, "The independent native exclusion intervals use the native TOF axis");
            }
            for (const placement of [
                {
                    spacing: "Separate",
                    spans: [[0, .5], [.5, 1]]
                },
                {
                    spacing: "Medium",
                    spans: [[0, .75], [.25, 1]]
                }
            ]) {
                choose(named("toolbar.spacing"), placement.spacing);
                chart.zoomY = [-.1, 1.1];
                const sample = (image, x, y) => {
                    const at = layer.mapToItem(chart, (x - axes.axisX.min) / (axes.axisX.max - axes.axisX.min) * layer.width, (axes.axisY.max - y) / (axes.axisY.max - axes.axisY.min) * layer.height);
                    return String(image.pixel(Math.floor(at.x * image.width / chart.width), Math.floor(at.y * image.height / chart.height)));
                };
                settled(chart);
                const full = grabImage(chart);
                for (let row = 0; row < 2; ++row) {
                    const x = (bands[row][0] + bands[row][1]) / 2;
                    const plainX = row === 0 ? bands[row][0] - 100 : bands[row][1] + 100;
                    const span = placement.spans[row];
                    for (const y of [span[0] + .035, (span[0] + span[1]) / 2, span[1] - .035])
                        compare(sample(full, x, y), sample(full, plainX, y), "Stacked excluded ranges never tint the empty vertical span above the curve");
                    let dimmed = false;
                    for (let dy = -3; dy <= 3; ++dy) {
                        const y = span[0] + dy * (axes.axisY.max - axes.axisY.min) / layer.height;
                        dimmed = dimmed || sample(full, x, y) !== sample(full, plainX, y);
                    }
                    verify(dimmed, "Each experiment's excluded curve is dimmed at its independently placed baseline");
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
            compare(layer.highlight, true, "The default highlight preference reaches the active scan layer");
            closeEnough(layer.faded, 0.3, "The active scan layer uses the shared thirty-percent fade");
            Session.project.currentExperimentIndex = 1;
            if (data.mode === "stacked") {
                choose(named("toolbar.spacing"), "Separate");
            }
            settled(chart);
            const before = grabImage(surface);
            mouseClick(toggle, toggle.width / 2, toggle.height / 2);
            tryCompare(Preferences, "chartHighlightSelected", false, 1000, "Actual toolbar input writes the one shared highlight preference");
            compare(layer.highlight, false, "Disabling highlight reaches the active scan layer");
            settled(chart);
            const equal = grabImage(surface);
            verify(!before.equals(equal), "Disabling highlight changes actual rendered ink rather than only a preference");
            const background = chart.colors.chartBackground;
            function sample(image, x, y) {
                const point = layer.mapToItem(surface, x, y);
                return image.pixel(Math.floor(point.x * image.width / surface.width), Math.floor(point.y * image.height / surface.height));
            }
            function distance(colour) {
                return Math.sqrt(["r", "g", "b"].reduce((sum, channel) => sum + Math.pow(colour[channel] - background[channel], 2), 0));
            }
            for (let row = 0; row < 3; ++row) {
                const level = data.mode === "map" ? chart.scan.rowOf(row) : layer.rowOf(row) + (layer.peakOf(row) - layer.rowOf(row)) * 2 / 3;
                const py = (axes.axisY.max - level) / (axes.axisY.max - axes.axisY.min) * layer.height;
                const xValue = data.mode === "map" ? 40 : 30;
                const px = (xValue - axes.axisX.min) / (axes.axisX.max - axes.axisX.min) * layer.width;
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
                    verify(data.mode === "stacked" ? ratio > 1.1 && ratio < 1.5 : ratio > .85 && ratio < 1.15, "Highlight draws the selected Stacked line at full opacity and retains the selected Map colour");
                else {
                    verify(ratio > 0 && ratio < .5, "Unselected patterns recede below half the normal rendered ink");
                    if (data.mode === "stacked") {
                        const faded = sample(before, px, best.y);
                        verify(Math.max(faded.r, faded.g, faded.b) - Math.min(faded.r, faded.g, faded.b) <= 3 / 255, "Unselected Stacked curves use the owner's disabled neutral colour");
                    }
                }
            }
            if (data.mode === "stacked") {
                choose(named("toolbar.spacing"), "Overlay");
                mouseClick(toggle, toggle.width / 2, toggle.height / 2);
                tryCompare(Preferences, "chartHighlightSelected", true, 1000, "Real toolbar input restores highlighting for the overlap witness");
                settled(chart);
                const hex = Approved.colours(SettingsProof, "earth", "measured", 3, false)[1];
                const expected = [1, 3, 5].map(start => parseInt(hex.substr(start, 2), 16) / 255);
                const x = (30 - axes.axisX.min) / (axes.axisX.max - axes.axisX.min) * layer.width;
                const peak = layer.peakOf(1), base = layer.rowOf(1), value = base + (peak - base) * 2 / 3;
                const y = (axes.axisY.max - value) / (axes.axisY.max - axes.axisY.min) * layer.height;
                const overlap = grabImage(surface);
                let error = Infinity;
                for (let dy = -3; dy <= 3; ++dy) {
                    const pixel = sample(overlap, x, Math.max(1, Math.min(layer.height - 2, y + dy)));
                    error = Math.min(error, Math.max(...["r", "g", "b"].map((channel, index) => Math.abs(pixel[channel] - expected[index]))));
                }
                verify(error <= 3 / 255, "With fully overlapping traces the selected middle dataset is drawn on top in its independently frozen palette colour");
                mouseClick(toggle, toggle.width / 2, toggle.height / 2);
                tryCompare(Preferences, "chartHighlightSelected", false, 1000, "The overlap witness restores equal-dataset rendering before row selection");
                choose(named("toolbar.spacing"), "Separate");
            }
            compare(findChild(chart, "scanView." + data.mode + ".current"), null, "The retired selected-pattern rectangle has no remaining runtime instance");
            Session.project.currentExperimentIndex = 1;
            settled(chart);
            const labels = Render.descendants(chart).filter(item => item.objectName === "scanView." + data.mode + ".rowLabel.1" && item.visible && item.opacity > 0 && item.width > 0 && item.height > 0);
            compare(labels.length, 1, "With highlight off exactly one visible label marks the selected dataset");
            const label = labels[0];
            const segments = Array.from(label.segments).filter(segment => typeof segment.text === "string" && segment.text !== "" && segment.bold === true);
            verify(segments.length > 0, "The selected IconLine declares a nonempty bold text segment");
            const selectedHex = Approved.colours(SettingsProof, "earth", "measured", 3, false, {
                scan: true
            })[1];
            const selectedColour = data.mode === "map" ? Style.Colors.themeAccent : Qt.rgba(parseInt(selectedHex.slice(1, 3), 16) / 255, parseInt(selectedHex.slice(3, 5), 16) / 255, parseInt(selectedHex.slice(5, 7), 16) / 255, 1);
            compare(label.textColor, selectedColour, "The selected IconLine uses its dataset colour on Stacked and the accent on Map");
            const bold = Render.texts(label).find(item => item.opacity > 0 && segments.some(segment => segment.text === item.text) && item.font.family === Style.Fonts.ptSansBold.name && item.font.styleName === "Bold");
            verify(bold !== undefined, "The selected dataset's visible text uses the loaded bold font family and style");
            tryCompare(bold, "color", selectedColour, 1500, "The selected dataset text reaches its approved view colour");
            const pointer = named("pointer");
            const row = data.mode === "map" ? chart.scan.rowOf(2) : layer.rowOf(2) + (layer.peakOf(2) - layer.rowOf(2)) * 2 / 3;
            const x = (30 - axes.axisX.min) / (axes.axisX.max - axes.axisX.min) * pointer.width;
            const y = (axes.axisY.max - row) / (axes.axisY.max - axes.axisY.min) * pointer.height;
            mouseMove(pointer, x, y);
            const hover = named("hover");
            tryVerify(() => hover.visible && named("hover.name").segments.some(piece => piece.text === chart.scan.rowText(2)), 1500, "Actual plot hover names the independently targeted dataset");
            mouseClick(pointer, x, y);
            tryCompare(Session.project, "currentExperimentIndex", 2, 1000, "Actual plot input selects the dataset at its independently observed row");
        }
        function test_hover_tooltip_data() {
            return ["stacked", "map"].map(mode => ({
                        tag: mode,
                        mode: mode
                    }));
        }
        function test_hover_tooltip(data) {
            open(data.mode);
            const layer = named("layer"), axes = named("axes"), pointer = named("pointer");
            if (data.mode === "stacked") {
                choose(named("toolbar.spacing"), "Separate");
            }
            for (const pose of [
                {
                    x: 30,
                    row: 1
                },
                {
                    x: 60,
                    row: 2
                },
                {
                    x: 20,
                    row: 0
                }
            ]) {
                const share = pose.x <= 40 ? (pose.x - 10) / 30 : (80 - pose.x) / 40;
                const value = data.mode === "map" ? chart.scan.rowOf(pose.row) : layer.rowOf(pose.row) + (layer.peakOf(pose.row) - layer.rowOf(pose.row)) * share;
                const x = (pose.x - axes.axisX.min) / (axes.axisX.max - axes.axisX.min) * pointer.width;
                const y = (axes.axisY.max - value) / (axes.axisY.max - axes.axisY.min) * pointer.height;
                mouseMove(pointer, x, y);
                const tooltip = named("hover");
                tryVerify(() => tooltip.visible && named("hover.name").segments.some(piece => piece.text === chart.scan.rowText(pose.row)), 2000, "Real plot hover names the independently targeted dataset");
                tryCompare(tooltip, "opacity", 1, 2500, "The actual tooltip finishes its entry transition before geometry and style observations");
                const caption = named("hover.name"), intensity = named("hover.intensity");
                compare(tooltip.color, chart.colors.mainContentBackgroundHalfTransparent, "The plotted readout shares the Pattern figure's translucent background");
                compare(tooltip.border.color, chart.colors.chartGridLine, "The plotted readout shares the Pattern figure's border colour");
                compare(intensity.color, chart.colors.themeForeground, "The intensity line uses the common figure text colour");
                compare(intensity.font.family, Style.Fonts.fontFamily, "The intensity line uses the application's shared text font");
                verify(caption.segments.some(piece => piece.icon === "microscope"), "The first hover line retains the experiment icon beside its name");
                const expected = Approved.colours(SettingsProof, "earth", "measured", 3, false, {
                    scan: true
                })[pose.row];
                compare(String(caption.textColor).toLowerCase(), expected, "The hovered dataset name retains its independently recorded colour");
                verify(intensity.visible && Math.abs(parseFloat(intensity.text.replace(/^meas:\s*/, "").replace(/,/g, "")) - 255 * share) <= 1, "The second hover line draws the independent triangular input intensity within one count of pointer quantization");
                const background = tooltip;
                verify(Ui.rendered(background) && background.opacity > 0, "The actual plot readout background is visibly rendered");
                const texts = Render.texts(tooltip);
                verify(texts.some(item => item.text === chart.scan.rowText(pose.row)) && texts.some(item => item === intensity), "Both dataset and intensity lines have real rendered text");
                const box = background.mapToItem(layer, 0, 0, background.width, background.height);
                verify(box.x >= -1 && box.y >= -1 && box.x + box.width <= layer.width + 1 && box.y + box.height <= layer.height + 1, "The complete visible plot tooltip remains inside the plot, including edge hovers");
                const dx = Math.max(box.x - x, 0, x - box.x - box.width), dy = Math.max(box.y - y, 0, y - box.y - box.height);
                verify(Math.hypot(dx, dy) <= 2 * Style.Sizes.fontPixelSize, "The plot tooltip is next to the actual pointer rather than pinned elsewhere in the chart");
                for (const control of controls(chart).filter(item => String(item.objectName).includes("toolbar."))) {
                    const rect = control.mapToItem(layer, 0, 0, control.width, control.height);
                    verify(box.x + box.width <= rect.x || rect.x + rect.width <= box.x || box.y + box.height <= rect.y || rect.y + rect.height <= box.y, "The visible hover tooltip never overlaps an actual toolbar control");
                }
            }
        }
        function combo(item) {
            return typeof item.currentIndex === "number" && typeof item.currentText === "string" && item.model !== undefined;
        }
        function controls(root) {
            return Render.descendants(root).filter(item => item.visible && item.width > 0 && item.height > 0 && typeof item.toolTip === "string" && (combo(item) || (typeof item.checked === "boolean" && typeof item.fontIcon === "string")));
        }
        function pageBody(name) {
            return name === "home" ? Ui.page(app) : Render.descendants(app.contentItem).find(item => item.pageName === name);
        }
        function pageReady(name) {
            const selected = Ui.control(Probe, app, "appBar.tab." + name), page = Ui.page(app);
            return selected !== null && selected.checked && page !== null && Math.abs(page.mapToItem(app.contentItem, 0, 0).x) < 1;
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
            // A wide application must leave the chart wide after its adaptive sidebar.
            const minimum = win.minimumWidth, wide = Math.max(2000, minimum + 1000);
            const requested = data.width === 420 ? minimum : data.width === 740 ? Math.round((minimum + wide) / 2) : wide;
            win.width = requested;
            win.height = Math.max(win.minimumHeight, 900);
            tryVerify(() => Math.abs(win.width - requested) <= 1, 2000, "Toolbar geometry uses the actual supported minimum, middle or wide application width");
            tryVerify(() => pageReady(data.page), 3000, "The actual chart page reaches its viewport after application resize");
            settled(chart);
            let previous = "", stable = 0;
            tryVerify(() => {
                const selector = Ui.control(Probe, win, "mainArea.blocks");
                if (!selector)
                    return false;
                const geometry = [selector, chart].concat(controls(chart)).map(item => {
                    const point = item.mapToItem(win.contentItem, 0, 0);
                    return [point.x, point.y, item.width, item.height].map(value => Math.round(value * 10) / 10);
                });
                const current = JSON.stringify(geometry);
                stable = current === previous ? stable + 1 : 0;
                previous = current;
                return stable >= 3;
            }, 4000, "The selector and toolbar finish their independent geometry animations before their centres are compared");
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
            tryVerify(() => Ui.control(Probe, win, "mainArea.blocks") !== null, 3000, "The actual dataset selector reaches its settled viewport after application resize");
            const selector = Ui.control(Probe, win, "mainArea.blocks");
            verify(selector !== null && selector.width > 0, "Every chart toolbar has its actual visible dataset selector line above it");
            const centre = selector.mapToItem(chart, selector.width / 2, 0).x;
            for (const y of ys) {
                const row = lines[y];
                const left = Math.min(...row.map(item => item.left)), right = Math.max(...row.map(item => item.right));
                console.log("TOOLBAR_CENTRE " + JSON.stringify({
                    page: data.page,
                    mode: data.mode,
                    windowWidth: win.width,
                    chartWidth: chart.width,
                    line: [left, right],
                    actual: (left + right) / 2,
                    selector: centre
                }));
                verify(Math.abs((left + right) / 2 - centre) <= 1, "Every actual toolbar line shares the dataset selector line's horizontal centre; actual=" + (left + right) / 2 + "; selector=" + centre);
            }
            if (data.width === 1200) {
                const conservativeRoom = items.reduce((sum, item) => sum + item.width, 0) + (items.length + 1) * Math.max(AppSizes.toolbarSpacing, Style.Sizes.fontPixelSize);
                verify(chart.width - 2 * AppSizes.mainAreaMargin >= conservativeRoom, "The wide-window scenario leaves actual chart room for every control and its spacing before requiring one line");
                compare(ys.length, 1, "A chart with room for all controls puts them on one centred line");
            }
            const comboWidth = items.filter(combo).reduce((sum, item) => sum + item.width, 0);
            if (comboWidth > chart.width - 2 * AppSizes.mainAreaMargin)
                verify(ys.length >= 3, "Comboboxes that physically cannot fit together wrap onto multiple lines above the buttons");
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
                    Session.project.mapDirection = Session.project.mapDirection === "normal" ? "inverted" : "normal";
                else {
                    Preferences.scanStackedReversed = !Preferences.scanStackedReversed;
                    Preferences.scanStackedPalette = chart.stackedChoices[i % chart.stackedChoices.length];
                }
                Preferences.chartHighlightSelected = !Preferences.chartHighlightSelected;
                Session.project.currentExperimentIndex = i % 3;
                if (data.mode === "stacked") {
                    const spacing = named("toolbar.spacing");
                    spacing.activated(i % 5);
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
            tryVerify(() => pageBody(data.page) && pageReady(data.page), 3000, "The minimum-size witness reaches the actual selected page including Home");
            tryVerify(() => !Ui.moving(win.contentItem), 2000, "Page movement finishes before minimum-size geometry is inspected");
            verify(waitForPolish(win.contentItem) && waitForRendering(win.contentItem), "Every page at exactly the minimum has a completed frame");
            const current = pageBody(data.page), image = grabImage(win.contentItem);
            verify(current !== undefined && current !== null && pageReady(data.page) && image.width > 0, "Every real page produces a minimum-size capture");
            const fields = Render.descendants(current).filter(item => item.visible && item.width > 0 && item.height > 0 && (combo(item) || (typeof item.cursorPosition === "number" && typeof item.readOnly === "boolean") || item.objectName.startsWith("group.")) && Ui.inPane(item));
            if (data.index > 0)
                verify(fields.length > 0, "Loaded workflow pages retain reachable real inputs at the minimum");
            for (const field of fields) {
                const folded = [];
                for (let parent = field.parent; parent; parent = parent.parent)
                    if (parent.titleArea && parent.collapsible && parent.collapsed)
                        folded.push(parent);
                for (const group of folded.reverse()) {
                    Ui.scrollIntoView(group.titleArea);
                    const hit = Ui.clickPoint(group.titleArea);
                    verify(hit !== null, "Every folded ancestor has a reachable header at the supported minimum");
                    mouseClick(group.titleArea, hit.x, hit.y);
                    tryCompare(group, "collapsed", false, 1500, "Real header input reveals the minimum-size control before scrolling to it");
                }
                Ui.scrollIntoView(field);
                const at = field.mapToItem(win.contentItem, 0, 0);
                verify(at.x >= -1 && at.x + field.width <= win.width + 1, "No actual input field or whole group is clipped horizontally at the minimum");
                verify(waitForPolish(win.contentItem), "Minimum-size input scrolling completes its actual layout");
                tryVerify(() => Ui.exposed(field), 1000, "Vertical scrolling reaches each actual input at the minimum: " + field.objectName);
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
            compare(AppSizes.minimumAppWidth, 1024, "ADR-0017 section 2 fixes the supported app width at 1024 logical pixels");
            compare(AppSizes.minimumAppHeight, 640, "ADR-0017 section 2 fixes the supported app height at 640 logical pixels");
            compare(win.minimumWidth, AppSizes.minimumAppWidth, "The native window publishes the app's shared supported minimum width to its window manager");
            compare(win.minimumHeight, AppSizes.minimumAppHeight, "The native window publishes the app's shared supported minimum height to its window manager");
            verify(win.minimumWidth >= win.appBarCentralTabs.width && win.minimumHeight > 2 * AppSizes.toolbarControlSize, "The published native minimum leaves room for the workflow controls");
        }
        function test_placeholder_boundary_and_state() {
            open("stacked");
            chart.destroy();
            chart = null;
            const win = window(), w = win.minimumWidth, h = win.minimumHeight;
            Ui.click(test, Probe, win, "appBar.tab.analysis");
            tryVerify(() => pageReady("analysis") && !Ui.moving(win.contentItem), 3000, "The restored-state witness starts on a settled nondefault page");
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
            const cover = findChild(win, "app.tooSmall"), label = findChild(win, "app.tooSmall.text"), root = Ui.windowRoot(win);
            verify(cover !== null && label !== null, "The actual Main window owns the named undersize overlay and its empty-view label");
            compare(cover.parent, win.Overlay.overlay, "The undersize cover belongs to the complete window overlay rather than the application content subtree");
            verify(label.parent === cover && String(label.text) === "Increase the window size", "The named overlay contains the exact requested increase-window message");
            const home = Ui.control(Probe, win, "appBar.tab.home");
            verify(home !== null && home.enabled && !home.checked, "The pointer-blocking witness targets a real enabled nonselected navigation control");
            win.minimumWidth = 0;
            win.minimumHeight = 0;
            for (const size of [[w - 1, h], [w, h - 1], [w - 1, h - 1], [w, h], [w + 1, h + 1]]) {
                win.width = size[0];
                win.height = size[1];
                tryCompare(win, "width", size[0], 1500, "The native boundary witness actually reaches its requested browser-sized width");
                tryCompare(win, "height", size[1], 1500, "The native boundary witness actually reaches its requested browser-sized height");
                verify(waitForPolish(root) && waitForRendering(root), "A resize reaches its completed full-window overlay layout");
                const small = size[0] < w || size[1] < h;
                tryCompare(cover, "visible", small, 1500, "The named placeholder appears below either threshold and disappears exactly at the minimum");
                compare(label.visible, small, "The actual empty-view label follows the overlay's effective visibility");
                if (small) {
                    const box = cover.mapToItem(root, 0, 0, cover.width, cover.height);
                    verify(Math.abs(box.x) <= 1 && Math.abs(box.y) <= 1 && Math.abs(box.width - win.width) <= 1 && Math.abs(box.height - win.height) <= 1, "The named overlay covers the entire application area including app and status bars");
                    const at = label.mapToItem(root, label.width / 2, label.height / 2);
                    compare(label.font.family, reference.font.family, "The placeholder reuses the empty-view font family");
                    compare(label.font.pixelSize, reference.font.pixelSize, "The placeholder reuses the empty-view font size");
                    compare(label.font.weight, reference.font.weight, "The placeholder reuses the empty-view font weight");
                    compare(label.color, reference.color, "The placeholder reuses the empty-view disabled text colour");
                    verify(Math.abs(at.x - win.width / 2) <= 1 && Math.abs(at.y - win.height / 2) <= 1, "The undersize message is centred in the complete application area");
                    const image = grabImage(root), expected = Style.Colors.contentBackground;
                    const text = label.mapToItem(root, 0, 0, label.width, label.height);
                    const dpr = image.width / root.width;
                    const empty = colour => ["r", "g", "b"].every(channel => Math.abs(colour[channel] - expected[channel]) <= 1 / 255);
                    for (let y = 3; y < root.height; y += 29)
                        for (let x = 3; x < root.width; x += 31)
                            if (x < text.x - 3 || x > text.x + text.width + 3 || y < text.y - 3 || y > text.y + text.height + 3)
                                verify(empty(image.pixel(Math.floor(x * dpr), Math.floor(y * dpr))), "The complete undersize frame paints only the empty-view background outside its message");
                    let ink = false;
                    for (let y = Math.max(0, Math.floor(text.y * dpr)); y < Math.min(image.height, (text.y + text.height) * dpr) && !ink; y += 2)
                        for (let x = Math.max(0, Math.floor(text.x * dpr)); x < Math.min(image.width, (text.x + text.width) * dpr) && !ink; x += 2)
                            ink = !empty(image.pixel(x, y));
                    verify(ink, "The named increase-window message contributes actual visible glyph ink");
                    const hit = Ui.clickPoint(home);
                    verify(hit !== null, "The underlying enabled navigation target remains in the window for pointer interception");
                    mouseClick(home, hit.x, hit.y);
                    compare(Globals.Vars.appBarCurrentIndex, page, "The undersize overlay blocks actual pointer activation of a covered application control");
                }
            }
            compare(Session.project, project, "Resizing across the minimum preserves the current project instance");
            compare(Globals.Vars.appBarCurrentIndex, page, "Resizing across the minimum preserves navigation state");
            compare(pageBody("analysis"), retainedPage, "Resize restoration retains the original page object rather than recreating it");
            compare(Session.project.currentExperimentIndex, 1, "Resize restoration retains the selected dataset");
            verify(stacked.checked, "Resize restoration retains the selected chart tab");
            for (let index = 0; index < viewports.length; ++index)
                compare(viewports[index].contentY, scrolls[index], "Resize restoration retains each existing scroll position");
            Ui.click(test, Probe, win, "appBar.tab.home");
            tryCompare(home, "checked", true, 1500, "The same real navigation control accepts pointer input after the overlay disappears");
            reference.destroy();
        }
    }
}
