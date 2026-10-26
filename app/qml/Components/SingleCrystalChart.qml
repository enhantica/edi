// SPDX-License-Identifier: BSD-3-Clause
pragma ComponentBehavior: Bound

import QtQuick
import QtGraphs

import EasyApplication.Gui.Style as EaStyle
import EasyApplication.Gui.Elements as EaElements

import edi.app

// A single crystal's F²calc against F²meas, or Fcalc against Fmeas (the toolbar's choice, kept in the preferences):
// each reflection a point with its su as an error bar, drawn as the pattern chart draws measured points
// (MeasuredLayer), and the y = x line a perfect model would put them on. A drag zooms to its box, the wheel about the
// pointer, a right click or the reset button shows every reflection again. A report figure draws the report model's
// `single_crystal` as it is, in F², with its reliability above the plot and no toolbar or pointer. Given several
// experiments (`stackedExperiments`, the Stacked tab of a project of single crystals) it draws all of them on the one
// chart, each in its experiment's colour, with the legend shown at first. There the selected experiment is drawn on top
// and the others faded while the app's "Highlight the selected dataset" setting is on; off, all are drawn alike and the
// legend marks the selected one. A click on a point selects its experiment (the owner, 2026-10-24).
Item {
    id: chart

    objectName: "singleCrystal.chart"

    property ExperimentViewModel experiment: null
    property list<ExperimentViewModel> stackedExperiments: []
    readonly property bool stacked: stackedExperiments.length > 0
    // The project whose selected experiment the Stacked chart shows and sets; its experiments are the stacked ones.
    property ProjectViewModel project: null
    readonly property int selectedIndex: stacked && project ? project.currentExperimentIndex : -1
    readonly property bool highlight: stacked && Preferences.chartHighlightSelected && selectedIndex >= 0
    readonly property SingleCrystalReflectionModel reflections: !stacked && experiment ? experiment.singleCrystalReflections : null
    // Every shown reflection model: the stacked experiments' or the one experiment's.
    readonly property list<SingleCrystalReflectionModel> models: {
        if (!stacked)
            return reflections ? [reflections] : [];
        const out = [];
        for (const shown of stackedExperiments)
            if (shown && shown.singleCrystalReflections)
                out.push(shown.singleCrystalReflections);
        return out;
    }
    // Bumped when any shown model's points change, so the bindings below read them again.
    property int revision: 0
    property FigureColors colors: FigureColors {}
    property bool shown: true
    // The report's input (edi ADR-0036): an experiment's `single_crystal` from the report model's JSON.
    property var reportData: null
    readonly property bool reportMode: reportData !== null
    // How faint the reflections the fit leaves out are drawn.
    readonly property real leftOutOpacity: 0.3
    readonly property bool calculated: {
        if (reportMode)
            return reportData.calc.length > 0;
        void revision;
        return models.some(model => model.calculatedShown);
    }
    // The report's range: every bar end and every F²calc, padded as the app pads its own.
    readonly property list<real> reportRange: {
        if (!reportMode)
            return [0, 1];
        let low = Infinity, high = -Infinity;
        for (let i = 0; i < reportData.meas.length; ++i) {
            for (const end of [reportData.meas[i] - reportData.su[i], reportData.meas[i] + reportData.su[i], reportData.calc[i]]) {
                if (isFinite(end)) {
                    low = Math.min(low, end);
                    high = Math.max(high, end);
                }
            }
        }
        if (!(high > low))
            return [0, 1];
        const pad = (high - low) * 0.05;
        return [Math.min(0, low - pad), high + pad];
    }

    readonly property real em: EaStyle.Sizes.fontPixelSize
    // The pattern chart's layout: the toolbar line a gap below the page's block selector row, centred over the plot,
    // and the plot the main area's margin below it.
    readonly property real sideMargin: AppSizes.mainAreaMargin
    readonly property real topMargin: em
    readonly property real belowToolbar: AppSizes.mainAreaMargin
    readonly property real toolbarLeft: AppSizes.mainAreaMargin
    readonly property real toolbarRightInset: width - (view.x + view.plotArea.x + view.plotArea.width)
    readonly property real titleGutter: Math.round(em * 1.6)
    readonly property real xTitleHeight: Math.round(em * 1.7)
    readonly property int xTicks: Math.max(2, Math.min(8, Math.round(width / (em * 6))))
    readonly property int yTicks: Math.max(2, Math.min(6, Math.floor((height - em * 7 - xTitleHeight) / (em * 2.5))))
    // F² or F on both axes, each titled by its item's dictionary label (edi ADR-0051).
    readonly property bool squared: reportMode || Preferences.singleCrystalQuantity !== "f"
    readonly property string calculatedItem: squared ? "refln.intensity_calc" : "refln.f_calc"
    readonly property string measuredItem: squared ? "refln.intensity_meas" : "refln.f_meas"
    // The shown ranges, [xMin, xMax, yMin, yMax]; empty: every reflection, on one range for both axes.
    property list<real> zoom: []
    readonly property real fullLow: {
        if (reportMode)
            return reportRange[0];
        void revision;
        const lows = models.filter(model => model.calculatedShown).map(model => squared ? model.low : model.lowF).filter(isFinite);
        return lows.length > 0 ? Math.min(...lows) : 0;
    }
    readonly property real fullHigh: {
        if (reportMode)
            return reportRange[1];
        void revision;
        const highs = models.filter(model => model.calculatedShown).map(model => squared ? model.high : model.highF).filter(isFinite);
        return highs.length > 0 ? Math.max(...highs) : 1;
    }
    // The legend: the Stacked chart's experiments, or the one experiment, each name in its points' colour.
    // Sets the legend: the experiments shown, each in its colour, and the selected one marked when the chart does not
    // highlight it.
    function updateLegend() {
        const named = chart.stacked ? chart.stackedExperiments : chart.experiment ? [chart.experiment] : [];
        legendRows.setRows(named.map(shown => shown ? shown.name : ""), named.map((shown, index) => String(AppColors.experiment(chart.stacked ? index : 0, chart.colors.isDarkPalette))), chart.stacked && !Preferences.chartHighlightSelected ? chart.selectedIndex : -1);
    }
    ListedLegendModel {
        id: legendRows
    }
    readonly property real xLow: zoom.length === 4 ? zoom[0] : fullLow
    readonly property real xHigh: zoom.length === 4 ? zoom[1] : fullHigh
    readonly property real yLow: zoom.length === 4 ? zoom[2] : fullLow
    readonly property real yHigh: zoom.length === 4 ? zoom[3] : fullHigh

    function niceStep(span, count) {
        if (!(span > 0))
            return 1;
        const raw = span / count;
        const power = Math.pow(10, Math.floor(Math.log10(raw)));
        const scaled = raw / power;
        return (scaled < 1.5 ? 1 : scaled < 3.5 ? 2 : scaled < 7.5 ? 5 : 10) * power;
    }

    // The points the fit uses (`want` true) or leaves out (false) of three parallel lists, by the model's `used`;
    // a report's points are all used.
    function part(x, y, su, used, want) {
        const out = [[], [], []];
        for (let i = 0; i < x.length; ++i) {
            if ((used && i < used.length ? used[i] : true) === want) {
                out[0].push(x[i]);
                out[1].push(y[i]);
                out[2].push(su[i]);
            }
        }
        return out;
    }
    // Draws a model's points on `usedLayer` and the ones its fit leaves out, dimmed, on `leftOutLayer`.
    function drawModel(model, usedLayer, leftOutLayer) {
        if (!model || !chart.shown || !model.calculatedShown) {
            usedLayer.setPoints([], [], []);
            leftOutLayer.setPoints([], [], []);
            return;
        }
        const x = chart.squared ? model.calculated : model.calculatedF;
        const y = chart.squared ? model.measured : model.measuredF;
        const su = chart.squared ? model.measuredSu : model.measuredFSu;
        const used = part(x, y, su, model.used, true);
        const left = part(x, y, su, model.used, false);
        usedLayer.setPoints(used[0], used[1], used[2]);
        leftOutLayer.setPoints(left[0], left[1], left[2]);
    }

    // Each Stacked layer draws its experiment again.
    signal redrawStacked

    function redraw() {
        chart.updateLegend();
        if (chart.stacked) {
            chart.redrawStacked();
            return;
        }
        if (chart.reportMode) {
            if (chart.calculated)
                layer.setPoints(chart.reportData.calc, chart.reportData.meas, chart.reportData.su);
            else
                layer.setPoints([], [], []);
            leftOutLayer.setPoints([], [], []);
            return;
        }
        if (!chart.reflections || !chart.shown)
            return;
        // Points only once F²calc is calculated: a reflection is placed by it.
        chart.drawModel(chart.reflections, layer, leftOutLayer);
    }

    // The y = x line across whatever both axes show.
    function drawDiagonal() {
        const from = Math.min(chart.xLow, chart.yLow);
        const to = Math.max(chart.xHigh, chart.yHigh);
        diagonal.clear();
        diagonal.append(from, from);
        diagonal.append(to, to);
    }

    onXLowChanged: drawDiagonal()
    onXHighChanged: drawDiagonal()
    onYLowChanged: drawDiagonal()
    onYHighChanged: drawDiagonal()
    Component.onCompleted: drawDiagonal()
    onShownChanged: redraw()
    onSquaredChanged: {
        zoom = [];
        redraw();
    }
    onReflectionsChanged: redraw()
    onReportDataChanged: redraw()
    onStackedExperimentsChanged: redraw()
    onSelectedIndexChanged: chart.updateLegend()
    Connections {
        target: Preferences
        function onChartHighlightSelectedChanged() {
            chart.updateLegend();
        }
    }
    Connections {
        target: chart.reflections
        function onPointsChanged() {
            chart.revision++;
            chart.redraw();
        }
    }

    Rectangle {
        anchors.fill: parent
        color: chart.colors.chartBackground
    }

    EaElements.Label {
        x: chart.toolbarLeft
        y: chart.topMargin + (toolbar.height - height) / 2
        color: chart.colors.chartLabels
        text: (chart.reportMode || chart.reflections) && !chart.calculated ? qsTr("Not calculated yet") : ""
    }
    // A report figure's reliability (edi::reliability_text), above its plot at the left, as the pattern chart's.
    EaElements.Label {
        objectName: "singleCrystal.reliability"
        visible: chart.reportMode && text !== ""
        x: view.x + view.plotArea.x
        y: Math.max(0, view.y + view.plotArea.y - height - Math.round(chart.em * 0.25))
        color: chart.colors.chartLabels
        text: chart.reportMode ? chart.reportData.title : ""
    }

    // The toolbar line, centred as the pattern chart's: what both axes plot, then the pattern chart's buttons.
    Row {
        id: toolbar

        visible: !chart.reportMode
        x: Math.round(chart.toolbarLeft + (chart.width - chart.toolbarRightInset - chart.toolbarLeft - width) / 2)
        y: chart.topMargin
        spacing: EaStyle.Sizes.fontPixelSize * 0.5 + 2 * AppSizes.toolbarSpacing

        ToolbarComboBox {
            objectName: "singleCrystal.toolbar.quantity"
            toolTip: qsTr("Plotted quantity")
            model: [qsTr("F²"), qsTr("F")]
            closedTexts: [qsTr("axes: F²"), qsTr("axes: F")]
            shownIndex: chart.squared ? 0 : 1
            onActivated: index => Preferences.singleCrystalQuantity = index === 0 ? "f_squared" : "f"
        }
        // The pattern chart's toolbar, without the included-range button, which has nothing to act on here; the
        // tooltip toggle and the zoom or move mode are the same remembered settings.
        ChartToolbar {
            id: buttons

            // The legend starts shown on the Stacked chart and hidden on the Pattern chart, which follows the
            // pattern charts' remembered choice.
            legendShown: chart.stacked ? true : Preferences.patternLegendShown
            onLegendShownChanged: {
                if (!chart.stacked)
                    Preferences.patternLegendShown = legendShown;
            }
            includedRangeAvailable: false
            hoverShown: Preferences.patternHoverShown
            onHoverShownChanged: Preferences.patternHoverShown = hoverShown
            pointerMode: Preferences.patternPointerMode
            onPointerModeChanged: Preferences.patternPointerMode = pointerMode
            onResetClicked: chart.zoom = []
        }
        // On the Stacked chart: the selected experiment on top and the others faded, or all alike. One app setting for
        // every chart of several datasets.
        ChartToolButton {
            objectName: "singleCrystal.toolbar.highlight"
            visible: chart.stacked
            fontIcon: "highlighter"
            toolTip: qsTr("Highlight the selected dataset")
            checked: Preferences.chartHighlightSelected
            onClicked: Preferences.chartHighlightSelected = !Preferences.chartHighlightSelected
        }
        // A click on a button sets the toolbar's own value, which ends the bindings above; these follow the
        // remembered settings again whenever another chart changes them.
        Binding {
            target: buttons
            property: "hoverShown"
            value: Preferences.patternHoverShown
        }
        Binding {
            target: buttons
            property: "pointerMode"
            value: Preferences.patternPointerMode
        }
    }

    GraphsView {
        id: view

        y: chart.reportMode ? chart.topMargin + Math.round(chart.em * 1.5) : chart.topMargin + toolbar.height + chart.belowToolbar
        width: parent.width
        height: parent.height - y - chart.xTitleHeight - chart.em
        marginLeft: chart.sideMargin + chart.titleGutter
        marginRight: chart.sideMargin
        marginTop: 0
        marginBottom: 0
        theme: GraphsTheme {
            colorScheme: GraphsTheme.ColorScheme.Light
            backgroundVisible: false
            plotAreaBackgroundVisible: false
            labelTextColor: chart.colors.chartLabels
            labelFont.family: EaStyle.Fonts.fontFamily
            labelFont.pixelSize: EaStyle.Sizes.fontPixelSize
            axisX.mainColor: "transparent"
            axisX.subColor: "transparent"
            axisY.mainColor: "transparent"
            axisY.subColor: "transparent"
            grid.mainColor: "transparent"
            grid.subColor: "transparent"
        }
        axisX: ValueAxis {
            id: axisX
            min: chart.xLow
            max: chart.xHigh
            tickInterval: chart.niceStep(max - min, chart.xTicks)
            tickAnchor: 0
            lineVisible: false
            gridVisible: false
            subGridVisible: false
        }
        axisY: ValueAxis {
            id: axisY
            min: chart.yLow
            max: chart.yHigh
            tickInterval: chart.niceStep(max - min, chart.yTicks)
            tickAnchor: 0
            lineVisible: false
            gridVisible: false
            subGridVisible: false
        }
        // The y = x line, on the chart's own axes, refilled whenever their range changes.
        LineSeries {
            id: diagonal
            color: chart.colors.chartAxis
            width: 1
        }
    }

    // The hover read-out of the reflection nearest the pointer (within about an em): h k l, the measured value with
    // its su and the calculated one, in the plotted quantity; the pattern chart's look.
    Rectangle {
        id: hoverLabel

        function hide() {
            hoverText.text = "";
        }
        // The reflection nearest the pointer, within about an em: its model's place and its row; null when none.
        function nearest(px, py) {
            const span = axisX.max - axisX.min;
            let best = -1, bestDistance = chart.em * chart.em, bestModel = -1, xs = [], ys = [];
            for (let m = 0; m < chart.models.length; ++m) {
                const model = chart.models[m];
                if (!model.calculatedShown)
                    continue;
                const mx = chart.squared ? model.calculated : model.calculatedF;
                const my = chart.squared ? model.measured : model.measuredF;
                for (let i = 0; i < mx.length; ++i) {
                    const dx = (mx[i] - axisX.min) / span * plot.width - px;
                    const dy = (1 - (my[i] - axisY.min) / (axisY.max - axisY.min)) * plot.height - py;
                    const distance = dx * dx + dy * dy;
                    if (isFinite(distance) && distance < bestDistance) {
                        best = i;
                        bestDistance = distance;
                        bestModel = m;
                        xs = mx;
                        ys = my;
                    }
                }
            }
            return best < 0 ? null : {
                "model": bestModel,
                "row": best,
                "x": xs[best],
                "y": ys[best]
            };
        }
        function read(px, py) {
            const hit = nearest(px, py);
            if (hit === null) {
                hide();
                return;
            }
            const span = axisX.max - axisX.min;
            const text = chart.models[hit.model].hoverText(hit.row, chart.squared);
            hoverText.text = chart.stacked ? "<b>" + chart.stackedExperiments[hit.model].name + "</b><br>" + text : text;
            const atX = plot.x + (hit.x - axisX.min) / span * plot.width;
            const atY = plot.y + (1 - (hit.y - axisY.min) / (axisY.max - axisY.min)) * plot.height;
            x = atX + chart.em + width <= chart.width ? atX + chart.em : atX - chart.em - width;
            y = atY - height - chart.em * 0.5 >= 0 ? atY - height - chart.em * 0.5 : atY + chart.em;
        }

        objectName: "singleCrystal.hover"
        z: 2
        visible: hoverText.text !== ""
        width: hoverText.implicitWidth + chart.em
        height: hoverText.implicitHeight + chart.em * 0.5
        color: chart.colors.mainContentBackgroundHalfTransparent
        border.color: chart.colors.chartGridLine
        border.width: EaStyle.Sizes.borderThickness

        EaElements.Label {
            id: hoverText
            anchors.centerIn: parent
            textFormat: Text.RichText
            color: chart.colors.themeForeground
        }
    }

    // The legend, inside the plot's top left corner, behind the toolbar's legend button.
    ChartLegend {
        objectName: "singleCrystal.legend"
        z: 1
        colors: chart.colors
        x: view.x + view.plotArea.x + chart.em
        y: view.y + view.plotArea.y + chart.em
        visible: !chart.reportMode && buttons.legendShown && chart.models.length > 0
        entries: legendRows
    }

    EaElements.Label {
        x: view.x + view.plotArea.x + (view.plotArea.width - width) / 2
        y: view.y + view.height + chart.em * 0.6
        color: chart.colors.chartLabels
        text: Session.label(chart.calculatedItem)
    }
    EaElements.Label {
        x: chart.sideMargin - chart.em * 0.5
        y: view.y + view.plotArea.y + (view.plotArea.height + width) / 2
        rotation: -90
        transformOrigin: Item.TopLeft
        color: chart.colors.chartLabels
        text: Session.label(chart.measuredItem)
    }

    Item {
        id: plot

        x: view.x + view.plotArea.x
        y: view.y + view.plotArea.y
        width: view.plotArea.width
        height: view.plotArea.height
        clip: true

        function ticks(axis: ValueAxis): list<real> {
            const out = [];
            const span = axis.max - axis.min;
            if (!(axis.tickInterval > 0) || !(span > 0))
                return out;
            for (let i = Math.ceil(axis.min / axis.tickInterval - 1e-9); out.length < 64; ++i) {
                const share = (i * axis.tickInterval - axis.min) / span;
                if (share > 1 + 1e-9)
                    break;
                out.push(share);
            }
            return out;
        }

        Repeater {
            model: plot.ticks(axisX)
            delegate: Rectangle {
                required property real modelData
                x: Math.round(modelData * plot.width)
                width: 1
                height: plot.height
                color: chart.colors.chartGridLine
            }
        }
        Repeater {
            model: plot.ticks(axisY)
            delegate: Rectangle {
                required property real modelData
                y: Math.round((1 - modelData) * plot.height)
                width: plot.width
                height: 1
                color: chart.colors.chartGridLine
            }
        }
        // The Stacked chart's experiments, one layer each in its colour, drawn in the project's order.
        Repeater {
            id: stackedLayers

            model: chart.stacked ? chart.stackedExperiments : []
            delegate: MeasuredLayer {
                id: stackedLayer

                required property ExperimentViewModel modelData
                required property int index
                readonly property SingleCrystalReflectionModel model: modelData ? modelData.singleCrystalReflections : null

                function redraw() {
                    chart.drawModel(model, stackedLayer, stackedLeftOut);
                }

                objectName: "singleCrystal.points." + index
                anchors.fill: parent
                // The selected experiment on top and every other faded, while highlighting.
                z: chart.highlight && index === chart.selectedIndex ? 1 : 0
                opacity: chart.highlight && index !== chart.selectedIndex ? Preferences.chartFadedOpacity : 1
                color: AppColors.experiment(index, chart.colors.isDarkPalette)
                markerSize: 5
                xMin: axisX.min
                xMax: axisX.max
                yMin: axisY.min
                yMax: axisY.max
                Component.onCompleted: redraw()
                Connections {
                    target: stackedLayer.model
                    function onPointsChanged() {
                        chart.revision++;
                        stackedLayer.redraw();
                    }
                }
                Connections {
                    target: chart
                    function onRedrawStacked() {
                        stackedLayer.redraw();
                    }
                }
                // The reflections this experiment's fit leaves out, dimmed.
                MeasuredLayer {
                    id: stackedLeftOut

                    objectName: "singleCrystal.leftOut." + stackedLayer.index
                    anchors.fill: parent
                    opacity: chart.leftOutOpacity
                    color: stackedLayer.color
                    markerSize: 5
                    xMin: axisX.min
                    xMax: axisX.max
                    yMin: axisY.min
                    yMax: axisY.max
                }
            }
        }
        MeasuredLayer {
            id: layer

            objectName: "singleCrystal.points"
            visible: !chart.stacked
            anchors.fill: parent
            color: AppColors.experiment(0, chart.colors.isDarkPalette)
            markerSize: 5
            xMin: axisX.min
            xMax: axisX.max
            yMin: axisY.min
            yMax: axisY.max
        }
        // The reflections the fit leaves out (its cutoff), dimmed; the hover says why.
        MeasuredLayer {
            id: leftOutLayer

            objectName: "singleCrystal.leftOut"
            visible: !chart.stacked
            anchors.fill: parent
            opacity: chart.leftOutOpacity
            color: layer.color
            markerSize: 5
            xMin: axisX.min
            xMax: axisX.max
            yMin: axisY.min
            yMax: axisY.max
        }
        Rectangle {
            anchors.fill: parent
            color: "transparent"
            border.color: chart.colors.chartAxis
            border.width: 1
        }
        // The pointer, as on the pattern chart: a box zoom or a move by dragging, by the toolbar's mode; a zoom about
        // the pointer by the wheel; a reset by a right click; the nearest reflection's read-out while hovering.
        MouseArea {
            id: pointer

            property real pressX: 0
            property real pressY: 0
            property real lastX: 0
            property real lastY: 0
            readonly property bool zooming: pressed && (pressedButtons & Qt.LeftButton) && Preferences.patternPointerMode === "zoom"

            function xAt(px: real): real {
                return axisX.min + px / width * (axisX.max - axisX.min);
            }
            function yAt(py: real): real {
                return axisY.max - py / height * (axisY.max - axisY.min);
            }

            objectName: "singleCrystal.pointer"
            anchors.fill: parent
            // A report figure has no pointer, so the wheel scrolls the report.
            enabled: !chart.reportMode
            acceptedButtons: Qt.LeftButton | Qt.RightButton
            hoverEnabled: Preferences.patternHoverShown
            onPressed: mouse => {
                pressX = lastX = mouse.x;
                pressY = lastY = mouse.y;
                hoverLabel.hide();
            }
            onPositionChanged: mouse => {
                if (pressed && (pressedButtons & Qt.LeftButton) && Preferences.patternPointerMode === "pan") {
                    const dx = (mouse.x - lastX) / width * (axisX.max - axisX.min);
                    const dy = (mouse.y - lastY) / height * (axisY.max - axisY.min);
                    chart.zoom = [axisX.min - dx, axisX.max - dx, axisY.min + dy, axisY.max + dy];
                    lastX = mouse.x;
                    lastY = mouse.y;
                }
                if (Preferences.patternHoverShown && !pressed)
                    hoverLabel.read(mouse.x, mouse.y);
                else
                    hoverLabel.hide();
            }
            onExited: hoverLabel.hide()
            onReleased: mouse => {
                if (mouse.button === Qt.RightButton) {
                    chart.zoom = [];
                    return;
                }
                // A click on the Stacked chart (not a drag) selects the experiment of the reflection under it.
                if (chart.stacked && chart.project && Math.abs(mouse.x - pressX) < chart.em * 0.3 && Math.abs(mouse.y - pressY) < chart.em * 0.3) {
                    const hit = hoverLabel.nearest(mouse.x, mouse.y);
                    if (hit !== null)
                        chart.project.currentExperimentIndex = hit.model;
                    return;
                }
                if (Preferences.patternPointerMode !== "zoom" || Math.abs(mouse.x - pressX) < chart.em * 0.3 || Math.abs(mouse.y - pressY) < chart.em * 0.3)
                    return;
                const box = [xAt(Math.min(pressX, mouse.x)), xAt(Math.max(pressX, mouse.x)), yAt(Math.max(pressY, mouse.y)), yAt(Math.min(pressY, mouse.y))];
                if (box[1] > box[0] && box[3] > box[2] && isFinite(box[1] - box[0]) && isFinite(box[3] - box[2]))
                    chart.zoom = box;
            }
            onWheel: wheel => {
                if (wheel.angleDelta.y === 0)
                    return;
                const factor = Math.pow(0.8, wheel.angleDelta.y / 120);
                const ax = xAt(wheel.x), ay = yAt(wheel.y);
                const box = [ax - (ax - axisX.min) * factor, ax + (axisX.max - ax) * factor, ay - (ay - axisY.min) * factor, ay + (axisY.max - ay) * factor];
                if (box.every(isFinite) && box[1] > box[0] && box[3] > box[2])
                    chart.zoom = box;
            }

            // The box being dragged, as the pattern chart draws it.
            Rectangle {
                objectName: "singleCrystal.zoom.box"
                visible: pointer.zooming
                x: Math.min(pointer.pressX, pointer.mouseX)
                y: Math.min(pointer.pressY, pointer.mouseY)
                width: Math.abs(pointer.mouseX - pointer.pressX)
                height: Math.abs(pointer.mouseY - pointer.pressY)
                color: "transparent"
                border.color: chart.colors.appBorder
                border.width: EaStyle.Sizes.borderThickness
                opacity: 0.9

                Rectangle {
                    anchors.fill: parent
                    opacity: 0.5
                    color: chart.colors.appBorder
                }
            }
        }
    }
}
