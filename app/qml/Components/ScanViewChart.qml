// SPDX-License-Identifier: BSD-3-Clause
pragma ComponentBehavior: Bound

import QtQuick
import QtGraphs

import EasyApplication.Gui.Style as EaStyle
import EasyApplication.Gui.Elements as EaElements

import edi.app

// A scan's two pattern views (edi ADR-0041), each a tab of the Analysis page: "stacked" draws every dataset's measured
// pattern above its row, "map" colours each dataset's row by intensity (viridis), with a colour bar at the right. x is
// the pattern's axis across; up is the scan value (the first extract rule's) or, without one, the file index. The
// datasets are read in the background the first time either view shows. A line marks the shown dataset and follows
// it as a running scan moves on; a click on a row shows that dataset, here and on the Pattern tab.
Item {
    id: chart

    property ProjectViewModel project: null
    // "stacked" or "map".
    property string mode: "stacked"
    property bool shown: true
    readonly property ScanViewModel scan: project ? project.scanViews : null
    readonly property bool scanProject: project !== null && project.scan
    readonly property bool hasData: scan !== null && scan.loaded > 0
    property FigureColors colors: FigureColors {}
    readonly property real em: EaStyle.Sizes.fontPixelSize
    readonly property real sideMargin: AppSizes.mainAreaMargin
    readonly property real titleGutter: Math.round(em * 1.6)
    readonly property real xTitleHeight: Math.round(em * 1.7)
    readonly property real barWidth: mode === "map" ? em * 6 : 0
    readonly property int xTicks: Math.max(2, Math.min(8, Math.round(width / (em * 6))))
    readonly property int yTicks: Math.max(2, Math.min(8, Math.floor((height - em * 6) / (em * 2.5))))
    readonly property real yMin: scan ? scan.rowMin : 0
    readonly property real yMax: scan ? scan.rowMax + (mode === "stacked" ? scan.stackHeight : 0) : 1

    objectName: "scanView." + mode

    // Shown once: the datasets are read from then on, for either view.
    onShownChanged: if (shown && scan !== null)
        scan.wanted = true
    Component.onCompleted: if (shown && scan !== null)
        scan.wanted = true
    onScanChanged: if (shown && scan !== null)
        scan.wanted = true

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
        color: chart.colors.chartBackground
    }

    GraphsView {
        id: view

        objectName: "scanView." + chart.mode + ".axes"
        visible: chart.hasData
        y: chart.em
        width: parent.width - chart.barWidth
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
            min: chart.scan ? chart.scan.xMin : 0
            max: chart.scan ? chart.scan.xMax : 1
            tickInterval: chart.niceStep(max - min, chart.xTicks)
            tickAnchor: 0
            lineVisible: false
            gridVisible: false
            subGridVisible: false
        }
        axisY: ValueAxis {
            id: axisY
            min: chart.yMin
            max: chart.yMax
            tickInterval: chart.niceStep(chart.scan ? chart.scan.rowMax - chart.scan.rowMin : 1, chart.yTicks)
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

    // The plot area: the grid at the ticks, the patterns or the map, the shown dataset's line, and the border.
    Item {
        id: plot

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

        visible: chart.hasData
        x: view.x + view.plotArea.x
        y: view.y + view.plotArea.y
        width: view.plotArea.width
        height: view.plotArea.height
        clip: true

        Repeater {
            model: chart.mode === "stacked" ? plot.ticks(axisX) : []
            delegate: Rectangle {
                required property real modelData
                x: Math.round(modelData * plot.width)
                width: 1
                height: plot.height
                color: chart.colors.chartGridLine
            }
        }
        ScanLayer {
            id: layer

            objectName: "scanView." + chart.mode + ".layer"
            anchors.fill: parent
            model: chart.scan
            mode: chart.mode
            xMin: axisX.min
            xMax: axisX.max
            yMin: axisY.min
            yMax: axisY.max
            scale: Preferences.patternYScale
            colourScheme: Preferences.colourScheme
            dark: chart.colors.isDarkPalette
            current: chart.project ? chart.project.currentExperimentIndex : -1
        }
        // The shown dataset's row: it moves with the shown dataset, so with a followed scan as it runs.
        Rectangle {
            readonly property real at: chart.scan && chart.project ? chart.scan.rowOf(chart.project.currentExperimentIndex) : NaN

            objectName: "scanView." + chart.mode + ".current"
            visible: !isNaN(at)
            y: Math.round((axisY.max - at) / (axisY.max - axisY.min) * plot.height)
            width: plot.width
            height: 1
            color: chart.mode === "map" ? "white" : EaStyle.Colors.themeForegroundMinor
        }
        Rectangle {
            anchors.fill: parent
            color: "transparent"
            border.color: chart.colors.chartAxis
            border.width: 1
        }
        // A click shows the dataset whose row it falls in.
        MouseArea {
            objectName: "scanView." + chart.mode + ".pointer"
            anchors.fill: parent
            cursorShape: Qt.PointingHandCursor
            onClicked: mouse => {
                if (chart.scan === null || chart.project === null)
                    return;
                const row = axisY.max - mouse.y / height * (axisY.max - axisY.min);
                // In the stacked view a pattern rises above its row: a click picks the row below it.
                const dataset = chart.scan.datasetAt(row);
                if (dataset >= 0)
                    chart.project.currentExperimentIndex = dataset;
            }
        }
    }

    // The map's colour bar: the colour map from bottom to top, labelled at its ends with the intensities they stand for.
    Item {
        objectName: "scanView.map.colourBar"
        visible: chart.mode === "map" && chart.hasData
        x: view.x + view.width
        y: plot.y
        width: chart.barWidth
        height: plot.height

        Rectangle {
            id: bar

            x: chart.em
            width: chart.em
            height: parent.height
            border.color: chart.colors.chartAxis
            border.width: 1
            gradient: Gradient {
                GradientStop {
                    position: 0.0
                    color: layer.mapColour(1.0)
                }
                GradientStop {
                    position: 0.25
                    color: layer.mapColour(0.75)
                }
                GradientStop {
                    position: 0.5
                    color: layer.mapColour(0.5)
                }
                GradientStop {
                    position: 0.75
                    color: layer.mapColour(0.25)
                }
                GradientStop {
                    position: 1.0
                    color: layer.mapColour(0.0)
                }
            }
        }
        EaElements.Label {
            x: bar.x + bar.width + chart.em * 0.3
            y: 0
            color: chart.colors.chartLabels
            text: chart.intensityText(layer.displayMax)
        }
        EaElements.Label {
            x: bar.x + bar.width + chart.em * 0.3
            y: parent.height - height
            color: chart.colors.chartLabels
            text: chart.intensityText(layer.displayMin)
        }
    }

    // An end of the colour bar as an intensity: the y scale's value taken back to counts.
    function intensityText(value: real): string {
        const scale = Preferences.patternYScale;
        const counts = scale === "log" ? Math.pow(10, value) : scale === "sqrt" ? Math.sign(value) * value * value : value;
        return Math.abs(counts) >= 1000 ? Math.round(counts).toString() : Number(Number(counts).toPrecision(3)).toString();
    }

    EaElements.Label {
        objectName: "scanView." + chart.mode + ".title.y"
        visible: chart.hasData
        rotation: -90
        color: chart.colors.chartLabels
        x: (chart.sideMargin - width) / 2
        y: plot.y + (plot.height - height) / 2
        text: chart.scan ? chart.scan.rowTitle : ""
    }
    EaElements.Label {
        objectName: "scanView." + chart.mode + ".title.x"
        visible: chart.hasData
        x: plot.x + (plot.width - width) / 2
        y: chart.height - chart.em - chart.xTitleHeight + (chart.xTitleHeight - height) / 2
        color: chart.colors.chartLabels
        text: chart.scan ? chart.scan.xTitle : ""
    }
    // Reading the datasets: how far it has come, at the top right.
    EaElements.Label {
        objectName: "scanView." + chart.mode + ".progress"
        visible: chart.scan !== null && chart.scan.wanted && chart.scan.loaded < chart.scan.count
        anchors.right: parent.right
        anchors.rightMargin: chart.sideMargin
        y: chart.em * 0.2
        color: chart.colors.chartLabels
        text: chart.scan ? qsTr("Reading patterns: %1 of %2").arg(chart.scan.loaded).arg(chart.scan.count) : ""
    }
    EmptyStateLabel {
        objectName: "scanView." + chart.mode + ".empty"
        anchors.centerIn: parent
        visible: !chart.hasData
        width: Math.min(implicitWidth, parent.width - 2 * chart.sideMargin)
        text: chart.scanProject ? qsTr("Reading the scan's patterns") : qsTr("A sequential fit's patterns show here")
    }
}
