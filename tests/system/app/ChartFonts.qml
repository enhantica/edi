// SPDX-License-Identifier: BSD-3-Clause
import QtQuick
import QtQuick.Window
import QtTest
import QtGraphs
import edi.app
import ChartFontAcceptance 1.0
import EasyApplication.Gui.Style as Style

Rectangle {
    id: surface
    width: 1200; height: 800; color: "white"
    ChartFontProbe { id: probe }
    FontLoader { id: alternate; source: "qrc:/qt/qml/EasyApplication/Gui/Resources/Fonts/Noto_Sans/NotoSans-Regular.ttf" }
    Component { id: powder; PatternChart { anchors.fill: parent; shown: true } }
    Component { id: single; SingleCrystalChart { anchors.fill: parent; shown: true } }
    Component { id: scan; ScanViewChart { anchors.fill: parent; shown: true } }
    Component { id: evolution; EvolutionChart { anchors.fill: parent; shown: true } }
    Component { id: correlations; CorrelationChart { anchors.fill: parent; shown: true; namesShown: true } }
    Component { id: structure; StructureView { anchors.fill: parent; shown: true } }
    TestCase {
        id: test
        name: "ChartFonts"
        when: windowShown
        property var chart: null
        property var reference: null
        property var originalLoader: null
        property int originalSize: 0
        function init() {
            originalLoader = Style.Fonts.ptSansRegular;
            originalSize = Style.Sizes.fontPixelSize;
            Preferences.resetToDefaults();
        }
        function cleanup() {
            if (reference) reference.destroy();
            if (chart) chart.destroy();
            reference = null; chart = null;
            Session.closeProject();
            Style.Fonts.ptSansRegular = originalLoader;
            Style.Sizes.fontPixelSize = originalSize;
            Preferences.resetToDefaults();
        }
        function objects(root) { return Array.from(probe.objects(root)); }
        function named(root, name) { return objects(root).find(item => item.objectName === name); }
        function texts(root) {
            return objects(root).filter(item => probe.nativeText(item) && item.visible && item.width > 0 && item.height > 0 && typeof item.text === "string" && item.text !== "");
        }
        function frame() {
            surface.Window.window.update();
            verify(waitForPolish(surface) && waitForRendering(surface), "Chart font observations follow an actual laid-out rendered frame");
        }
        function titleFont(data) {
            if (reference) reference.visible = true;
            frame();
            const title = data.kind === "single" ? texts(chart).find(item => item.text === chart.quantity + " calc") : named(reference, "chart.title.x");
            verify(title !== undefined && title.visible && title.text.length > 0, "The font reference is the actual populated Pattern axis title");
            const font = title.font;
            compare(font.family, Style.Fonts.fontFamily, "The actual axis title uses the shared app font family");
            compare(font.pixelSize, Style.Sizes.fontPixelSize, "The actual axis title uses the shared app font pixel size");
            if (reference) reference.visible = false;
            return font;
        }
        function equal(font, expected, role) {
            compare(font.family, expected.family, "Every actual chart tick and label uses its axis title's app font family: " + role);
            compare(font.pixelSize, expected.pixelSize, "Every actual chart tick and label uses its axis title's pixel size: " + role);
        }
        function test_fonts_data() {
            return [
                {tag: "powder-main", kind: "powder", pane: "main"},
                {tag: "powder-residual", kind: "powder", pane: "residual"},
                {tag: "powder-bragg", kind: "powder", pane: "bragg"},
                {tag: "single-squared", kind: "single", quantity: "f_squared"},
                {tag: "single-f", kind: "single", quantity: "f"},
                {tag: "correlations", kind: "correlations"},
                {tag: "evolution", kind: "scan", mode: "evolution"},
                {tag: "stacked", kind: "scan", mode: "stacked"},
                {tag: "map", kind: "scan", mode: "map"},
                {tag: "structure-labels", kind: "powder", mode: "structure", field: "font"},
                {tag: "structure-axis-letters", kind: "powder", mode: "structure", field: "letterFont"}
            ];
        }
        function open(data) {
            const location = probe.project(data.kind);
            verify(String(location).startsWith("file:") && Session.openProject(location), "Every chart-font case opens its independent saved fixture through a valid private project URL");
            tryVerify(() => Session.project && !Session.project.calculating, 15000, "The saved fixture finishes its ordinary calculation before font comparison");
            if (data.kind === "correlations") {
                Session.project.fit.start();
                tryVerify(() => !Session.project.fit.running && Session.project.correlations.available >= 2, 15000, "The small saved polynomial fit supplies real correlation axis labels");
            }
            if (data.kind !== "single") {
                reference = powder.createObject(surface, {experiment: Session.project.currentExperiment});
                verify(reference !== null, "Every powder/scan comparison has a real Pattern axis-title reference");
            }
            if (data.mode === "structure") {
                Session.project.structureViewOptions.showLabels = true;
                Session.project.structureViewOptions.axes = true;
                chart = structure.createObject(surface, {structure: Session.project.currentStructure, options: Session.project.structureViewOptions});
            } else if (data.kind === "single") {
                Preferences.singleCrystalQuantity = data.quantity;
                chart = single.createObject(surface, {experiment: Session.project.currentExperiment});
                tryVerify(() => chart.models.some(model => model.calculatedShown), 15000, "The F or squared-F scatter has actual calculated reflections before checking ticks");
            } else if (data.kind === "scan") {
                chart = data.mode === "evolution" ? evolution.createObject(surface, {project: Session.project}) : scan.createObject(surface, {project: Session.project, mode: data.mode});
                tryVerify(() => data.mode === "evolution" ? chart.fitted : chart.hasData, 5000, "The real saved scan populates every requested scan chart");
            } else if (data.kind === "correlations") chart = correlations.createObject(surface, {project: Session.project});
            else chart = powder.createObject(surface, {experiment: Session.project.currentExperiment});
            verify(chart !== null, "Every requested chart is an actual production component");
            frame();
        }
        function inspect(data, phase) {
            const expected = titleFont(data);
            frame();
            if (data.mode === "structure") {
                const layer = named(chart, "structure.view.labels");
                verify(layer !== undefined && layer.visible && layer.count > 0, "The Structure view has actual populated painted labels");
                equal(layer[data.field], expected, data.tag + "/" + phase);
                console.log("CHART_FONT " + JSON.stringify({chart: data.tag, phase, family: layer[data.field].family, pixels: layer[data.field].pixelSize, count: layer.count}));
                return;
            }
            if (data.kind === "correlations") {
                verify(chart.count >= 2 && chart.namesShown, "Correlation row and column labels are enabled on a real matrix");
                const labels = texts(chart).filter(item => chart.labels.includes(item.text) || /^-?\d+\.\d+$/.test(item.text));
                verify(labels.length >= chart.count * 2, "The correlation font witness reaches both matrix edges and numeric colour-bar labels");
                chart.labels.forEach(label => verify(labels.filter(item => item.text === label).length >= 2, "Every real correlation parameter name is observed on both matrix axes"));
                labels.forEach(item => equal(item.font, expected, data.tag + "/" + item.text + "/" + phase));
                console.log("CHART_FONT " + JSON.stringify({chart: data.tag, phase, family: expected.family, pixels: expected.pixelSize, count: labels.length}));
                return;
            }
            let graph;
            if (data.kind === "powder") graph = named(chart, "chart.view." + data.pane);
            else if (data.kind === "scan") graph = named(chart, data.mode === "evolution" ? "evolution.view" : "scanView." + data.mode + ".axes");
            else graph = objects(chart).find(item => item.axisX !== undefined && item.axisY !== undefined && item.theme !== undefined);
            verify(graph !== undefined && graph.visible && graph.width > 0 && graph.height > 0, "Every requested pane has an actual visible Qt Graphs view");
            const titles = texts(chart).filter(item => /(?:^chart|^evolution|^scanView\.[^.]+)\.title\./.test(item.objectName) || data.kind === "single" && [chart.quantity + " calc", chart.quantity + " meas"].includes(item.text));
            verify(titles.length >= 2, "Every numeric chart exposes both of its actual axis titles for font comparison");
            titles.forEach(item => equal(item.font, expected, data.tag + "/title/" + phase));
            if (data.pane === "bragg") {
                const rows = objects(chart).filter(item => item.objectName === "chart.bragg.label" && item.visible);
                verify(rows.length > 0, "The Bragg strip has actual structure-name labels as well as its axis theme");
                rows.forEach(row => {
                    const names = texts(row).filter(item => item.isIcon !== true);
                    verify(names.length > 0, "Every Bragg structure label has real name text");
                    names.forEach(item => equal(item.font, expected, data.tag + "/structure-name/" + phase));
                });
            }
            if (data.mode === "map") for (const end of ["min", "max"]) {
                const label = named(chart, "scanView.map.colourBar." + end);
                verify(label !== undefined && label.visible && label.text.length > 0, "Each Map colour-bar endpoint has an actual numeric label");
                equal(label.font, expected, data.tag + "/colour-bar/" + phase);
            }
            // Expose each pane's labels even where a stacked pane normally shares its x labels below.
            graph.axisX.visible = true;
            graph.axisY.visible = true;
            graph.axisX.labelsVisible = true;
            graph.axisY.labelsVisible = true;
            equal(graph.theme.axisXLabelFont, expected, data.tag + "/axisXLabelFont/" + phase);
            equal(graph.theme.axisYLabelFont, expected, data.tag + "/axisYLabelFont/" + phase);
            frame();
            let labels = [];
            tryVerify(() => { labels = texts(graph).filter(item => /[0-9]/.test(item.text)); return labels.length >= 2; }, 2000, "Every requested chart and pane instantiates actual numeric tick text, rather than only a theme property");
            labels.forEach(item => equal(item.font, expected, data.tag + "/tick/" + phase));
            console.log("CHART_FONT " + JSON.stringify({chart: data.tag, phase, family: expected.family, pixels: expected.pixelSize, count: labels.length}));
        }
        function test_fonts(data) {
            open(data);
            inspect(data, "default");
            tryCompare(alternate, "status", FontLoader.Ready, 2000, "The font-family stimulus uses an actually bundled alternate face");
            verify(alternate.name !== Style.Fonts.fontFamily, "The shared-font stimulus changes family as well as nontrivial pixel size");
            Style.Fonts.ptSansRegular = alternate;
            Style.Sizes.fontPixelSize = originalSize + 5;
            inspect(data, "changed-shared-font");
            Style.Fonts.ptSansRegular = originalLoader;
            Style.Sizes.fontPixelSize = originalSize;
            inspect(data, "restored");
        }
    }
}
