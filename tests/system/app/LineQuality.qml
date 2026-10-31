// SPDX-License-Identifier: BSD-3-Clause
import QtQuick
import QtQuick.Window
import QtTest
import edi.app
import EdiAcceptance 1.0
import EdiChartReference 1.0
import ReportAcceptance 1.0
import ChartBackendAcceptance 1.0
import EasyApplication.Gui.Style as Style
import "../../unit/app/RenderedTable.js" as Render
import "../../unit/app/ApprovedPalette.js" as Approved
import "../../fixtures/scan_views/input.js" as Input

Rectangle {
    id: surface
    width: 512
    height: 384
    color: "white"
    Item {
        id: viewport
        width: 512
        height: 384
        clip: true
    }
    Component {
        id: patternFactory
        PatternChart {
            width: 900
            height: 650
            x: -10000
            settingsPage: "pattern"
        }
    }
    Component {
        id: scanFactory
        ScanViewChart {
            width: 900
            height: 650
            x: -10000
            mode: "stacked"
        }
    }
    TestCase {
        id: test
        name: "LineQuality"
        when: windowShown
        property var pattern: null
        property var scan: null
        property var detached: []
        function cleanup() {
            for (const item of detached)
                item.item.parent = item.parent;
            detached = [];
            if (pattern)
                pattern.destroy();
            if (scan)
                scan.destroy();
            pattern = null;
            scan = null;
            Session.closeProject();
            Preferences.resetToDefaults();
        }
        function frame(item) {
            surface.Window.window.update();
            verify(waitForPolish(item) && waitForRendering(item), "The line-quality reference and candidate finish an actual rendered frame");
        }
        function test_capture_data() {
            let rows = [];
            for (const mode of ["gpu", "software"])
                for (const shape of ["peak", "needle"])
                    rows.push({
                        tag: mode + "-" + shape,
                        mode: mode,
                        shape: shape
                    });
            return rows;
        }
        function test_capture(data) {
            Preferences.resetToDefaults();
            Style.Colors.theme = Style.Colors.LightTheme;
            Preferences.patternMeasuredStyle = "line";
            Preferences.scanRenderer = data.mode;
            Preferences.chartHighlightSelected = false;

            const dpr = Screen.devicePixelRatio;
            ChartBackendProof.watch(surface);
            const centre = 10 + (256 * dpr + 0.25) / (512 * dpr) * 70;
            const half = 0.75 / (512 * dpr) * 70;
            const points = data.shape === "peak" ? [[10, 0], [40, 255], [80, 0]] : [[10, 0], [centre - half, 0], [centre, 255], [centre + half, 0], [80, 0]];
            const location = SettingsProof.copyProject(Qt.resolvedUrl("../../fixtures/scan_template/project"));
            Input.dense(SettingsProof, location, false, 1);
            const xs = points.map(point => point[0]);
            for (let i = 0; i <= 4096; ++i)
                xs.push(10 + 70 * i / 4096);
            xs.sort((a, b) => a - b);
            const dense = xs.filter((x, i) => i === 0 || x !== xs[i - 1]).map(x => {
                let index = 0;
                while (index + 1 < points.length - 1 && x > points[index + 1][0])
                    ++index;
                const a = points[index], b = points[index + 1];
                return [x, a[1] + (b[1] - a[1]) * (x - a[0]) / (b[0] - a[0])];
            });
            const rows = dense.map(point => point.join(" ") + " 1").join("\n") + "\n";
            verify(SettingsProof.write(location, "experiments/d20_scan/row_000.dat", "XYDATA independent line quality\nTEMP 100\n" + rows), "The Stacked fixture receives the independent sharp-peak columns");
            const file = "experiments/d20.edi", old = SettingsProof.text(location, file), start = old.indexOf("loop_\n_data.two_theta");
            verify(start >= 0, "The Pattern reference fixture declares its original measured-data loop");
            verify(SettingsProof.write(location, file, old.slice(0, start) + "loop_\n_data.two_theta\n_data.intensity_meas\n_data.intensity_meas_su\n" + rows), "The real Pattern reference receives exactly the same independent columns");
            verify(Session.openProject(location), "The line-quality pair opens the same private project");
            pattern = patternFactory.createObject(surface, {
                experiment: Session.project.currentExperiment
            });
            scan = scanFactory.createObject(surface, {
                project: Session.project
            });
            tryVerify(() => Probe.datasetReady(Session.project) && !Session.project.calculating && scan.scan && scan.scan.loaded === 1, 15000, "Both production charts finish loading the independent line-quality pattern");
            const view = ChartOracle.object(pattern, "chart.view.main");
            verify(view !== null, "The independent rendering reference is the actual Pattern chart Qt Graphs view");
            const series = Render.series(view), measured = series.find(item => item.objectName === "chart.series.meas");
            verify(measured !== undefined, "The Pattern reference contains its real measured line series");
            tryVerify(() => ChartOracle.points(measured).some(point => point.y === 255), 4000, "The Pattern reference contains the supplied independent points before raster comparison");
            measured.width = 1.5;
            const supplied = ChartOracle.points(measured);
            const peak = points[data.shape === "peak" ? 1 : 2];
            verify(supplied.some(actual => Math.abs(actual.x - peak[0]) < 1e-8 && actual.y === 255), "The actual Pattern reduction retains the independently supplied narrow peak at its physical x position");
            verify(dense.length > 8 * viewport.width, "The independent line input exceeds both DPR reduction budgets rather than bypassing reduction with a sparse polyline");
            const expected = Approved.colours(SettingsProof, "earth", "measured", 1, false)[0];
            compare(String(measured.color).toLowerCase(), expected, "The Pattern reference retains the independently approved measured colour");
            Session.project.stackedSpacing = "separate";
            const layer = Render.descendants(scan).find(item => item.objectName === "scanView.stacked.layer");
            verify(layer !== undefined, "The candidate is the actual production Stacked layer");
            compare(String(layer.colourOf(0)).toLowerCase(), expected, "Both Stacked paths retain the independently approved measured colour");
            compare(layer.gpu, data.mode === "gpu", "The line-quality matrix exercises the requested effective Stacked renderer");
            detached.push({
                item: view,
                parent: view.parent
            });
            view.parent = viewport;
            view.anchors.fill = undefined;
            view.width = 512;
            view.height = 384;
            view.marginLeft = 0;
            view.marginRight = 0;
            view.marginTop = 0;
            view.marginBottom = 0;
            view.axisX.visible = false;
            view.axisY.visible = false;
            AppState.patternViewRanges = [10, 80, -25.5, 280.5];
            for (const item of series)
                item.visible = item === measured;
            frame(view);
            view.x = -view.plotArea.x;
            view.y = -view.plotArea.y;
            compare(view.axisX.min, 10, "The independent Pattern reference uses the declared x range");
            compare(view.axisY.min, -25.5, "The independent Pattern reference uses the declared y range");
            detached.push({
                item: layer,
                parent: layer.parent
            });
            layer.parent = viewport;
            layer.anchors.fill = undefined;
            layer.x = 0;
            layer.y = 0;
            layer.width = view.plotArea.width;
            layer.height = view.plotArea.height;
            scan.setZoom([10, 80], [-0.1, 1.1]);
            layer.opacity = data.shape === "peak" ? 0.3 : 1;
            view.opacity = layer.opacity * .75;
            layer.visible = false;
            frame(view);
            const origin = view.mapToItem(surface, view.plotArea.x, view.plotArea.y);
            verify(Math.abs(origin.x) < 0.01 && Math.abs(origin.y) < 0.01 && Math.abs(view.plotArea.width - layer.width) < 0.01 && Math.abs(view.plotArea.height - layer.height) < 0.01, "Both actual plot rasters have the same origin, extent and device-pixel phase without image registration");
            const prefix = "line-quality-" + data.mode + "-" + data.shape + "-" + dpr;
            const reference = Qt.resolvedUrl("../../../build/" + prefix + "-pattern.png").toString().replace(/^file:\/\//, "");
            const candidate = Qt.resolvedUrl("../../../build/" + prefix + "-stacked.png").toString().replace(/^file:\/\//, "");
            let referenceElapsed = [];
            for (let i = 0; i < 8; ++i) {
                const before = Date.now();
                view.update();
                frame(view);
                referenceElapsed.push(Date.now() - before);
            }
            grabImage(surface).save(reference);
            view.visible = false;
            layer.visible = true;
            frame(layer);
            let elapsed = [];
            for (let i = 0; i < 8; ++i) {
                const before = Date.now();
                layer.update();
                frame(layer);
                elapsed.push(Date.now() - before);
            }
            grabImage(surface).save(candidate);
            console.log("LINE_QUALITY_CAPTURE " + JSON.stringify({
                mode: data.mode,
                shape: data.shape,
                dpr,
                reference,
                candidate,
                colour: expected,
                stroke_width: 1.5,
                reference_opacity: (data.shape === "peak" ? 0.3 : 1) * 0.75,
                x_range: [10, 80],
                y_range: [-25.5, 280.5],
                width: layer.width,
                height: layer.height,
                points,
                input_count: dense.length,
                reference_count: supplied.length,
                backend: ChartBackendProof.facts(surface),
                pattern_frame_delivery_ms: referenceElapsed,
                stacked_frame_delivery_ms: elapsed
            }));
        }
    }
}
