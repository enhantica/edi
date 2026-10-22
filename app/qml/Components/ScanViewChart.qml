// SPDX-License-Identifier: BSD-3-Clause
pragma ComponentBehavior: Bound

import QtQuick
import QtQuick.Controls
import QtGraphs

import EasyApplication.Gui.Style as EaStyle
import EasyApplication.Gui.Elements as EaElements

import edi.app

// A scan's two pattern views (edi ADR-0041), each a tab of the Analysis page: "stacked" draws every dataset's measured
// pattern above its row, "map" colours the plot by intensity, smoothly from one dataset's row to the next, with a
// colour bar at the right. x is the pattern's axis across; up is the scan value (the first extract rule's) or, without
// one, the file index. A toolbar line above, as the Pattern tab's, chooses the y scale and the colours: the stacked
// patterns' palette or the map's colour map (the owner, 2026-10-22). The datasets are read in the background the first
// time either view shows; a dataset that cannot be read is named above the plot. A line marks the shown dataset at all
// times and follows it as a running scan moves on; a click on a row shows that dataset, here and on the Pattern tab.
Item {
    id: chart

    property ProjectViewModel project: null
    // "stacked" or "map".
    property string mode: "stacked"
    property bool shown: true
    readonly property ScanViewModel scan: project ? project.scanViews : null
    readonly property bool scanProject: project !== null && project.scan
    readonly property bool hasData: scan !== null && scan.loaded - scan.failed > 0
    property FigureColors colors: FigureColors {}
    readonly property real em: EaStyle.Sizes.fontPixelSize
    readonly property real sideMargin: AppSizes.mainAreaMargin
    readonly property real titleGutter: Math.round(em * 1.6)
    // The toolbar line at the top, as the pattern chart's, and the room under it: enough for the notes above the plot
    // and for the colour bar's top label, centred on the bar's end.
    readonly property real toolbarTop: em
    readonly property real plotTop: toolbarTop + AppSizes.toolbarControlSize + AppSizes.mainAreaMargin
    // The colours, as the app settings hold them (the owner, 2026-10-22): for either view a colour scheme's token (the
    // stacked view only), one of the four colour maps, or a ramp from the pattern chart's plot background to a scheme's
    // first measured colour (`ramp:<scheme>`).
    readonly property var stackedChoices: Array.from(ApplicationInfo.colourSchemes).concat(Array.from(ApplicationInfo.scanColourMaps), Array.from(ApplicationInfo.scanColourRamps))
    readonly property var mapChoices: Array.from(ApplicationInfo.scanColourMaps).concat(Array.from(ApplicationInfo.scanColourRamps))
    readonly property string stackedPalette: {
        const stored = Preferences.scanStackedPalette !== "" ? Preferences.scanStackedPalette : Preferences.colourScheme;
        return stackedChoices.indexOf(stored) >= 0 ? stored : ApplicationInfo.colourSchemeOrDefault(stored);
    }
    readonly property string mapColours: mapChoices.indexOf(Preferences.scanMapColours) >= 0 ? Preferences.scanMapColours : "viridis"
    // The view's zoom, always on in these views (the owner, 2026-10-22): [min, max] on x and on y, or empty for the
    // whole range. A drag on the plot sets it; the reset button, another scan, another x axis or another row placing
    // clears it.
    property var zoomX: []
    property var zoomY: []
    function resetZoom() {
        zoomX = [];
        zoomY = [];
    }
    readonly property real xTitleHeight: Math.round(em * 1.7)
    readonly property real barWidth: mode === "map" ? em * 6 : 0
    readonly property int xTicks: Math.max(2, Math.min(8, Math.round(width / (em * 6))))
    readonly property int yTicks: Math.max(2, Math.min(8, Math.floor((height - em * 6) / (em * 2.5))))
    readonly property real yMin: zoomY.length === 2 ? zoomY[0] : scan ? scan.rowMin : 0
    readonly property real yMax: zoomY.length === 2 ? zoomY[1] : scan ? scan.rowMax + (mode === "stacked" ? scan.stackHeight : 0) : 1

    objectName: "scanView." + mode

    // Shown once: the datasets are read from then on, for either view.
    onShownChanged: if (shown && scan !== null)
        scan.wanted = true
    Component.onCompleted: if (shown && scan !== null)
        scan.wanted = true
    onScanChanged: {
        resetZoom();
        if (shown && scan !== null)
            scan.wanted = true;
    }
    Connections {
        target: chart.scan
        function onXTitleChanged() {
            chart.resetZoom();
        }
        function onRowTitleChanged() {
            chart.resetZoom();
        }
        function onCountChanged() {
            chart.resetZoom();
        }
    }
    // Each axis type is one setting with every other selector for the same quantity (the owner, 2026-10-22): x is the
    // project's own, as the pattern chart's (edi ADR-0017 §15), its native quantity or d-spacing; the rows' places
    // follow the Evolution tab's x, the scan value or the file index.
    Binding {
        target: chart.scan
        property: "dSpacing"
        value: chart.project !== null && chart.project.patternDSpacing
        when: chart.scan !== null
    }
    Binding {
        target: chart.scan
        property: "rowsByIndex"
        value: chart.project !== null && chart.project.evolution !== null && chart.project.evolution.xMode === 1
        when: chart.scan !== null
    }

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
        y: chart.plotTop
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
            min: chart.zoomX.length === 2 ? chart.zoomX[0] : chart.scan ? chart.scan.xMin : 0
            max: chart.zoomX.length === 2 ? chart.zoomX[1] : chart.scan ? chart.scan.xMax : 1
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
            tickInterval: chart.niceStep(chart.zoomY.length === 2 ? max - min : chart.scan ? chart.scan.rowMax - chart.scan.rowMin : 1, chart.yTicks)
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
            colourScheme: chart.stackedPalette
            colourMap: chart.mapColours
            background: chart.colors.chartBackground
            smoothRows: Preferences.scanMapSmooth
            reversed: chart.mode === "map" && Preferences.scanMapReversed
            dark: chart.colors.isDarkPalette
            current: chart.project ? chart.project.currentExperimentIndex : -1
        }
        // The shown dataset's row, at all times: it moves with the shown dataset, so with a followed scan as it runs,
        // and with the rows when they are placed again (by scan value once every dataset is read). On the map a white
        // line edged in black, which shows on every colour of every map; on the stacked view the accent colour.
        Rectangle {
            // The revision is part of the expression, so the line moves when the rows are placed again.
            readonly property real at: chart.scan && chart.project && chart.scan.revision >= 0 ? chart.scan.rowOf(chart.project.currentExperimentIndex) : NaN

            objectName: "scanView." + chart.mode + ".current"
            visible: !isNaN(at)
            // Kept inside the plot, so the top and bottom rows' lines show too.
            y: Math.max(0, Math.min(plot.height - height, Math.round((axisY.max - at) / (axisY.max - axisY.min) * plot.height) - Math.floor(height / 2)))
            width: plot.width
            height: chart.mode === "map" ? 4 : 2
            color: chart.mode === "map" ? "black" : EaStyle.Colors.themeAccent

            Rectangle {
                visible: chart.mode === "map"
                y: 1
                width: parent.width
                height: 2
                color: "white"
            }
        }
        Rectangle {
            anchors.fill: parent
            color: "transparent"
            border.color: chart.colors.chartAxis
            border.width: 1
        }
        // The box a drag draws, which the view zooms to on release.
        Rectangle {
            id: zoomBox

            objectName: "scanView." + chart.mode + ".zoomBox"
            visible: false
            color: Qt.alpha(EaStyle.Colors.themeAccent, 0.15)
            border.color: EaStyle.Colors.themeAccent
            border.width: 1
        }
        // A drag zooms to the box it draws; a click shows the dataset whose row it falls in.
        MouseArea {
            property point start

            objectName: "scanView." + chart.mode + ".pointer"
            anchors.fill: parent
            cursorShape: Qt.CrossCursor
            onPressed: mouse => {
                start = Qt.point(mouse.x, mouse.y);
                zoomBox.width = 0;
                zoomBox.height = 0;
            }
            onPositionChanged: mouse => {
                const x = Math.max(0, Math.min(width, mouse.x)), y = Math.max(0, Math.min(height, mouse.y));
                zoomBox.x = Math.min(start.x, x);
                zoomBox.y = Math.min(start.y, y);
                zoomBox.width = Math.abs(x - start.x);
                zoomBox.height = Math.abs(y - start.y);
                zoomBox.visible = zoomBox.width > 4 || zoomBox.height > 4;
            }
            onReleased: mouse => {
                const atX = share => axisX.min + share * (axisX.max - axisX.min);
                const atY = share => axisY.max - share * (axisY.max - axisY.min);
                if (zoomBox.visible) {
                    zoomBox.visible = false;
                    if (zoomBox.width > 4 && zoomBox.height > 4) {
                        chart.zoomX = [atX(zoomBox.x / width), atX((zoomBox.x + zoomBox.width) / width)];
                        chart.zoomY = [atY((zoomBox.y + zoomBox.height) / height), atY(zoomBox.y / height)];
                    }
                    return;
                }
                if (chart.scan === null || chart.project === null)
                    return;
                // In the stacked view a pattern rises above its row: a click picks the row below it.
                const dataset = chart.scan.datasetAt(atY(mouse.y / height));
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

        // Drawn by the lookup the map's pixels take, so the key is the map's own.
        ScanColourBar {
            id: bar

            objectName: "scanView.map.colourBar.colours"
            x: chart.em
            width: chart.em
            height: parent.height
            colourMap: chart.mapColours
            background: chart.colors.chartBackground
            dark: chart.colors.isDarkPalette
            reversed: Preferences.scanMapReversed
        }
        Rectangle {
            anchors.fill: bar
            color: "transparent"
            border.color: chart.colors.chartAxis
            border.width: 1
        }
        // Each end's label centred on it, as a tick label is.
        EaElements.Label {
            objectName: "scanView.map.colourBar.max"
            x: bar.x + bar.width + chart.em * 0.3
            y: -height / 2
            color: chart.colors.chartLabels
            text: chart.intensityText(layer.displayMax)
        }
        EaElements.Label {
            objectName: "scanView.map.colourBar.min"
            x: bar.x + bar.width + chart.em * 0.3
            y: parent.height - height / 2
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
    // The toolbar line, centred above the plot as the pattern chart's (the owner, 2026-10-22): the axes' types, then the
    // colours, then the zoom, always on here, and the reset. x is the project's axis, shared with the pattern chart; y
    // places the rows by the extracted value or by file index, shared with the Evolution tab's x; z, the intensity
    // scale, is the pattern chart's y scale. The colours are each view's own app setting.
    Row {
        objectName: "scanView." + chart.mode + ".toolbar"
        // Centred over the plot, and kept inside the chart when the view is narrow.
        x: Math.round(Math.max(chart.sideMargin, Math.min(chart.width - width - chart.sideMargin, view.x + view.plotArea.x + (view.plotArea.width - width) / 2)))
        y: chart.toolbarTop
        spacing: EaStyle.Sizes.fontPixelSize * 0.5 + 2 * AppSizes.toolbarSpacing

        Row {
            spacing: AppSizes.toolbarSpacing

            ToolbarComboBox {
                objectName: "scanView." + chart.mode + ".toolbar.xaxis"
                readonly property string nativeName: chart.scan !== null && chart.scan.timeOfFlight ? qsTr("TOF") : qsTr("2θ")
                toolTip: qsTr("X axis")
                model: [chart.scan !== null && chart.scan.timeOfFlight ? qsTr("time-of-flight") : qsTr("2θ"), qsTr("d-spacing")]
                closedTexts: [qsTr("x: %1").arg(nativeName), qsTr("x: d")]
                currentIndex: chart.scan !== null && chart.scan.dShown ? 1 : 0
                onActivated: index => {
                    if (chart.project)
                        chart.project.patternDSpacing = index === 1;
                }
            }
            ToolbarComboBox {
                objectName: "scanView." + chart.mode + ".toolbar.rows"
                enabled: chart.scan !== null && chart.scan.valueTitle !== ""
                toolTip: qsTr("Y axis: the rows' places")
                readonly property var entries: [chart.scan !== null && chart.scan.valueTitle !== "" ? chart.scan.valueTitle : qsTr("scan value"), qsTr("file index")]
                model: entries
                closedTexts: entries.map(text => qsTr("y: %1").arg(text))
                currentIndex: chart.scan !== null && (chart.scan.rowsByIndex || chart.scan.valueTitle === "") ? 1 : 0
                onActivated: index => {
                    if (chart.project && chart.project.evolution)
                        chart.project.evolution.xMode = index;
                }
            }
            ToolbarComboBox {
                objectName: "scanView." + chart.mode + ".toolbar.yscale"
                readonly property var tokens: ["linear", "sqrt", "log"]
                readonly property string axis: "z"
                toolTip: qsTr("Z axis: the intensity scale, the pattern chart's y scale")
                readonly property var entries: [qsTr("linear"), qsTr("square root"), qsTr("log")]
                model: entries
                closedTexts: entries.map(text => qsTr("%1: %2").arg(axis).arg(text))
                currentIndex: Math.max(0, tokens.indexOf(Preferences.patternYScale))
                onActivated: index => Preferences.patternYScale = tokens[index]
            }
            ToolbarComboBox {
                objectName: "scanView.stacked.toolbar.palette"
                visible: chart.mode === "stacked"
                toolTip: qsTr("The patterns' colours")
                readonly property var entries: chart.stackedChoices.map(choice => ApplicationInfo.scanColourTitle(choice))
                model: entries
                closedTexts: entries
                currentIndex: Math.max(0, chart.stackedChoices.indexOf(chart.stackedPalette))
                onActivated: index => Preferences.scanStackedPalette = chart.stackedChoices[index]
            }
            ToolbarComboBox {
                objectName: "scanView.map.toolbar.colourMap"
                visible: chart.mode === "map"
                toolTip: qsTr("The map's colours")
                readonly property var entries: chart.mapChoices.map(choice => ApplicationInfo.scanColourTitle(choice))
                model: entries
                closedTexts: entries
                currentIndex: Math.max(0, chart.mapChoices.indexOf(chart.mapColours))
                onActivated: index => Preferences.scanMapColours = chart.mapChoices[index]
            }
        }
        Row {
            spacing: AppSizes.toolbarSpacing

            ChartToolButton {
                objectName: "scanView.map.toolbar.smooth"
                visible: chart.mode === "map"
                fontIcon: "water"
                toolTip: Preferences.scanMapSmooth ? qsTr("Colour changes smoothly between datasets: click for one band per dataset") : qsTr("One band of colour per dataset: click for a smooth change between datasets")
                checked: Preferences.scanMapSmooth
                onClicked: Preferences.scanMapSmooth = !Preferences.scanMapSmooth
            }
            ChartToolButton {
                objectName: "scanView.map.toolbar.reverse"
                visible: chart.mode === "map"
                fontIcon: "exchange-alt"
                toolTip: qsTr("Reverse the map's colours")
                checked: Preferences.scanMapReversed
                onClicked: Preferences.scanMapReversed = !Preferences.scanMapReversed
            }
            ChartToolButton {
                objectName: "scanView." + chart.mode + ".toolbar.zoom"
                fontIcon: "expand"
                toolTip: qsTr("Box zoom: drag over the plot (always on here)")
                checked: true
            }
            ChartToolButton {
                objectName: "scanView." + chart.mode + ".toolbar.reset"
                fontIcon: "home"
                toolTip: qsTr("Reset axes")
                onClicked: chart.resetZoom()
            }
        }
    }

    // Above the plot, under the toolbar: how far reading has come, then what could not be read, and why the rows are
    // placed by file index when the scan extracts a value.
    Column {
        anchors.right: parent.right
        anchors.rightMargin: chart.sideMargin
        y: chart.toolbarTop + AppSizes.toolbarControlSize + chart.em * 0.2
        width: Math.min(implicitWidth, parent.width - 2 * chart.sideMargin)

        EaElements.Label {
            objectName: "scanView." + chart.mode + ".progress"
            visible: chart.scan !== null && chart.scan.wanted && chart.scan.loaded < chart.scan.count
            anchors.right: parent.right
            color: chart.colors.chartLabels
            text: chart.scan ? qsTr("Reading patterns: %1 of %2").arg(chart.scan.loaded).arg(chart.scan.count) : ""
        }
        EaElements.Label {
            objectName: "scanView." + chart.mode + ".refused"
            visible: chart.scan !== null && chart.scan.failed > 0 && chart.hasData
            anchors.right: parent.right
            width: Math.min(implicitWidth, chart.width - 2 * chart.sideMargin)
            elide: Text.ElideMiddle
            color: EaStyle.Colors.red
            text: chart.scan ? qsTr("%1 of %2 patterns could not be read and are not shown. %3").arg(chart.scan.failed).arg(chart.scan.count).arg(chart.scan.error) : ""
            ToolTip.text: chart.scan ? chart.scan.error : ""
        }
        EaElements.Label {
            objectName: "scanView." + chart.mode + ".rowNote"
            visible: chart.scan !== null && chart.scan.rowNote !== "" && chart.hasData
            anchors.right: parent.right
            width: Math.min(implicitWidth, chart.width - 2 * chart.sideMargin)
            elide: Text.ElideMiddle
            color: chart.colors.chartLabels
            text: chart.scan ? chart.scan.rowNote : ""
        }
    }
    EmptyStateLabel {
        objectName: "scanView." + chart.mode + ".empty"
        anchors.centerIn: parent
        visible: !chart.hasData
        width: Math.min(implicitWidth, parent.width - 2 * chart.sideMargin)
        text: !chart.scanProject ? qsTr("A sequential fit's patterns show here") : chart.scan !== null && chart.scan.count > 0 && chart.scan.failed === chart.scan.count ? qsTr("None of the scan's patterns could be read. %1").arg(chart.scan.error) : qsTr("Reading the scan's patterns")
    }
}
