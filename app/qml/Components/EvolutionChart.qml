// SPDX-License-Identifier: BSD-3-Clause
pragma ComponentBehavior: Bound

import QtQuick
import QtGraphs

import EasyApplication.Gui.Style as EaStyle
import EasyApplication.Gui.Elements as EaElements

import edi.app

// The Evolution tab's chart (edi ADR-0017 §19): one fitted parameter across a scan's datasets, each dataset a point
// with its uncertainty as an error bar, drawn as the pattern chart draws measured points (MeasuredLayer). x is the
// first extract rule's value or the file's place in the scan (the box at the top left); the parameter is chosen in
// the selector beside that box; the page's selector row above lists the datasets, as on the Pattern tab. A click on
// a point shows that dataset, here and on the Pattern tab; a line marks the shown one. The pointer zooms as on the
// pattern chart, without its toolbar: a drag zooms to the box, the wheel or touchpad about the pointer, a right click
// resets.
Item {
    id: chart

    objectName: "evolution"

    property ProjectViewModel project: null
    readonly property EvolutionViewModel evolution: project ? project.evolution : null
    // The tab is the one the window shows; the points are drawn once it is.
    property bool shown: true

    readonly property real em: EaStyle.Sizes.fontPixelSize
    // The main area's margin (AppSizes.mainAreaMargin), as the pattern chart's.
    readonly property real sideMargin: AppSizes.mainAreaMargin
    readonly property real toolbarRightInset: sideMargin
    readonly property real titleGutter: Math.round(em * 1.6)
    readonly property real xTitleHeight: Math.round(em * 1.7)
    // The zoomed ranges, [xMin, xMax, yMin, yMax]; empty: the whole data.
    property list<real> zoom: []

    // A round step giving about `count` ticks over a span: 1, 2 or 5 times a power of ten.
    function niceStep(span, count) {
        if (!(span > 0))
            return 1;
        const raw = span / count;
        const power = Math.pow(10, Math.floor(Math.log10(raw)));
        const scaled = raw / power;
        return (scaled < 1.5 ? 1 : scaled < 3.5 ? 2 : scaled < 7.5 ? 5 : 10) * power;
    }

    Rectangle {
        anchors.fill: parent
        color: EaStyle.Colors.chartBackground
    }

    // x: the extracted value or the file index; the closed box names its axis, as the pattern chart's do.
    ToolbarComboBox {
        id: xBox

        objectName: "evolution.toolbar.x"
        x: chart.sideMargin
        y: chart.em
        enabled: chart.evolution !== null && chart.evolution.xModes.length > 1 && chart.project.scanColumns.length > 0
        toolTip: qsTr("X axis")
        model: chart.evolution ? chart.evolution.xModes : []
        closedTexts: chart.evolution ? chart.evolution.xModes.map(mode => qsTr("x: %1").arg(mode)) : []
        currentIndex: chart.evolution ? chart.evolution.xMode : 0
        onActivated: index => chart.evolution.xMode = index
    }

    // The parameter drawn, one of those results.csv records, with the previous and next buttons.
    BlockSelector {
        objectName: "evolution.parameters"
        x: xBox.x + xBox.width + AppSizes.toolbarSpacing * 4
        y: xBox.y + (xBox.height - height) / 2
        width: Math.max(0, chart.width - x - chart.toolbarRightInset)
        backgroundColor: EaStyle.Colors.chartBackground
        blocks: chart.evolution ? chart.evolution.parameters : null
        blocksTextRole: "label"
        blockKind: "parameter"
        blockIndex: chart.evolution ? chart.evolution.currentParameter : -1
        onBlockActivated: index => chart.evolution.currentParameter = index
    }

    GraphsView {
        id: view

        objectName: "evolution.view"
        y: xBox.y + xBox.height + chart.sideMargin
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
            labelTextColor: EaStyle.Colors.chartLabels
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
            min: chart.evolution ? chart.evolution.xMin : 0
            max: chart.evolution ? chart.evolution.xMax : 1
            tickInterval: chart.niceStep(max - min, 8)
            tickAnchor: 0
            lineVisible: false
            gridVisible: false
            subGridVisible: false
        }
        axisY: ValueAxis {
            id: axisY
            min: chart.evolution ? chart.evolution.yMin : 0
            max: chart.evolution ? chart.evolution.yMax : 1
            tickInterval: chart.niceStep(max - min, 6)
            tickAnchor: 0
            lineVisible: false
            gridVisible: false
            subGridVisible: false
        }
        // Qt Graphs draws nothing without a series.
        LineSeries {
            visible: false
        }
    }

    // The plot area: the grid at the ticks, the shown dataset's line, the points, and the border over them.
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
                color: EaStyle.Colors.chartGridLine
            }
        }
        Repeater {
            model: plot.ticks(axisY)
            delegate: Rectangle {
                required property real modelData
                y: Math.round((1 - modelData) * plot.height)
                width: plot.width
                height: 1
                color: EaStyle.Colors.chartGridLine
            }
        }
        // The shown dataset, from its own x: it moves only when the shown dataset, the x mode or the axis does.
        Rectangle {
            readonly property real at: chart.evolution && chart.project && chart.evolution.xMode >= 0 ? chart.evolution.datasetX(chart.project.currentExperimentIndex) : NaN

            objectName: "evolution.current"
            visible: !isNaN(at)
            x: Math.round((at - axisX.min) / (axisX.max - axisX.min) * plot.width)
            width: 1
            height: plot.height
            color: EaStyle.Colors.themeForegroundMinor
        }
        MeasuredLayer {
            id: layer

            objectName: "evolution.points"
            anchors.fill: parent
            color: AppColors.experiment(0)
            markerSize: 6
            xMin: axisX.min
            xMax: axisX.max
            yMin: axisY.min
            yMax: axisY.max
        }
        Rectangle {
            anchors.fill: parent
            color: "transparent"
            border.color: EaStyle.Colors.chartAxis
            border.width: 1
        }
        // A left click shows the dataset of the nearest point within a few pixels. A drag zooms to its box (refused
        // when flat in either direction or not finite); the wheel zooms about the pointer (one notch away multiplies
        // the x span by 0.8, as on the pattern chart); a right click resets. Neither a drag nor a right click selects:
        // the press arms the point pick only for a left button, and a move past the threshold disarms it.
        MouseArea {
            id: pointer

            property real pressX: 0
            property real pressY: 0
            // Whether a click may pick a point: a press arms it only for the left button, and a move past the
            // threshold disarms it, so a drag or a right click selects nothing (the Binding below hands it to the model).
            property bool picking: true
            readonly property bool dragging: pressed && (pressedButtons & Qt.LeftButton) && (Math.abs(mouseX - pressX) > chart.em * 0.3 || Math.abs(mouseY - pressY) > chart.em * 0.3)

            function xAt(px: real): real {
                return axisX.min + px / width * (axisX.max - axisX.min);
            }
            function yAt(py: real): real {
                return axisY.max - py / height * (axisY.max - axisY.min);
            }
            function moved(mouse): bool {
                return Math.abs(mouse.x - pressX) > chart.em * 0.3 || Math.abs(mouse.y - pressY) > chart.em * 0.3;
            }

            objectName: "evolution.pointer"
            anchors.fill: parent
            acceptedButtons: Qt.LeftButton | Qt.RightButton
            cursorShape: Qt.PointingHandCursor
            onPressed: mouse => {
                pressX = mouse.x;
                pressY = mouse.y;
                picking = mouse.button === Qt.LeftButton;
            }
            onPositionChanged: mouse => {
                if (moved(mouse))
                    picking = false;
            }
            // A zoom is taken only with increasing ends and finite spans on both axes.
            onReleased: mouse => {
                if (mouse.button === Qt.RightButton) {
                    picking = false;
                    chart.zoom = [];
                } else if (moved(mouse)) {
                    picking = false;
                    const box = [Math.min(xAt(pressX), xAt(mouse.x)), Math.max(xAt(pressX), xAt(mouse.x)), Math.min(yAt(pressY), yAt(mouse.y)), Math.max(yAt(pressY), yAt(mouse.y))];
                    if (Math.abs(mouse.x - pressX) > chart.em * 0.3 && Math.abs(mouse.y - pressY) > chart.em * 0.3 && box[1] > box[0] && box[3] > box[2] && isFinite(box[1] - box[0]) && isFinite(box[3] - box[2]))
                        chart.zoom = box;
                }
            }
            onClicked: mouse => {
                const reach = chart.em * 0.6;
                const dataset = chart.evolution.datasetAt(axisX.min + mouse.x / width * (axisX.max - axisX.min), axisY.max - mouse.y / height * (axisY.max - axisY.min), reach / width * (axisX.max - axisX.min), reach / height * (axisY.max - axisY.min));
                if (dataset >= 0)
                    chart.project.currentExperimentIndex = dataset;
            }
            onWheel: wheel => {
                if (wheel.angleDelta.y === 0)
                    return;
                const anchor = xAt(wheel.x);
                const factor = Math.pow(0.8, wheel.angleDelta.y / 120);
                // Only a zoom with finite, non-empty spans on both axes.
                if (!(isFinite(anchor) && isFinite((axisX.max - axisX.min) * factor) && (axisX.max - axisX.min) * factor > 0 && isFinite(axisY.max - axisY.min) && axisY.max > axisY.min))
                    return;
                chart.zoom = [anchor - (anchor - axisX.min) * factor, anchor + (axisX.max - anchor) * factor, axisY.min, axisY.max];
            }

            Binding {
                target: chart.evolution
                property: "picking"
                value: pointer.picking
                when: chart.evolution !== null
            }

            // The box being dragged, as the pattern chart draws it.
            Rectangle {
                objectName: "evolution.zoom.box"
                visible: pointer.dragging
                x: Math.min(pointer.pressX, pointer.mouseX)
                y: Math.min(pointer.pressY, pointer.mouseY)
                width: Math.abs(pointer.mouseX - pointer.pressX)
                height: Math.abs(pointer.mouseY - pointer.pressY)
                color: "transparent"
                border.color: EaStyle.Colors.appBorder
                border.width: EaStyle.Sizes.borderThickness
                opacity: 0.9

                Rectangle {
                    anchors.fill: parent
                    opacity: 0.5
                    color: EaStyle.Colors.appBorder
                }
            }
        }
    }

    // A zoom holds the axes at its box until it is reset; the axes then follow the data's ranges again.
    Binding {
        target: axisX
        property: "min"
        value: chart.zoom.length === 4 ? chart.zoom[0] : 0
        when: chart.zoom.length === 4
    }
    Binding {
        target: axisX
        property: "max"
        value: chart.zoom.length === 4 ? chart.zoom[1] : 1
        when: chart.zoom.length === 4
    }
    Binding {
        target: axisY
        property: "min"
        value: chart.zoom.length === 4 ? chart.zoom[2] : 0
        when: chart.zoom.length === 4
    }
    Binding {
        target: axisY
        property: "max"
        value: chart.zoom.length === 4 ? chart.zoom[3] : 1
        when: chart.zoom.length === 4
    }

    // Another parameter or x axis is drawn at its whole range.
    Connections {
        target: chart.evolution
        function onCurrentParameterChanged() {
            chart.zoom = [];
        }
        function onXModeChanged() {
            chart.zoom = [];
        }
    }

    // The layer is the model's to fill while the tab is shown.
    Binding {
        target: chart.evolution
        property: "layer"
        value: chart.shown ? layer : null
        when: chart.evolution !== null
    }

    EaElements.Label {
        objectName: "evolution.title.y"
        rotation: -90
        color: EaStyle.Colors.chartLabels
        // Centred in the margin, clear of the tick labels, which Qt Graphs lets reach into the plot's left margin.
        x: (chart.sideMargin - width) / 2
        y: plot.y + (plot.height - height) / 2
        text: chart.evolution ? chart.evolution.yTitle : ""
    }
    EaElements.Label {
        objectName: "evolution.title.x"
        x: plot.x + (plot.width - width) / 2
        y: chart.height - chart.em - chart.xTitleHeight + (chart.xTitleHeight - height) / 2
        color: EaStyle.Colors.chartLabels
        text: chart.evolution ? chart.evolution.xTitle : ""
    }
    // Results the template has changed since stay drawn, marked out of date until the next run.
    EaElements.Label {
        objectName: "evolution.outOfDate"
        anchors.right: plot.right
        anchors.bottom: plot.top
        anchors.bottomMargin: chart.em * 0.5
        visible: chart.evolution !== null && chart.evolution.outOfDate
        color: EaStyle.Colors.orange
        text: qsTr("Out of date: the template changed after this run")
    }
    EaElements.Label {
        anchors.centerIn: plot
        visible: chart.evolution !== null && chart.evolution.count === 0
        color: EaStyle.Colors.themeForegroundMinor
        text: qsTr("No fitted values yet: the scan's results appear here as the datasets are fitted")
    }
}
