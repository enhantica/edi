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
// pointer, a right click or the reset button shows every reflection again.
Item {
    id: chart

    objectName: "singleCrystal.chart"

    property ExperimentViewModel experiment: null
    readonly property SingleCrystalReflectionModel reflections: experiment ? experiment.singleCrystalReflections : null
    property FigureColors colors: FigureColors {}
    property bool shown: true

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
    // F² or F on both axes.
    readonly property bool squared: Preferences.singleCrystalQuantity !== "f"
    readonly property string quantity: squared ? "F²" : "F"
    // The shown ranges, [xMin, xMax, yMin, yMax]; empty: every reflection, on one range for both axes.
    property list<real> zoom: []
    readonly property real fullLow: !reflections ? 0 : squared ? reflections.low : reflections.lowF
    readonly property real fullHigh: !reflections ? 1 : squared ? reflections.high : reflections.highF
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

    function redraw() {
        if (!chart.reflections || !chart.shown)
            return;
        // Points only once F²calc is calculated: a reflection is placed by it.
        if (chart.reflections.calculatedShown && chart.squared)
            layer.setPoints(chart.reflections.calculated, chart.reflections.measured, chart.reflections.measuredSu);
        else if (chart.reflections.calculatedShown)
            layer.setPoints(chart.reflections.calculatedF, chart.reflections.measuredF, chart.reflections.measuredFSu);
        else
            layer.setPoints([], [], []);
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
    Connections {
        target: chart.reflections
        function onPointsChanged() {
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
        text: chart.reflections && !chart.reflections.calculatedShown ? qsTr("Not calculated yet") : ""
    }

    // The toolbar line, centred as the pattern chart's: what both axes plot, then the pattern chart's buttons.
    Row {
        id: toolbar

        x: Math.round(chart.toolbarLeft + (chart.width - chart.toolbarRightInset - chart.toolbarLeft - width) / 2)
        y: chart.topMargin
        spacing: EaStyle.Sizes.fontPixelSize * 0.5 + 2 * AppSizes.toolbarSpacing

        ToolbarComboBox {
            objectName: "singleCrystal.toolbar.quantity"
            toolTip: qsTr("Plotted quantity")
            model: [qsTr("F²"), qsTr("F")]
            closedTexts: [qsTr("axes: F²"), qsTr("axes: F")]
            currentIndex: chart.squared ? 0 : 1
            onActivated: index => Preferences.singleCrystalQuantity = index === 0 ? "f_squared" : "f"
        }
        // The pattern chart's toolbar, without the legend and the included-range buttons, which have nothing to
        // act on here; the tooltip toggle and the zoom or move mode are the same remembered settings.
        ChartToolbar {
            id: buttons

            legendAvailable: false
            includedRangeAvailable: false
            hoverShown: Preferences.chartHoverShown
            onHoverShownChanged: Preferences.chartHoverShown = hoverShown
            pointerMode: Preferences.chartPointerMode
            onPointerModeChanged: Preferences.chartPointerMode = pointerMode
            onResetClicked: chart.zoom = []
        }
    }

    GraphsView {
        id: view

        y: chart.topMargin + toolbar.height + chart.belowToolbar
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
        function read(px, py) {
            const model = chart.reflections;
            if (!model || !model.calculatedShown) {
                hide();
                return;
            }
            const xs = chart.squared ? model.calculated : model.calculatedF;
            const ys = chart.squared ? model.measured : model.measuredF;
            const sus = chart.squared ? model.measuredSu : model.measuredFSu;
            const span = axisX.max - axisX.min;
            let best = -1, bestDistance = chart.em * chart.em;
            for (let i = 0; i < xs.length; ++i) {
                const dx = (xs[i] - axisX.min) / span * plot.width - px;
                const dy = (1 - (ys[i] - axisY.min) / (axisY.max - axisY.min)) * plot.height - py;
                const distance = dx * dx + dy * dy;
                if (isFinite(distance) && distance < bestDistance) {
                    best = i;
                    bestDistance = distance;
                }
            }
            if (best < 0) {
                hide();
                return;
            }
            hoverText.text = model.hoverText(best, chart.squared);
            const atX = plot.x + (xs[best] - axisX.min) / span * plot.width;
            const atY = plot.y + (1 - (ys[best] - axisY.min) / (axisY.max - axisY.min)) * plot.height;
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

    EaElements.Label {
        x: view.x + view.plotArea.x + (view.plotArea.width - width) / 2
        y: view.y + view.height + chart.em * 0.6
        color: chart.colors.chartLabels
        text: qsTr("%1 calc").arg(chart.quantity)
    }
    EaElements.Label {
        x: chart.sideMargin - chart.em * 0.5
        y: view.y + view.plotArea.y + (view.plotArea.height + width) / 2
        rotation: -90
        transformOrigin: Item.TopLeft
        color: chart.colors.chartLabels
        text: qsTr("%1 meas").arg(chart.quantity)
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
        MeasuredLayer {
            id: layer

            objectName: "singleCrystal.points"
            anchors.fill: parent
            color: AppColors.experiment(0, chart.colors.isDarkPalette)
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
            readonly property bool zooming: pressed && (pressedButtons & Qt.LeftButton) && Preferences.chartPointerMode === "zoom"

            function xAt(px: real): real {
                return axisX.min + px / width * (axisX.max - axisX.min);
            }
            function yAt(py: real): real {
                return axisY.max - py / height * (axisY.max - axisY.min);
            }

            objectName: "singleCrystal.pointer"
            anchors.fill: parent
            acceptedButtons: Qt.LeftButton | Qt.RightButton
            hoverEnabled: Preferences.chartHoverShown
            onPressed: mouse => {
                pressX = lastX = mouse.x;
                pressY = lastY = mouse.y;
                hoverLabel.hide();
            }
            onPositionChanged: mouse => {
                if (pressed && (pressedButtons & Qt.LeftButton) && Preferences.chartPointerMode === "pan") {
                    const dx = (mouse.x - lastX) / width * (axisX.max - axisX.min);
                    const dy = (mouse.y - lastY) / height * (axisY.max - axisY.min);
                    chart.zoom = [axisX.min - dx, axisX.max - dx, axisY.min + dy, axisY.max + dy];
                    lastX = mouse.x;
                    lastY = mouse.y;
                }
                if (Preferences.chartHoverShown && !pressed)
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
                if (Preferences.chartPointerMode !== "zoom" || Math.abs(mouse.x - pressX) < chart.em * 0.3 || Math.abs(mouse.y - pressY) < chart.em * 0.3)
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
