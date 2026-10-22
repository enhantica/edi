// SPDX-License-Identifier: BSD-3-Clause
pragma ComponentBehavior: Bound

import QtQuick
import QtQuick.Controls
import QtGraphs

import EasyApplication.Gui.Style as EaStyle
import EasyApplication.Gui.Elements as EaElements

import edi.app

// A scan's two pattern views (edi ADR-0041), each a tab of the Analysis page, and a joint fit's: "stacked" draws every
// dataset's measured pattern above its row, "map" colours the plot by intensity, smoothly from one dataset's row to the
// next, with a colour bar at the right. x is the pattern's axis across; up is the scan value (the first extract
// rule's) or, without one, the file index; a joint fit's experiments are rows in the project's order, each named. A toolbar line above, as the Pattern tab's, chooses the y scale and the colours: the stacked
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
    readonly property bool scanProject: project !== null && (project.scan || (scan !== null && scan.joint))
    readonly property bool joint: scan !== null && scan.joint
    // Rows labelled left of the plot instead of a numeric scale: always on the Stacked view, and on the Map when the
    // rows are in order by file or datablock, one band each; by scan value the Map keeps its scale, a position on it
    // being a real value its colour is interpolated at, with a tick at each dataset's row (the owner, 2026-10-22).
    readonly property bool rowLabels: mode === "stacked" || (scan !== null && !scan.rowsByValue)
    // Experiments on different native axes show on d only, so not before a calculation gives it.
    readonly property bool hasData: scan !== null && scan.loaded - scan.failed > 0 && (scan.nativeShared || scan.dAvailable)
    property FigureColors colors: FigureColors {}
    readonly property real em: EaStyle.Sizes.fontPixelSize
    readonly property real sideMargin: AppSizes.mainAreaMargin
    readonly property real titleGutter: Math.round(em * 1.6)
    // The toolbar line at the top, as the pattern chart's, and the room under it: enough for the notes above the plot
    // and for the colour bar's top label, centred on the bar's end.
    readonly property real toolbarTop: em
    readonly property real plotTop: toolbarTop + scanToolbar.height + AppSizes.mainAreaMargin
    // The colours, as the app settings hold them (the owner, 2026-10-22): for either view a colour scheme's token (the
    // stacked view only), one of the four colour maps, or a ramp from the pattern chart's plot background to a scheme's
    // first measured colour (`ramp:<scheme>`).
    // The Stacked view takes the schemes' own colours or a colour map, never a one-colour ramp, whose neighbouring lines
    // could not be told apart; the Map lists the Edi shades first (the owner, 2026-10-22).
    readonly property var stackedChoices: Array.from(ApplicationInfo.colourSchemes).concat(Array.from(ApplicationInfo.scanColourMaps))
    readonly property var mapChoices: Array.from(ApplicationInfo.scanColourRamps).concat(Array.from(ApplicationInfo.scanColourMaps))
    readonly property string stackedPalette: {
        const stored = Preferences.scanStackedPalette !== "" ? Preferences.scanStackedPalette : Preferences.patternColours;
        return stackedChoices.indexOf(stored) >= 0 ? stored : ApplicationInfo.colourSchemeOrDefault(stored);
    }
    readonly property string mapColours: mapChoices.indexOf(Preferences.scanMapColours) >= 0 ? Preferences.scanMapColours : "ramp:ediNatural"
    // The view's zoom, always on in these views (the owner, 2026-10-22): [min, max] on x and on y, or empty for the
    // whole range. A drag on the plot sets it; the reset button, another scan, another x axis or another row placing
    // clears it.
    property var zoomX: []
    property var zoomY: []
    // The x and y ranges change together and are published once, so another page never takes up a new x with the
    // old y.
    property bool settingZoom: false
    function setZoom(x, y) {
        settingZoom = true;
        zoomX = x;
        zoomY = y;
        settingZoom = false;
        publishZoom();
    }
    function resetZoom() {
        setZoom([], []);
    }
    // The zoom is one per view across the pages (the owner, 2026-10-22): the shown chart writes it, and a chart
    // takes it up when it is shown.
    readonly property var sharedZoom: AppState.scanZoom[mode] ?? ({
            "x": [],
            "y": []
        })
    function publishZoom() {
        if (!shown || settingZoom)
            return;
        const next = Object.assign({}, AppState.scanZoom);
        next[mode] = {
            "x": zoomX,
            "y": zoomY
        };
        AppState.scanZoom = next;
    }
    onZoomXChanged: publishZoom()
    onZoomYChanged: publishZoom()
    readonly property real xTitleHeight: Math.round(em * 1.7)
    // The bar, its gap and its wider end label, so a label never runs past the chart's right edge.
    readonly property real barWidth: mode === "map" ? Math.max(em * 6, em * 2.8 + Math.max(tickMetrics.advanceWidth(intensityText(layer.displayMax)), tickMetrics.advanceWidth(intensityText(layer.displayMin)))) : 0
    // As many x ticks as their labels leave room for, the widest label (the larger end, with room for a decimal or
    // two) and three em between labels, room for the round steps niceStep may take, so long TOF values never run into
    // each other (the owner, 2026-10-22).
    readonly property real xLabelWidth: tickMetrics.advanceWidth(Math.round(Math.max(Math.abs(scan ? scan.xMin : 0), Math.abs(scan ? scan.xMax : 1))).toString() + ".00")
    readonly property int xTicks: Math.max(2, Math.min(8, Math.floor(Math.max(1, view.plotArea.width) / (xLabelWidth + em * 3))))
    FontMetrics {
        id: tickMetrics

        font.family: EaStyle.Fonts.fontFamily
        font.pixelSize: EaStyle.Sizes.fontPixelSize
    }
    readonly property int yTicks: Math.max(2, Math.min(8, Math.floor((height - em * 6) / (em * 2.5))))
    readonly property real yMin: zoomY.length === 2 ? zoomY[0] : scan ? scan.rowMin : 0
    readonly property real yMax: zoomY.length === 2 ? zoomY[1] : scan ? scan.rowMax + (mode === "stacked" ? scan.stackHeight : 0) : 1

    objectName: "scanView." + mode

    // Shown once: the datasets are read from then on, for either view.
    onShownChanged: {
        if (shown) {
            const zoom = sharedZoom;
            setZoom(zoom.x, zoom.y);
        }
        if (shown && scan !== null)
            scan.wanted = true;
    }
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
        // The range changed to or from the included one: the view starts over on it.
        function onIncludedOnlyChanged() {
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
    // How high the stacked patterns rise, an app setting.
    Binding {
        target: chart.scan
        property: "stackScale"
        value: Preferences.scanStackedHeight
        when: chart.scan !== null
    }
    // Only the included range, the pattern charts' one setting.
    Binding {
        target: chart.scan
        property: "includedOnly"
        value: Preferences.chartIncludedOnly
        when: chart.scan !== null
    }
    Binding {
        target: chart.scan
        property: "rowsByIndex"
        value: chart.project !== null && chart.project.evolution !== null && chart.project.evolution.xMode === 1
        when: chart.scan !== null
    }

    // An x tick's label in the app's label font and size, as the pattern chart's axes (the owner, 2026-10-22).
    Component {
        id: xLabel

        Item {
            id: xTick

            property string text: ""

            implicitWidth: xTickText.implicitWidth
            implicitHeight: xTickText.implicitHeight

            EaElements.Label {
                id: xTickText

                anchors.fill: parent
                horizontalAlignment: Text.AlignHCenter
                verticalAlignment: Text.AlignVCenter
                color: chart.colors.chartLabels
                text: xTick.text
            }
        }
    }

    // A y tick's label. On the Stacked view only the scan values the rows cover are labelled (the owner, 2026-10-22):
    // above the top row the patterns rise into height that stands for no scan value.
    Component {
        id: yLabel

        Item {
            id: tick

            property string text: ""
            readonly property real value: parseFloat(text.replace(/[^0-9eE+\-.]/g, ""))
            readonly property real slack: chart.scan ? 1e-9 * Math.max(1, Math.abs(chart.scan.rowHighest - chart.scan.rowLowest)) : 0

            implicitWidth: tickText.implicitWidth
            implicitHeight: tickText.implicitHeight

            EaElements.Label {
                id: tickText

                anchors.fill: parent
                visible: chart.mode !== "stacked" || chart.scan === null || (tick.value >= chart.scan.rowLowest - tick.slack && tick.value <= chart.scan.rowHighest + tick.slack)
                horizontalAlignment: Text.AlignRight
                verticalAlignment: Text.AlignVCenter
                color: chart.colors.chartLabels
                text: tick.text
            }
        }
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
        // A joint fit's row labels stand left of the plot, where a scan's tick labels are.
        marginLeft: chart.sideMargin + chart.titleGutter + (chart.rowLabels ? chart.rowLabelsRoom + chart.rowLabelGap : 0)
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
            labelDelegate: xLabel
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
            // Rows labelled left of the plot have no scale: the axis itself is hidden, since a hidden axis keeps no
            // room, where one with hidden labels still keeps 60 px left of the plot (measured, Qt Graphs 6.11).
            visible: !chart.rowLabels
            labelDelegate: yLabel
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
            stackedReversed: Preferences.scanStackedReversed
            includedOnly: Preferences.chartIncludedOnly
            dark: chart.colors.isDarkPalette
            current: chart.project ? chart.project.currentExperimentIndex : -1
        }
        // The plot's border, under the shown dataset's rectangle, so that rectangle's outer line shows at the plot's
        // edges too.
        Rectangle {
            anchors.fill: parent
            color: "transparent"
            border.color: chart.colors.chartAxis
            border.width: 1
        }
        // The shown dataset, at all times, marked by an open rectangle (the owner, 2026-10-22): on the map round its
        // row's band, halfway to each neighbour; on the stacked view from its row up to its line's highest point in
        // the range shown. It moves with the shown dataset, so with a followed scan as it runs, and with the rows when
        // they are placed again (by scan value once every dataset is read), the range and the scale.
        SelectedPatternBox {
            readonly property int dataset: chart.project ? chart.project.currentExperimentIndex : -1
            // What the edges are read from, so the box follows each of them.
            readonly property var follows: [chart.scan ? chart.scan.revision : -1, layer.xMin, layer.xMax, layer.scale, layer.includedOnly, layer.displayMin, layer.displayMax]
            readonly property real low: chart.scan && follows.length > 0 ? (chart.mode === "map" ? chart.scan.rowLowEdge(dataset) : chart.scan.rowOf(dataset)) : NaN
            readonly property real high: chart.scan && follows.length > 0 ? (chart.mode === "map" ? chart.scan.rowHighEdge(dataset) : layer.peakOf(dataset)) : NaN
            readonly property real topPx: (axisY.max - high) / (axisY.max - axisY.min) * plot.height
            readonly property real bottomPx: (axisY.max - low) / (axisY.max - axisY.min) * plot.height
            // The stacked line sits inside its box: the border stands three pixels clear of its top and its row.
            readonly property real clear: chart.mode === "map" ? 0 : 3
            // Never thinner than its three lines either side and an empty inside (the owner, 2026-10-22): a thinner
            // band, in a dense part of a scan, takes this height centred on the dataset's row, and a band the zoom
            // leaves only a sliver of takes it centred on that sliver.
            readonly property real minimum: 8
            readonly property real rowPx: chart.scan ? (axisY.max - chart.scan.rowOf(dataset)) / (axisY.max - axisY.min) * plot.height : NaN
            readonly property real ownTop: Math.round(topPx) - clear
            readonly property real ownBottom: Math.round(bottomPx) + clear
            readonly property bool thin: ownBottom - ownTop < minimum
            // What is left of the band inside the plot: the minimum applies to it, so a tall band zoomed down to a
            // sliver at an edge keeps a readable box there too.
            readonly property real shownTop: Math.max(0, ownTop)
            readonly property real shownBottom: Math.min(plot.height, ownBottom)
            readonly property bool small: shownBottom - shownTop < minimum
            readonly property real centre: thin ? rowPx : (shownTop + shownBottom) / 2
            // Only a dataset whose band reaches into the range shown is marked: one outside it is never drawn at an
            // edge, where it would mark another row.
            readonly property bool inView: !isNaN(low) && !isNaN(high) && Math.max(low, high) >= axisY.min && Math.min(low, high) <= axisY.max

            objectName: "scanView." + chart.mode + ".current"
            dark: chart.colors.isDarkPalette
            visible: inView && height > 0
            x: 0
            y: small ? Math.max(0, Math.min(plot.height - minimum, Math.round(centre - minimum / 2))) : shownTop
            width: plot.width
            height: small ? Math.min(minimum, plot.height) : shownBottom - shownTop
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
        // A drag zooms to the box it draws; a click shows the dataset whose row it falls in; a secondary click (a
        // touchpad's two-finger click) resets the axes, as on the pattern chart.
        MouseArea {
            property point start

            objectName: "scanView." + chart.mode + ".pointer"
            anchors.fill: parent
            acceptedButtons: Qt.LeftButton | Qt.RightButton
            cursorShape: Qt.CrossCursor
            onPressed: mouse => {
                if (mouse.button === Qt.RightButton)
                    return;
                start = Qt.point(mouse.x, mouse.y);
                zoomBox.width = 0;
                zoomBox.height = 0;
            }
            onPositionChanged: mouse => {
                if (!(mouse.buttons & Qt.LeftButton))
                    return;
                const x = Math.max(0, Math.min(width, mouse.x)), y = Math.max(0, Math.min(height, mouse.y));
                zoomBox.x = Math.min(start.x, x);
                zoomBox.y = Math.min(start.y, y);
                zoomBox.width = Math.abs(x - start.x);
                zoomBox.height = Math.abs(y - start.y);
                zoomBox.visible = zoomBox.width > 4 || zoomBox.height > 4;
            }
            onReleased: mouse => {
                if (mouse.button === Qt.RightButton) {
                    chart.resetZoom();
                    return;
                }
                const atX = share => axisX.min + share * (axisX.max - axisX.min);
                const atY = share => axisY.max - share * (axisY.max - axisY.min);
                if (zoomBox.visible) {
                    zoomBox.visible = false;
                    if (zoomBox.width > 4 && zoomBox.height > 4) {
                        chart.setZoom([atX(zoomBox.x / width), atX((zoomBox.x + zoomBox.width) / width)], [atY((zoomBox.y + zoomBox.height) / height), atY(zoomBox.y / height)]);
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

    // The rows labelled left of the plot as the pattern chart labels a Bragg row (the owner, 2026-10-22): the
    // experiment's icon and the row's text (its scan value with unit, its file's name or its datablock's), in the
    // dataset's colour, at its row's height. The widest label sets the room left for them.
    readonly property real rowLabelGap: Math.round(em * 0.4)
    readonly property real rowLabelsRoom: {
        let widest = 0;
        for (let i = 0; i < rowLabelRepeater.count; ++i) {
            const label = rowLabelRepeater.itemAt(i);
            if (label)
                widest = Math.max(widest, label.width);
        }
        return Math.ceil(widest);
    }
    // Which labels show: all while they fit; when they would come too close to read, an evenly spread share of them,
    // the shown dataset's always among them. Zooming in spreads the rows, and the rest come back as they fit.
    readonly property var shownRowLabels: {
        const shown = [];
        const texts = rowLabels && scan !== null ? scan.rowTexts : [];
        if (texts.length === 0 || scan.revision < 0 || !(axisY.max > axisY.min) || plot.height <= 0)
            return shown;
        const gap = AppSizes.legendRowHeight;
        const placed = [];
        for (let i = 0; i < texts.length; ++i) {
            const at = scan.rowOf(i);
            shown.push(false);
            if (!isNaN(at) && at >= axisY.min && at <= axisY.max)
                placed.push({
                    "index": i,
                    "px": (axisY.max - at) / (axisY.max - axisY.min) * plot.height
                });
        }
        placed.sort((a, b) => a.px - b.px);
        // The smallest stride through the rows, in order, that keeps neighbouring labels a label's height apart.
        let stride = 1;
        const apart = k => {
            for (let n = k; n < placed.length; n += k)
                if (placed[n].px - placed[n - k].px < gap)
                    return false;
            return true;
        };
        while (stride < placed.length && !apart(stride))
            ++stride;
        const current = project ? project.currentExperimentIndex : -1;
        const currentPlace = placed.find(row => row.index === current);
        for (let n = 0; n < placed.length; n += stride) {
            if (!currentPlace || Math.abs(placed[n].px - currentPlace.px) >= gap || placed[n].index === current)
                shown[placed[n].index] = true;
        }
        if (currentPlace)
            shown[current] = true;
        return shown;
    }
    Repeater {
        id: rowLabelRepeater

        model: chart.rowLabels && chart.scan !== null ? chart.scan.rowTexts : []
        delegate: IconLine {
            required property string modelData
            required property int index
            readonly property real at: chart.scan.revision >= 0 ? chart.scan.rowOf(index) : NaN
            // The line's colour on the Stacked view; on the Map, a joint fit's experiment's own.
            // The colour choice and the theme are read here, so the label follows them.
            readonly property color colour: chart.mode === "stacked" && [layer.colourScheme, layer.dark, layer.stackedReversed].length > 0 ? layer.colourOf(index) : AppColors.experiment(index, chart.colors.isDarkPalette)

            objectName: "scanView." + chart.mode + ".rowLabel." + index
            visible: chart.hasData && chart.shownRowLabels[index] === true
            height: AppSizes.legendRowHeight
            textColor: colour
            segments: [
                {
                    "icon": "microscope",
                    "color": colour
                },
                {
                    "text": modelData
                }
            ]
            x: Math.max(0, plot.x - width - chart.rowLabelGap)
            // On Stacked a label stands on its curve's baseline, its bottom at the row (the owner, 2026-10-22); on the
            // Map it is centred on its band.
            y: plot.y + (axisY.max - at) / (axisY.max - axisY.min) * plot.height - (chart.mode === "stacked" ? height : height / 2)
        }
    }

    // One short tick per dataset at its row, in every y mode, on both views (the owner, 2026-10-22): just right of the
    // plot's right edge, a pixel clear of it, in the dataset's Stacked colour. Kept between the plot's top and bottom
    // border rows, so a row a fraction of a pixel above the axis's end is not drawn below the x axis line.
    Repeater {
        model: chart.scan !== null && chart.hasData ? chart.scan.count : 0
        delegate: Rectangle {
            required property int index
            readonly property real at: chart.scan.revision >= 0 ? chart.scan.rowOf(index) : NaN

            objectName: "scanView." + chart.mode + ".rowTick." + index
            visible: !isNaN(at) && at >= axisY.min && at <= axisY.max
            x: plot.x + plot.width + 1
            y: plot.y + Math.max(0, Math.min(plot.height - 1, Math.floor((axisY.max - at) / (axisY.max - axisY.min) * plot.height)))
            width: Math.round(chart.em * 0.4)
            height: 1
            // The colour choice and the theme are read here, so the tick follows them.
            color: [layer.colourScheme, layer.dark, layer.stackedReversed].length > 0 ? layer.colourOf(index) : "transparent"
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

    // An end of the colour bar as an intensity: the y scale's value taken back to counts, to four significant digits
    // as a key needs no more.
    function intensityCounts(value: real): real {
        const scale = Preferences.patternYScale;
        const counts = scale === "log" ? Math.pow(10, value) : scale === "sqrt" ? Math.sign(value) * value * value : value;
        return isFinite(counts) ? Number(counts.toPrecision(4)) : counts;
    }
    // The ends are written as the pattern chart writes its intensity ticks, so large ones take the same short
    // exponent form (the owner, 2026-10-22).
    readonly property var colourBarFormat: NumberText.axisFormat([intensityCounts(layer.displayMin), intensityCounts(layer.displayMax)], Preferences.patternYScale !== "log")
    function intensityText(value: real): string {
        return NumberText.axisTick(intensityCounts(value), colourBarFormat);
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
    Item {
        id: scanToolbar

        readonly property real spacing: EaStyle.Sizes.fontPixelSize * 0.5 + 2 * AppSizes.toolbarSpacing
        readonly property real available: chart.width - 2 * chart.sideMargin
        // The boxes that show, then the colours and the buttons, each a group: what is laid out, and every width it
        // depends on.
        readonly property var units: Array.from(selectors.children).filter(unit => unit.visible).concat([colours, buttons])
        readonly property string measure: available + ":" + units.map(unit => unit.width).join(",")

        // As many as fit on a line, each group a group's spacing after the one before, each line centred as the pattern
        // chart's are (the owner, 2026-10-22); the toolbar is as wide as its widest line.
        function layout() {
            const lines = [];
            let line = null;
            for (const unit of units) {
                const gap = line === null ? 0 : unit === colours || unit === buttons ? spacing : AppSizes.toolbarSpacing;
                if (line === null || line.width + gap + unit.width > available) {
                    line = {
                        "units": [unit],
                        "width": unit.width,
                        "gaps": [0]
                    };
                    lines.push(line);
                } else {
                    line.units.push(unit);
                    line.gaps.push(gap);
                    line.width += gap + unit.width;
                }
            }
            const widest = Math.max(0, ...lines.map(each => each.width));
            let top = 0;
            for (const each of lines) {
                let left = Math.round((widest - each.width) / 2);
                for (let i = 0; i < each.units.length; ++i) {
                    left += each.gaps[i];
                    each.units[i].x = left;
                    each.units[i].y = top;
                    left += each.units[i].width;
                }
                top += AppSizes.toolbarControlSize + AppSizes.toolbarSpacing;
            }
            width = widest;
            height = Math.max(0, top - AppSizes.toolbarSpacing);
        }

        objectName: "scanView." + chart.mode + ".toolbar"
        // Centred over the plot, and kept inside the chart when the view is narrow.
        x: Math.round(Math.max(chart.sideMargin, Math.min(chart.width - width - chart.sideMargin, view.x + view.plotArea.x + (view.plotArea.width - width) / 2)))
        y: chart.toolbarTop
        height: AppSizes.toolbarControlSize
        onMeasureChanged: Qt.callLater(layout)
        Component.onCompleted: layout()

        Item {
            id: selectors

            ToolbarComboBox {
                objectName: "scanView." + chart.mode + ".toolbar.xaxis"
                // As the pattern chart's: d once a calculation has given it, and the closed box names the list's entry.
                enabled: chart.scan !== null && chart.scan.dAvailable
                toolTip: chart.scan !== null && chart.scan.dAvailable ? qsTr("X axis") : qsTr("X axis: d-spacing can be chosen after a calculation")
                // A joint fit whose experiments share no native axis has d only.
                readonly property bool nativeOffered: chart.scan === null || chart.scan.nativeShared
                readonly property var entries: nativeOffered ? [chart.scan !== null && chart.scan.timeOfFlight ? qsTr("TOF") : qsTr("2θ"), qsTr("x: d-spacing")] : [qsTr("x: d-spacing")]
                model: entries
                closedTexts: entries.map(text => text.startsWith("x: ") ? text : qsTr("x: %1").arg(text))
                currentIndex: nativeOffered && chart.scan !== null && chart.scan.dShown ? 1 : 0
                onActivated: index => {
                    if (chart.project && nativeOffered)
                        chart.project.patternDSpacing = index === 1;
                }
            }
            ToolbarComboBox {
                objectName: "scanView." + chart.mode + ".toolbar.rows"
                // The rows by the scan value, where the scan extracts one, or in order by file (a scan's datasets share a
                // datablock) or by datablock (a joint fit's experiments), the owner, 2026-10-22.
                readonly property bool hasValue: chart.scan !== null && chart.scan.valueTitle !== ""
                readonly property string order: chart.scan !== null ? chart.scan.orderName : qsTr("file")
                enabled: hasValue
                toolTip: qsTr("Y axis: the rows' places")
                readonly property var entries: hasValue ? [chart.scan.valueTitle, order] : [order]
                model: entries
                closedTexts: entries.map(text => qsTr("y: %1").arg(text))
                currentIndex: hasValue && !chart.scan.rowsByIndex ? 0 : entries.length - 1
                onActivated: index => {
                    if (chart.project && chart.project.evolution)
                        chart.project.evolution.xMode = hasValue ? index : 1;
                }
            }
            // How high each stacked pattern rises: one to five times four rows, two by default (the owner, 2026-10-22).
            ToolbarComboBox {
                readonly property var entries: ["1×", "2×", "3×", "4×", "5×"]

                objectName: "scanView.stacked.toolbar.height"
                visible: chart.mode === "stacked"
                toolTip: qsTr("How high each pattern rises")
                model: entries
                closedTexts: entries.map(text => qsTr("height: %1").arg(text))
                currentIndex: Math.max(0, Math.min(4, Preferences.scanStackedHeight - 1))
                onActivated: index => Preferences.scanStackedHeight = index + 1
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
        }
        // The colours, a group of their own (the owner, 2026-10-22): on the Map its colour map and the reverse button;
        // on Stacked, whose colours are chosen in Preferences, the reverse button alone. Each view's reversal is kept
        // with its colour setting.
        Row {
            id: colours

            spacing: AppSizes.toolbarSpacing

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
            ChartToolButton {
                readonly property bool reversed: chart.mode === "map" ? Preferences.scanMapReversed : Preferences.scanStackedReversed

                objectName: "scanView." + chart.mode + ".toolbar.reverse"
                fontIcon: "exchange-alt"
                toolTip: chart.mode === "map" ? qsTr("Reverse the map's colours") : qsTr("Reverse the patterns' colours")
                checked: reversed
                onClicked: {
                    if (chart.mode === "map")
                        Preferences.scanMapReversed = !Preferences.scanMapReversed;
                    else
                        Preferences.scanStackedReversed = !Preferences.scanStackedReversed;
                }
            }
        }
        Row {
            id: buttons

            spacing: AppSizes.toolbarSpacing

            ChartToolButton {
                objectName: "scanView.map.toolbar.smooth"
                visible: chart.mode === "map"
                fontIcon: "water"
                toolTip: Preferences.scanMapSmooth ? qsTr("Bands blend into each other at their edges: click for hard edges") : qsTr("Hard edges between the bands: click to blend them at their edges")
                checked: Preferences.scanMapSmooth
                onClicked: Preferences.scanMapSmooth = !Preferences.scanMapSmooth
            }
            // Only the included range: the pattern chart's eraser button and its one app setting, so the three charts
            // switch together (the owner, 2026-10-22).
            ChartToolButton {
                objectName: "scanView." + chart.mode + ".toolbar.includedRange"
                fontIcon: "eraser"
                toolTip: qsTr("Show only the included range")
                checked: Preferences.chartIncludedOnly
                onClicked: Preferences.chartIncludedOnly = !Preferences.chartIncludedOnly
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
        text: !chart.scanProject ? qsTr("A sequential or joint fit's patterns show here") : chart.scan !== null && !chart.scan.nativeShared && !chart.scan.dAvailable ? qsTr("These experiments have different x axes: they show on d-spacing after a calculation") : chart.scan !== null && chart.scan.count > 0 && chart.scan.failed === chart.scan.count ? qsTr("None of the scan's patterns could be read. %1").arg(chart.scan.error) : qsTr("Reading the scan's patterns")
    }
}
