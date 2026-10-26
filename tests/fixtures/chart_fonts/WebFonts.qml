// SPDX-License-Identifier: BSD-3-Clause
import QtQuick
import QtQuick.Window
import edi.app
import ChartFontAcceptance 1.0
import EasyApplication.Gui.Style as Style

Window {
    id: window
    visible: true; width: 1280; height: 900
    ChartFontProbe { id: probe }
    FontLoader { id: alternate; source: "qrc:/qt/qml/EasyApplication/Gui/Resources/Fonts/Noto_Sans/NotoSans-Regular.ttf" }
    Item { id: surface; anchors.fill: parent }
    Component { id: powder; PatternChart { anchors.fill: parent; shown: true } }
    Component { id: single; SingleCrystalChart { anchors.fill: parent; shown: true } }
    Component { id: scan; ScanViewChart { anchors.fill: parent; shown: true } }
    Component { id: evolution; EvolutionChart { anchors.fill: parent; shown: true } }
    Component { id: correlations; CorrelationChart { anchors.fill: parent; shown: true; namesShown: true } }
    Component { id: structure; StructureView { anchors.fill: parent; shown: true } }
    property var inventory: probe.cases()
    property int index: -1
    property string stage: "next"
    onStageChanged: console.log("FONT_STAGE " + (currentCase ? currentCase.tag : "startup") + " " + stage)
    property real deadline: 0
    property real after: 0
    property var chart: null
    property var reference: null
    property var currentCase: null
    property var results: ({})
    property var originalLoader: null
    property var originalBoldLoader: null
    property int originalSize: 0
    Component.onCompleted: {
        originalLoader = Style.Fonts.ptSansRegular;
        originalBoldLoader = Style.Fonts.ptSansBold;
        originalSize = Style.Sizes.fontPixelSize;
    }
    Timer { interval: 40; repeat: true; running: true; onTriggered: window.step() }
    function objects(root) { return Array.from(probe.objects(root)); }
    function named(root, name) { return objects(root).find(item => item.objectName === name); }
    function texts(root) { return objects(root).filter(item => probe.nativeText(item) && item.visible && item.width > 0 && item.height > 0 && typeof item.text === "string" && item.text !== ""); }
    function font(font, role) { return {role, family: String(font.family), pixels: Number(font.pixelSize)}; }
    function graph() {
        if (currentCase.kind === "powder") return named(chart, "chart.view." + currentCase.pane);
        if (currentCase.kind === "scan") return named(chart, currentCase.mode === "evolution" ? "evolution.view" : "scanView." + currentCase.mode + ".axes");
        return objects(chart).find(item => item.axisX !== undefined && item.axisY !== undefined && item.theme !== undefined);
    }
    function ready() {
        if (!chart || Session.project.calculating) return false;
        if (currentCase.kind === "correlations") return chart.count >= 2;
        if (currentCase.mode === "structure") { const layer = named(chart, "structure.view.labels"); return layer && layer.count > 0; }
        if (currentCase.kind === "single" && !chart.models.some(model => model.calculatedShown)) return false;
        if (currentCase.kind === "scan" && !(currentCase.mode === "evolution" ? chart.fitted : chart.hasData)) return false;
        const view = graph();
        if (!view || !view.visible) return false;
        if (currentCase.kind !== "scan") {
            view.axisX.visible = true; view.axisY.visible = true;
            view.axisX.labelsVisible = true; view.axisY.labelsVisible = true;
        }
        return texts(view).filter(item => /[0-9]/.test(item.text)).length >= 2;
    }
    function snapshot() {
        let title;
        if (currentCase.kind === "single") title = texts(chart).find(item => item.text === chart.quantity + " calc");
        else if (currentCase.mode === "structure" || currentCase.kind === "correlations") title = named(reference, "chart.title.x");
        else title = named(chart, currentCase.kind === "powder" ? "chart.title.x" : currentCase.mode === "evolution" ? "evolution.title.x" : "scanView." + currentCase.mode + ".title.x");
        if (!title || !title.text) throw new Error("The actual axis-title reference is absent");
        const fields = [], counts = {};
        function add(items, role) { counts[role] = items.length; items.forEach(item => fields.push(font(item.font, role))); }
        if (currentCase.mode === "structure") {
            const layer = named(chart, "structure.view.labels");
            counts.painted = layer.count;
            fields.push(font(layer[currentCase.field], "painted"));
        } else if (currentCase.kind === "correlations") {
            add(texts(chart).filter(item => chart.labels.includes(item.text)), "matrix-names");
            add(texts(chart).filter(item => /^-?\d+\.\d+$/.test(item.text)), "key");
            counts.parameters = chart.count;
        } else {
            const view = graph();
            fields.push(font(view.theme.axisXLabelFont, "x-theme"), font(view.theme.axisYLabelFont, "y-theme"));
            add(texts(view).filter(item => /[0-9]/.test(item.text)), "ticks");
            add(texts(chart).filter(item => /(?:^chart|^evolution|^scanView\.[^.]+)\.title\./.test(item.objectName) || currentCase.kind === "single" && [chart.quantity + " calc", chart.quantity + " meas"].includes(item.text)), "titles");
            if (currentCase.pane === "bragg") {
                const rows = objects(chart).filter(item => item.objectName === "chart.bragg.label" && item.visible);
                counts.structures = rows.length;
                rows.forEach(row => add(texts(row).filter(item => item.isIcon !== true), "structure-name"));
            }
            if (currentCase.kind === "scan" && currentCase.mode !== "evolution") {
                counts.rowLabels = chart.rowLabels;
                const rows = objects(chart).filter(item => item.objectName.startsWith("scanView." + currentCase.mode + ".rowLabel.") && item.visible);
                add(rows.flatMap(row => texts(row).filter(item => item.isIcon !== true)), "row-names");
            }
            if (currentCase.mode === "map") add([named(chart, "scanView.map.colourBar.min"), named(chart, "scanView.map.colourBar.max")].filter(item => item && item.visible && item.text), "key");
        }
        return {title: font(title.font, "reference"), app: {family: String(Style.Fonts.fontFamily), pixels: Number(Style.Sizes.fontPixelSize)}, fields, counts};
    }
    function cleanup() {
        if (chart) chart.destroy(); if (reference) reference.destroy();
        chart = null; reference = null;
        Session.closeProject();
        Style.Fonts.ptSansRegular = originalLoader; Style.Fonts.ptSansBold = originalBoldLoader; Style.Sizes.fontPixelSize = originalSize;
        Preferences.resetToDefaults();
    }
    function step() {
        try {
            if (stage === "done") return;
            if (stage !== "next" && Date.now() > deadline) throw new Error("The actual chart did not populate before its case deadline");
            if (stage === "next") {
                cleanup(); ++index;
                if (index >= inventory.length) { stage = "done"; probe.publish({backend: "browser", cases: results}); return; }
                currentCase = inventory[index]; results[currentCase.tag] = {}; console.log("FONT_CASE " + currentCase.tag);
                const location = probe.project(currentCase.kind);
                if (!String(location).startsWith("file:") || !Session.openProject(location)) throw new Error("The saved private fixture cannot be opened: " + location + ": " + Session.lastError);
                deadline = Date.now() + 15000; stage = "loaded"; return;
            }
            if (stage === "loaded") {
                if (Session.project.calculating) return;
                if (currentCase.kind === "correlations") { Session.project.fit.start(); stage = "fitted"; return; }
                stage = "create";
            }
            if (stage === "fitted") {
                if (Session.project.fit.running || Session.project.correlations.available < 2) return;
                stage = "create";
            }
            if (stage === "create") {
                if (currentCase.mode === "structure" || currentCase.kind === "correlations") reference = powder.createObject(surface, {experiment: Session.project.currentExperiment});
                if (currentCase.mode === "structure") {
                    Session.project.structureViewOptions.showLabels = true; Session.project.structureViewOptions.axes = true;
                    chart = structure.createObject(surface, {structure: Session.project.currentStructure, options: Session.project.structureViewOptions});
                } else if (currentCase.kind === "single") { Preferences.singleCrystalQuantity = currentCase.quantity; chart = single.createObject(surface, {experiment: Session.project.currentExperiment}); }
                else if (currentCase.kind === "scan") chart = currentCase.mode === "evolution" ? evolution.createObject(surface, {project: Session.project}) : scan.createObject(surface, {project: Session.project, mode: currentCase.mode});
                else if (currentCase.kind === "correlations") chart = correlations.createObject(surface, {project: Session.project});
                else chart = powder.createObject(surface, {experiment: Session.project.currentExperiment});
                stage = "ready"; return;
            }
            if (stage === "ready") { if (!ready() || alternate.status !== FontLoader.Ready) return; after = Date.now() + 160; stage = "default"; return; }
            if (Date.now() < after || !ready()) return;
            if (stage === "default") { results[currentCase.tag].default = snapshot(); Style.Fonts.ptSansRegular = alternate; Style.Fonts.ptSansBold = alternate; Style.Sizes.fontPixelSize = originalSize + 5; after = Date.now() + 160; stage = "changed"; }
            else if (stage === "changed") { results[currentCase.tag].changed = snapshot(); Style.Fonts.ptSansRegular = originalLoader; Style.Fonts.ptSansBold = originalBoldLoader; Style.Sizes.fontPixelSize = originalSize; after = Date.now() + 160; stage = "restored"; }
            else if (stage === "restored") { results[currentCase.tag].restored = snapshot(); stage = "next"; }
        } catch (error) { if (currentCase) results[currentCase.tag].error = stage + ": " + String(error); else results.startupError = String(error); stage = "next"; }
    }
}
