// SPDX-License-Identifier: BSD-3-Clause
pragma ComponentBehavior: Bound

import QtQuick
import QtGraphs

import EasyApplication.Gui.Style as EaStyle
import EasyApplication.Gui.Elements as EaElements

import edi.app

// A single crystal's F²calc against F²meas: each reflection a point with its su as an error bar, drawn as the
// pattern chart draws measured points (MeasuredLayer), and the y = x line a perfect model would put them on. A drag
// zooms to its box, the wheel about the pointer, a right click or the reset button shows every reflection again.
Item {
    id: chart

    objectName: "singleCrystal.chart"

    property ExperimentViewModel experiment: null
    readonly property SingleCrystalReflectionModel reflections: experiment ? experiment.singleCrystalReflections : null
    property FigureColors colors: FigureColors {}
    property bool shown: true

    readonly property real em: EaStyle.Sizes.fontPixelSize
    readonly property real sideMargin: AppSizes.mainAreaMargin
    readonly property real toolbarRightInset: sideMargin
    readonly property real titleGutter: Math.round(em * 1.6)
    readonly property real xTitleHeight: Math.round(em * 1.7)
    readonly property int xTicks: Math.max(2, Math.min(8, Math.round(width / (em * 6))))
    readonly property int yTicks: Math.max(2, Math.min(6, Math.floor((height - em * 7 - xTitleHeight) / (em * 2.5))))
    // The zoomed range, [min, max] on both axes; empty: every reflection.
    property list<real> zoom: []
    readonly property real low: zoom.length === 2 ? zoom[0] : reflections ? reflections.low : 0
    readonly property real high: zoom.length === 2 ? zoom[1] : reflections ? reflections.high : 1

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
        layer.setPoints(chart.reflections.calculated, chart.reflections.measured, chart.reflections.measuredSu);
    }

    onShownChanged: redraw()
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

    Row {
        id: toolbar

        x: chart.sideMargin
        y: chart.em * 0.5
        spacing: AppSizes.toolbarSpacing
        EaElements.Label {
            anchors.verticalCenter: parent.verticalCenter
            color: chart.colors.chartLabels
            text: chart.reflections && !chart.reflections.calculatedShown ? qsTr("Not calculated yet") : ""
        }
    }
    ChartToolButton {
        objectName: "singleCrystal.toolbar.reset"
        anchors.right: parent.right
        anchors.rightMargin: chart.toolbarRightInset
        y: chart.em * 0.5
        fontIcon: "home"
        toolTip: qsTr("Reset axes")
        onClicked: chart.zoom = []
    }

    GraphsView {
        id: view

        y: chart.em * 2.75
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
            min: chart.low
            max: chart.high
            tickInterval: chart.niceStep(max - min, chart.xTicks)
            tickAnchor: 0
            lineVisible: false
            gridVisible: false
            subGridVisible: false
        }
        axisY: ValueAxis {
            id: axisY
            min: chart.low
            max: chart.high
            tickInterval: chart.niceStep(max - min, chart.yTicks)
            tickAnchor: 0
            lineVisible: false
            gridVisible: false
            subGridVisible: false
        }
        // The y = x line.
        LineSeries {
            color: chart.colors.chartAxis
            width: 1
            XYPoint {
                x: chart.low
                y: chart.low
            }
            XYPoint {
                x: chart.high
                y: chart.high
            }
        }
    }

    EaElements.Label {
        x: view.x + view.plotArea.x + (view.plotArea.width - width) / 2
        y: view.y + view.height + chart.em * 0.6
        color: chart.colors.chartLabels
        text: qsTr("F² calc")
    }
    EaElements.Label {
        x: chart.sideMargin - chart.em * 0.5
        y: view.y + view.plotArea.y + (view.plotArea.height + width) / 2
        rotation: -90
        transformOrigin: Item.TopLeft
        color: chart.colors.chartLabels
        text: qsTr("F² meas")
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
            markerSize: 6
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
        MouseArea {
            property real pressX: 0
            property real pressY: 0

            function valueAtX(px: real): real {
                return axisX.min + px / width * (axisX.max - axisX.min);
            }

            anchors.fill: parent
            acceptedButtons: Qt.LeftButton | Qt.RightButton
            onPressed: mouse => {
                pressX = mouse.x;
                pressY = mouse.y;
            }
            onReleased: mouse => {
                if (mouse.button === Qt.RightButton) {
                    chart.zoom = [];
                    return;
                }
                if (Math.abs(mouse.x - pressX) > chart.em * 0.3) {
                    const a = valueAtX(Math.min(pressX, mouse.x));
                    const b = valueAtX(Math.max(pressX, mouse.x));
                    if (b > a && isFinite(b - a))
                        chart.zoom = [a, b];
                }
            }
            onWheel: wheel => {
                if (wheel.angleDelta.y === 0)
                    return;
                const anchor = valueAtX(wheel.x);
                const factor = Math.pow(0.8, wheel.angleDelta.y / 120);
                const left = anchor - (anchor - axisX.min) * factor;
                const right = anchor + (axisX.max - anchor) * factor;
                if (isFinite(left) && isFinite(right) && right > left)
                    chart.zoom = [left, right];
            }
        }
    }
}
