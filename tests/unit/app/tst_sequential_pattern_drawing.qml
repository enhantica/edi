// SPDX-License-Identifier: BSD-3-Clause
import QtQuick
import QtQuick.Window
import QtTest
import edi.app
import EdiAcceptance 1.0
import ReportAcceptance 1.0
import "RenderedTable.js" as Render
import "UiInteraction.js" as Ui
import "SequentialDrawing.js" as Drawing

Item {
    id: surface
    width: 1400
    height: 1000
    Component {
        id: factory
        Main {
            width: 1400
            height: 1000
            visible: true
        }
    }
    TestCase {
        id: test
        name: "SequentialPatternDrawing"
        when: windowShown
        property var appWindow
        property var chart
        property var captures: []
        property var initialPoints: []
        property string captureKind: ""

        property var savedMeasuredStyle
        function init() {
            savedMeasuredStyle = typeof Preferences.patternMeasuredStyle === "string" ? Preferences.patternMeasuredStyle : null;
            if (savedMeasuredStyle !== null)
                Preferences.patternMeasuredStyle = "linePoints";
        }
        function cleanup() {
            if (savedMeasuredStyle !== null)
                Preferences.patternMeasuredStyle = savedMeasuredStyle;
            if (Session.project && Session.project.fit.running) {
                Session.project.fit.cancel();
                tryVerify(() => !Session.project.fit.running, 10000, "The real scan worker must stop before the chart is destroyed");
            }
            Session.closeProject();
            if (appWindow) {
                appWindow.close();
                appWindow.destroy();
            }
            appWindow = null;
            chart = null;
            captures = [];
            initialPoints = [];
        }
        function setupScan() {
            AppState.reset();
            appWindow = factory.createObject(null);
            verify(appWindow !== null, "Sequential drawing uses the actual Main window");
            appWindow.requestActivate();
            tryCompare(appWindow, "active", true, 2000, "The real scan window must receive pointer input");
            const source = Probe.repoUrl("tests/fixtures/scan_template/project");
            const project = SettingsProof.copyProject(source);
            verify(String(project) !== "", "The saved three-file scan must be copied before fitting");
            verify(Session.openProject(project), "The sequential drawing witness must open the saved independent scan");
            tryVerify(() => !Session.project.calculating && Probe.datasetReady(Session.project), 10000, "The scan must finish loading its initial pattern");
            verify(Session.project.scan && Session.project.fit.scanTotal === 3, "The real worker must retain all three saved measured files");
            Ui.click(test, Probe, appWindow, "appBar.tab.analysis");
            const page = Ui.page(appWindow);
            tryVerify(() => !Ui.moving(appWindow.contentItem), 2000, "The Analysis page must settle before scan input");
            chart = Render.descendants(page).find(item => item.objectName === "chart" && item.visible && item.shown && item.report === null);
            verify(chart !== undefined && chart.Window.window === appWindow, "The scan must draw in its actual visible app-owned chart");
            const toggle = Render.descendants(chart).find(item => item.toolTip === "Show each structure's curve" && typeof item.checked === "boolean");
            verify(toggle !== undefined && toggle.visible, "The real chart must expose the structure-curve toolbar toggle");
            if (!toggle.checked) {
                appWindow.update();
                verify(waitForRendering(appWindow.contentItem), "The actual structure toggle must render before input");
                const at = Ui.clickPoint(toggle);
                verify(at !== null, "The structure toggle must be exposed to real pointer input");
                mouseClick(toggle, at.x, at.y);
            }
            tryCompare(toggle, "checked", true, 1000, "The structure fills must be switched on through the real toolbar");
            Session.project.fit.patternUpdates = 0;
            compare(Session.project.fit.patternUpdates, 0, "Every-pattern mode must exercise each real scan handover");
            appWindow.update();
            verify(waitForRendering(appWindow.contentItem), "The initial pattern must reach a real rendered frame");
        }
        function seriesPoints(series) {
            const result = [];
            for (let i = 0; i < series.count; ++i)
                result.push({
                    x: series.at(i).x,
                    y: series.at(i).y
                });
            return result;
        }
        function receipt(frame) {
            const result = {};
            for (const key in frame)
                result[key] = key === "signature" ? "observed, not a scientific golden" : key === "pixels" ? "captured frame" : frame[key];
            return result;
        }
        function snapshot() {
            const project = Session.project, fit = project.fit;
            const file = fit.scanShownFile, wasRunning = fit.running;
            const graph = findChild(chart, "chart.view.main"), line = findChild(chart, "chart.series.calc");
            verify(graph !== null && line !== null && line.count > 0, "The real main graph must contain a nonempty calculated curve");
            const points = seriesPoints(line);
            // The cached table calculation is not the live fit frame. Bind the
            // displayed input independently, then test the renderer/series invariant.
            const measured = seriesPoints(findChild(chart, "chart.series.meas"));
            let measuredWrong = 0;
            if (file) {
                const expected = new Map();
                for (const row of Probe.readFile("tests/fixtures/scan_template/project/experiments/d20_scan/" + file).split("\n")) {
                    const cells = row.trim().split(/\s+/).map(Number);
                    if (cells.length === 3 && cells.every(Number.isFinite))
                        expected.set(Math.round(cells[0] * 10000) / 10000, cells[1]);
                }
                verify(expected.size > 0 && measured.length > 0, "The scan witness must reach independently saved measured columns and their actual plotted series");
                measuredWrong = measured.filter(point => !expected.has(point.x) || expected.get(point.x) !== point.y).length;
            }
            const xAxis = findChild(chart, "chart.axis.x"), yAxis = findChild(chart, "chart.axis.y");
            const at = graph.mapToItem(appWindow.contentItem, graph.plotArea.x, graph.plotArea.y);
            const image = grabImage(appWindow.contentItem), ratio = image.width / appWindow.contentItem.width;
            verify(image.width > 0 && image.height > 0 && graph.plotArea.width > 0 && xAxis.max > xAxis.min && yAxis.max > yAxis.min, "The renderer must expose a real nonempty image and finite plot geometry");
            const box = {
                x: at.x * ratio,
                y: at.y * ratio,
                width: graph.plotArea.width * ratio,
                height: graph.plotArea.height * ratio,
                left: xAxis.min,
                right: xAxis.max,
                bottom: yAxis.min,
                top: yAxis.max,
                ratio: ratio
            };
            const live = graph.seriesList.filter(series => series.visible && series.opacity > 0 && series.color.a > 0);
            const calculated = live.filter(series => series.objectName === "chart.series.calc");
            const areas = live.filter(series => String(series.objectName).startsWith("chart.series.structure.") && series.upperSeries !== undefined && series.lowerSeries !== undefined && series.upperSeries && series.lowerSeries && series.upperSeries.count > 0 && series.lowerSeries.count > 0);
            const pixels = {
                image,
                box,
                points,
                colour: line.color,
                initial: initialPoints,
                background: chart.colors.chartBackground,
                areas: areas.map(area => ({
                            lower: seriesPoints(area.lowerSeries),
                            upper: seriesPoints(area.upperSeries),
                            colour: area.color,
                            opacity: area.opacity
                        }))
            };
            if (file !== fit.scanShownFile || wasRunning !== fit.running)
                return null;
            const record = {
                file: file,
                running: wasRunning,
                count: points.length,
                signature: JSON.stringify(points),
                measuredWrong: measuredWrong,
                calculatedCount: calculated.length,
                pixels: pixels
            };
            if (initialPoints.length === 0)
                initialPoints = points;
            return record;
        }
        function analyze(frame) {
            // Analyze immutable captures after the worker runs; pixel scans must not delay handovers.
            const p = frame.pixels;
            frame.calculation = Drawing.calculatedPixels(p.image, p.box, p.points, p.colour, p.initial, p.background);
            frame.fills = p.areas.map(area => Drawing.fillPixels(p.image, p.box, area.lower, area.upper, area.colour, area.opacity, p.background));
            p.image.save("sequential-" + captureKind + "-" + (frame.file || "initial") + ".png");
            console.info("SEQUENTIAL_FRAME", JSON.stringify(receipt(frame)));
            return frame;
        }
        function test_pixel_observer_rejects_stale_and_empty_drawing() {
            const box = {
                x: 0,
                y: 0,
                width: 100,
                height: 100,
                left: 0,
                right: 10,
                bottom: 0,
                top: 10,
                ratio: 1
            };
            const ink = {
                r: 0.8,
                g: 0.1,
                b: 0.2,
                a: 1
            };
            const current = [
                {
                    x: 0,
                    y: 6
                },
                {
                    x: 10,
                    y: 6
                }
            ], initial = [
                {
                    x: 1,
                    y: 2
                },
                {
                    x: 9,
                    y: 2
                }
            ];
            function image(sample) {
                return {
                    red: (x, y) => sample(x, y)[0],
                    green: (x, y) => sample(x, y)[1],
                    blue: (x, y) => sample(x, y)[2]
                };
            }
            const white = [255, 255, 255], rose = [204, 25.5, 51];
            const ordinary = image((x, y) => y === 40 && x >= 5 && x <= 94 ? rose : white);
            verify(Drawing.currentVisible(Drawing.calculatedPixels(ordinary, box, current, ink, initial)), "The pixel observer must accept a real current-only line with a visible positive control");
            const ghost = image((x, y) => (y === 40 || y === 80) && x >= 5 && x <= 94 ? rose : white);
            verify(!Drawing.currentVisible(Drawing.calculatedPixels(ghost, box, current, ink, initial)), "An extra stale line cannot hide behind a current series object");
            const faded = image((x, y) => y === 80 && x >= 5 && x <= 94 ? rose.map(value => 255 + 0.25 * (value - 255)) : y === 40 && x >= 5 && x <= 94 ? rose : white);
            verify(!Drawing.currentVisible(Drawing.calculatedPixels(faded, box, current, ink, initial)), "A faded stale line must also fail rather than escape a solid-colour-only pixel observer");
            verify(!Drawing.currentVisible(Drawing.calculatedPixels(image(() => white), box, current, ink, initial)), "An empty or unavailable renderer cannot pass the current-curve gate");
            const lower = [], upper = [];
            for (let i = 0; i <= 10; ++i) {
                lower.push({
                    x: i,
                    y: 2
                });
                upper.push({
                    x: i,
                    y: 8
                });
            }
            const fill = {
                r: 1,
                g: 0.4,
                b: 0,
                a: 0.25
            }, background = {
                r: 1,
                g: 1,
                b: 1,
                a: 1
            };
            const filled = image((x, y) => y > 20 && y < 80 ? [255, 216.75, 191.25] : white);
            verify(Drawing.fillVisible(Drawing.fillPixels(filled, box, lower, upper, fill, 1, background)), "The fill observer must accept coloured interior pixels of a real area");
            verify(!Drawing.fillVisible(Drawing.fillPixels(image(() => white), box, lower, upper, fill, 1, background)), "An outline or nonempty area object without drawn interior cannot pass");
            verify(!Drawing.fillVisible(Drawing.fillPixels(filled, box, lower, upper, fill, 0, background)), "An invisible structure area cannot pass from matching unrelated pixels");
        }
        function test_drawn_pattern_data() {
            return [
                {
                    tag: "current",
                    kind: "current"
                },
                {
                    tag: "fills",
                    kind: "fills"
                }
            ];
        }
        function test_drawn_pattern(data) {
            captureKind = data.kind;
            setupScan();
            compare(Preferences.patternYScale, "linear", "The drawing witness uses the ordinary fresh linear axis, with no presentation transform ambiguity");
            appWindow.update();
            verify(waitForRendering(appWindow.contentItem), "The initial series completes its next scene-synchronized frame");
            const initial = snapshot();
            if (initial !== null)
                analyze(initial);
            verify(initial !== null && initial.calculation.pixels >= 40 && initial.calculation.offCurve === 0 && initial.measuredWrong === 0, "The pixel observer must positively see the initial real calculated curve at its current physical coordinates");
            const fit = Session.project.fit;
            Ui.click(test, Probe, appWindow, "statusBar.fit.button");
            verify(fit.running, "The real Start fitting button must launch the sequential worker");
            const started = Date.now();
            let last = "";
            while (fit.running && Date.now() - started < 25000) {
                appWindow.update();
                wait(20);
                if (fit.scanShownFile && fit.scanShownFile !== last) {
                    const frame = snapshot();
                    if (frame) {
                        captures.push(frame);
                        last = frame.file;
                    }
                }
            }
            captures.forEach(analyze);
            const running = captures.filter(item => item.running);
            console.info("SEQUENTIAL_CAPTURE", data.kind, JSON.stringify(captures.map(receipt)));
            verify(!fit.running && fit.scanFitted === 3 && fit.outcome === "success", "All three real scan files must finish with their ordinary scientific iteration limit");
            verify(running.length >= 2 && new Set(running.map(frame => frame.file)).size >= 2, "The witness must inspect two distinct current patterns while the real scan is still running");
            if (data.kind === "current") {
                verify(running.some(frame => frame.calculation.separatedInitial >= 10), "The initial and current curves must separate in visible space so a retained initial curve cannot escape the pixel check");
                let previous = initial.signature;
                for (const frame of running) {
                    compare(frame.measuredWrong, 0, "Each running frame's measured series must match its independently parsed current file");
                    verify(frame.signature !== initial.signature && frame.signature !== previous, "The published calculated curve must change with each distinct running file, rather than retaining the initial curve");
                    previous = frame.signature;
                    compare(frame.calculatedCount, 1, "Exactly one visible calculated series must remain during a sequential fit");
                    verify(Drawing.currentVisible(frame.calculation), "Every drawn calculated-colour pixel must follow the current curve; no stale initial pattern may remain");
                }
            } else {
                for (const frame of running) {
                    compare(frame.fills.length, Session.project.structures.count, "Every linked structure must retain its visible nonempty area during the running fit");
                    verify(frame.fills.every(fill => Drawing.fillVisible(fill)), "Each running structure curve must draw real coloured interior pixels while its toolbar toggle is on");
                }
            }
        }
    }
}
