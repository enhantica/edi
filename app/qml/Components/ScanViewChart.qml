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
// time either view shows; a dataset that cannot be read is named above the plot. The shown dataset is highlighted (on
// top, the others faded) or, with highlighting off, marked by its bold label, and follows a running scan as it moves
// on; the pointer names the dataset it is over, and a click shows that dataset, here and on the Pattern tab.
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
    // Where the toolbar and the block selector row above it end, from the chart's right edge.
    readonly property real toolbarRightInset: sideMargin
    readonly property real titleGutter: Math.round(em * 1.6)
    // The toolbar line at the top, as the pattern chart's, and the room under it: enough for the notes above the plot
    // and for the colour bar's top label, centred on the bar's end.
    readonly property real toolbarTop: em
    readonly property real plotTop: toolbarTop + scanToolbar.height + AppSizes.mainAreaMargin
    // The colours (the owner, 2026-10-26): the Stacked lines take a palette's colours (by default the app's) or a
    // colour map's, and the Map a colour map, Blue-Red by default, both app settings. The Map's direction is the
    // project's (Auto by default), resolved in the theme the view is drawn in.
    readonly property var stackedChoices: Array.from(ApplicationInfo.colourSchemes).concat(Array.from(ApplicationInfo.scanColourMaps))
    readonly property var mapChoices: ApplicationInfo.scanColourMaps
    readonly property string stackedPalette: {
        const stored = Preferences.scanStackedPalette !== "" ? Preferences.scanStackedPalette : Preferences.colourScheme;
        return stackedChoices.indexOf(stored) >= 0 ? stored : ApplicationInfo.colourSchemeOrDefault(stored);
    }
    readonly property string mapColours: mapChoices.indexOf(Preferences.scanMapColours) >= 0 ? Preferences.scanMapColours : "blue-red"
    readonly property string mapDirection: chart.project ? chart.project.mapDirection : "auto"
    readonly property bool mapInverted: ApplicationInfo.scanMapInverted(mapColours, mapDirection, chart.colors.chartBackground, chart.colors.isDarkPalette)
    // The Stacked legend shown: its toolbar button, an app setting, off by default as the pattern chart's.
    readonly property bool stackedLegend: mode === "stacked" && Preferences.scanStackedLegendShown
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
    // The stacked view's vertical axis is the plot's height, 0 to 1, which the patterns are placed on (edi ADR-0041 §4);
    // the map's is the rows'.
    readonly property real yMin: zoomY.length === 2 ? zoomY[0] : mode === "stacked" ? 0 : scan ? scan.rowMin : 0
    readonly property real yMax: zoomY.length === 2 ? zoomY[1] : mode === "stacked" ? 1 : scan ? scan.rowMax : 1

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
    Component.onCompleted: {
        if (shown && scan !== null)
            scan.wanted = true;
        reportShown();
    }
    Component.onDestruction: {
        presentedTo?.setScanViewShown(chart, false);
        presentedTo = null;
    }
    // On screen, the view is where a scan whose every pattern is waited for shows each file, as the current dataset
    // (edi ADR-0029, 8): the project it told so.
    property ProjectViewModel presentedTo: null
    readonly property bool presenting: shown && project !== null
    function reportShown() {
        if (presentedTo !== null && (!presenting || presentedTo !== project)) {
            presentedTo.setScanViewShown(chart, false);
            presentedTo = null;
        }
        if (presenting && presentedTo === null) {
            project.setScanViewShown(chart, true);
            presentedTo = project;
        }
    }
    onPresentingChanged: reportShown()
    onProjectChanged: reportShown()
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
        theme: ChartTheme {
            labelTextColor: chart.colors.chartLabels
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
            // A joint fit's experiments at their positions; a scan's datasets at those the structures leave free.
            positions: chart.scan !== null && chart.scan.joint && chart.project ? chart.project.experimentColourPositions : []
            takenPositions: chart.project ? chart.project.structureColourPositions : []
            colourMap: chart.mapColours
            background: chart.colors.chartBackground
            smoothRows: Preferences.scanMapSmooth
            reversed: chart.mode === "map" && chart.mapInverted
            stackedReversed: Preferences.scanStackedReversed
            includedOnly: Preferences.chartIncludedOnly
            subtractBackground: Preferences.chartSubtractBackground
            dark: chart.colors.isDarkPalette
            current: chart.project ? chart.project.currentExperimentIndex : -1
            // A view on a page or tab not shown draws again only once it is shown.
            active: chart.shown && chart.visible
            // The row labels' choice (shownLabels): only while the view is shown and labels its rows; a label's text item is
            // its font's line tall, rounded up to a whole pixel, which can be more than the row height it is given.
            labelled: chart.shown && chart.rowLabels && chart.scan !== null && chart.scan.rowTextsRevision >= 0 && chart.scan.count > 0
            labelGap: Math.max(AppSizes.legendRowHeight, Math.ceil(tickMetrics.height))
            // Highlighting with the Stacked legend shown, the legend marks the shown dataset instead of its row's name
            // (the owner, 2026-10-26).
            nameCurrent: !(chart.stackedLegend && Preferences.chartHighlightSelected)
            // The shown dataset on top and the others faded, or all alike: one app setting for every chart of several
            // datasets (the owner, 2026-10-24).
            highlight: Preferences.chartHighlightSelected
            faded: Preferences.chartFadedOpacity
            busy: chart.project !== null && chart.project.fit !== null && chart.project.fit.running
            // The stacked patterns' spacing, the project's step (edi::stacked_spacing_share).
            spacing: ApplicationInfo.stackedSpacingShare(chart.project ? chart.project.stackedSpacing : "wide")
            // On the GPU as detected or chosen (edi ADR-0041); never on Qt Quick's software backend, which cannot draw
            // the lines' shader.
            gpu: RenderingInfo.api !== "Software" && (Preferences.scanRenderer === "gpu" || (Preferences.scanRenderer === "auto" && RenderingInfo.detected && !RenderingInfo.software))
            Component.onCompleted: RenderingInfo.observe(Window.window)
        }
        // The plot's border, under the shown dataset's rectangle, so that rectangle's outer line shows at the plot's
        // edges too.
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
        // A drag zooms to the box it draws; a click shows the dataset whose row it falls in; a secondary click (a
        // touchpad's two-finger click) resets the axes, as on the pattern chart.
        MouseArea {
            id: pointer

            property point start

            // The dataset under the pointer, named while it hovers (the owner, 2026-10-24); -1 for none.
            property int hovered: -1

            objectName: "scanView." + chart.mode + ".pointer"
            anchors.fill: parent
            acceptedButtons: Qt.LeftButton | Qt.RightButton
            // On Stacked the wheel scrolls through a stack taller than the plot (a fixed height), the shown range keeping
            // its height so each pattern keeps its own: up to the highest pattern's top, down to the lowest baseline.
            onWheel: wheel => {
                const top = Math.max(1, layer.stackTop);
                const span = chart.yMax - chart.yMin;
                if (chart.mode !== "stacked" || wheel.angleDelta.y === 0 || !(span > 0) || span >= top) {
                    wheel.accepted = false;
                    return;
                }
                const from = Math.max(0, Math.min(top - span, chart.yMin + wheel.angleDelta.y / 120 * span * 0.2));
                chart.setZoom(chart.zoomX, [from, from + span]);
            }
            hoverEnabled: true
            cursorShape: Qt.CrossCursor
            onExited: hovered = -1
            onPressed: mouse => {
                if (mouse.button === Qt.RightButton)
                    return;
                start = Qt.point(mouse.x, mouse.y);
                zoomBox.width = 0;
                zoomBox.height = 0;
            }
            onPositionChanged: mouse => {
                if (!(mouse.buttons & Qt.LeftButton)) {
                    hovered = chart.scan !== null ? layer.datasetNear(axisX.min + mouse.x / width * (axisX.max - axisX.min), axisY.max - mouse.y / height * (axisY.max - axisY.min)) : -1;
                    return;
                }
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
                // The stacked line nearest the click, or the map's band holding it (one placing: layer.rowOf).
                const dataset = layer.datasetNear(atX(mouse.x / width), atY(mouse.y / height));
                if (dataset >= 0)
                    chart.project.currentExperimentIndex = dataset;
            }

            // The hovered dataset's name next to the pointer (the owner, 2026-10-25): above it while that fits inside the
            // plot, else below it, and kept between the plot's sides, so it never covers the toolbar. Its arrow points
            // at the pointer.
            Item {
                id: hoverPoint

                x: pointer.mouseX
                y: pointer.mouseY
                width: 0
                height: 0

                EaElements.ToolTip {
                    id: hoverTip

                    readonly property real plotWidth: pointer.width

                    objectName: "scanView." + chart.mode + ".hover"
                    visible: pointer.hovered >= 0 && pointer.containsMouse
                    text: pointer.hovered >= 0 && chart.scan !== null && chart.scan.rowTextsRevision >= 0 ? chart.scan.rowText(pointer.hovered) : ""
                    x: Math.max(-hoverPoint.x, Math.min(plotWidth - hoverPoint.x - implicitWidth, -implicitWidth / 2))
                    // Below, clear of the cross cursor.
                    y: hoverPoint.y >= implicitHeight + gap ? -implicitHeight - gap : 3 * gap
                }
            }
        }
    }

    // The rows labelled left of the plot as the pattern chart labels a Bragg row (the owner, 2026-10-22): the
    // experiment's icon and the row's text (its scan value with unit, its file's name or its datablock's), in the
    // dataset's colour, at its row's height. The widest label sets the room left for them, worked out from the font
    // with the texts (an IconLine: the icon, its spacing, the text), so the plot takes its room in the frame that changed
    // the labels, never a frame later. Each text is measured bold, as the shown dataset's may be, so choosing another
    // dataset or turning the highlight off never moves the plot. A view not shown keeps the room it had: its labels are
    // blank until it shows.
    readonly property real rowLabelGap: Math.round(em * 0.4)
    property real rowLabelsRoom: 0
    Binding {
        target: chart
        property: "rowLabelsRoom"
        when: chart.shown
        restoreMode: Binding.RestoreNone
        value: chart.scan !== null && chart.scan.rowTextsRevision >= 0 ? Math.ceil(labelIcon.implicitWidth + chart.em * 0.5 + chart.scan.widestRowText(chart.shownRowLabels, labelBold.font)) : 0
    }
    // The row label's pieces as IconLine draws them: the icon a label of the icon font, measured by the width it takes
    // (an icon is measured in the font of an item drawing it, never one built from the family alone).
    EaElements.Label {
        id: labelIcon
        visible: false
        font.family: EaStyle.Fonts.iconsFamily
        font.pixelSize: chart.em
        text: "microscope"
    }
    FontMetrics {
        id: labelBold
        font.family: EaStyle.Fonts.ptSansBold.name
        font.styleName: "Bold"
        font.pixelSize: chart.em
    }
    // Which labels show (ScanLayer.shownLabels): all while they fit, else an evenly spread share with the shown dataset
    // always among them. A view not shown chooses none: a followed scan moves the shown dataset with every file.
    readonly property var shownRowLabels: layer.shownLabels
    Repeater {
        id: rowLabelRepeater

        // One label per dataset, kept while the rows are placed again and while the view labels no row (the Map by scan
        // value; shownRowLabels hides them): only its text, place and colour follow, and only while the view is shown.
        model: chart.scan !== null ? chart.scan.count : 0
        delegate: IconLine {
            required property int index
            // Only a label shown has its text: the others, hidden while the rows are too close, lay out nothing.
            readonly property string rowText: chart.shown && chart.shownRowLabels[index] === true && chart.scan !== null && chart.scan.rowTextsRevision >= 0 ? chart.scan.rowText(index) : ""
            readonly property real at: chart.shown && chart.scan !== null && chart.scan.revision >= 0 && layer.patternHeight > 0 ? layer.rowOf(index) : NaN
            // The dataset's colour, its Stacked line's (a joint fit's experiment's own, a scan's dataset's position in the
            // palette). The colours' revision is read here, so the label follows the colour choice and the theme.
            readonly property color colour: layer.coloursRevision >= 0 ? layer.colourOf(index) : chart.colors.themeForegroundMinor

            objectName: "scanView." + chart.mode + ".rowLabel." + index
            visible: chart.hasData && chart.shownRowLabels[index] === true
            height: AppSizes.legendRowHeight
            // Not highlighting, the shown dataset's label is its mark: bold, in the accent colour.
            readonly property bool marked: !Preferences.chartHighlightSelected && chart.project !== null && chart.project.currentExperimentIndex === index
            // The icon takes the text's colour, so a new colour changes no piece of the line.
            textColor: marked ? EaStyle.Colors.themeAccent : colour
            segments: [
                {
                    "icon": "microscope"
                },
                {
                    "text": rowText,
                    "bold": marked
                }
            ]
            x: Math.max(0, plot.x - width - chart.rowLabelGap)
            // On Stacked a label stands on its curve's baseline, its bottom at the row (the owner, 2026-10-22); on the
            // Map it is centred on its band.
            y: plot.y + (axisY.max - at) / (axisY.max - axisY.min) * plot.height - (chart.mode === "stacked" ? height : height / 2)
        }
    }

    // The Stacked legend at the plot's top right: every dataset, or past fifteen the first, the shown and the last with how
    // many more, the shown one bold in the accent colour while highlighting (ScanLayer.legend).
    ChartLegend {
        objectName: "scanView.stacked.legend"
        z: 1
        colors: chart.colors
        x: plot.x + plot.width - width - chart.em
        y: plot.y + chart.em
        visible: chart.stackedLegend && chart.hasData
        entries: layer.legend
    }

    // A map whose rows stand at their scan values keeps its numeric scale and labels no row; highlighting off, the shown
    // dataset is still marked by its bold label (the owner, 2026-10-24), inside the plot's left edge at its row.
    IconLine {
        readonly property int dataset: chart.project !== null ? chart.project.currentExperimentIndex : -1
        readonly property real at: dataset >= 0 && chart.scan !== null && chart.scan.revision >= 0 ? layer.rowOf(dataset) : NaN

        objectName: "scanView." + chart.mode + ".rowLabel." + dataset
        visible: !chart.rowLabels && chart.hasData && !Preferences.chartHighlightSelected && !isNaN(at) && at >= axisY.min && at <= axisY.max
        height: AppSizes.legendRowHeight
        textColor: EaStyle.Colors.themeAccent
        segments: [
            {
                "icon": "microscope"
            },
            {
                "text": dataset >= 0 && chart.scan !== null && chart.scan.rowTextsRevision >= 0 ? chart.scan.rowText(dataset) : "",
                "bold": true
            }
        ]
        x: plot.x + chart.rowLabelGap
        y: plot.y + (axisY.max - at) / (axisY.max - axisY.min) * plot.height - height / 2
    }

    // One short tick per dataset at its row, in every y mode, on both views (the owner, 2026-10-22): just right of the
    // plot's right edge, a pixel clear of it, in the dataset's Stacked colour, all drawn by one item (ScanRowTicks).
    ScanRowTicks {
        objectName: "scanView." + chart.mode + ".rowTicks"
        visible: chart.hasData
        scanLayer: layer
        x: plot.x + plot.width + 1
        y: plot.y
        width: tickWidth
        height: plot.height
        plotHeight: plot.height
        tickWidth: Math.round(chart.em * 0.4)
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
            reversed: chart.mapInverted
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
    function intensityCounts(value: real): real {
        const scale = Preferences.patternYScale;
        return scale === "log" ? Math.pow(10, value) : scale === "sqrt" ? Math.sign(value) * value * value : value;
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
    // The toolbar, the one rule of every chart's (ToolbarLines; the owner, 2026-10-24): every control on one line,
    // centred under the block selector row, when they fit; else the comboboxes above and the buttons below. The
    // comboboxes: the axes' types (x is the project's axis, shared with the pattern chart; y places the rows by the
    // extracted value or by file index, shared with the Evolution tab's x; z, the intensity scale, is the pattern
    // chart's y scale), the Stacked offset and height, and the Map's colours. The buttons: the colours' reversal, the
    // Map's smooth edges, the included range, the highlight, the zoom, always on here, and the reset.
    ToolbarLines {
        id: scanToolbar

        objectName: "scanView." + chart.mode + ".toolbar"
        // Across the chart, each line centred between its side margins, where the block selector row is.
        x: 0
        width: chart.width
        y: chart.toolbarTop
        height: implicitHeight
        leftEdge: chart.sideMargin
        rightEdge: chart.width - chart.sideMargin

        ToolbarComboBox {
            objectName: "scanView." + chart.mode + ".toolbar.xaxis"
            toolbarGroup: "axes"
            // As the pattern chart's: d once a calculation has given it, and the closed box names the list's entry.
            enabled: chart.scan !== null && chart.scan.dAvailable
            toolTip: chart.scan !== null && chart.scan.dAvailable ? qsTr("X axis") : qsTr("X axis: d-spacing can be chosen after a calculation")
            // A joint fit whose experiments share no native axis has d only.
            readonly property bool nativeOffered: chart.scan === null || chart.scan.nativeShared
            readonly property string dEntry: qsTr("x: %1").arg(Session.optionLabel("pattern_chart.x_axis", "d_spacing"))
            readonly property var entries: nativeOffered ? [Session.label(chart.scan !== null && chart.scan.timeOfFlight ? "data.time_of_flight" : "data.two_theta"), dEntry] : [dEntry]
            model: entries
            closedTexts: entries.map(text => text.startsWith("x: ") ? text : qsTr("x: %1").arg(text))
            shownIndex: nativeOffered && chart.scan !== null && chart.scan.dShown ? 1 : 0
            onActivated: index => {
                if (chart.project && nativeOffered)
                    chart.project.patternDSpacing = index === 1;
            }
        }
        ToolbarComboBox {
            objectName: "scanView." + chart.mode + ".toolbar.rows"
            toolbarGroup: "axes"
            // The rows by the scan value, where the scan extracts one, or in order by file (a scan's datasets share a
            // datablock) or by datablock (a joint fit's experiments), the owner, 2026-10-22.
            readonly property bool hasValue: chart.scan !== null && chart.scan.valueTitle !== ""
            readonly property string order: chart.scan !== null ? chart.scan.orderName : qsTr("file")
            // Open with one entry too, so it shows how the rows are placed.
            toolTip: qsTr("Y axis: the rows' places")
            readonly property var entries: hasValue ? [chart.scan.valueTitle, order] : [order]
            model: entries
            closedTexts: entries.map(text => qsTr("y: %1").arg(text))
            shownIndex: hasValue && !chart.scan.rowsByIndex ? 0 : entries.length - 1
            onActivated: index => {
                if (chart.project && chart.project.evolution)
                    chart.project.evolution.xMode = hasValue ? index : 1;
            }
        }
        ToolbarComboBox {
            objectName: "scanView." + chart.mode + ".toolbar.yscale"
            toolbarGroup: "axes"
            readonly property var tokens: ["linear", "sqrt", "log"]
            readonly property string axis: "z"
            toolTip: qsTr("Z axis: the intensity scale, the pattern chart's y scale")
            readonly property var entries: [qsTr("linear"), qsTr("square root"), qsTr("log")]
            model: entries
            closedTexts: entries.map(text => qsTr("%1: %2").arg(axis).arg(text))
            shownIndex: Math.max(0, tokens.indexOf(Preferences.patternYScale))
            onActivated: index => Preferences.patternYScale = tokens[index]
        }
        // The Stacked patterns' spacing, from overlaid to fully separated, a group of its own after the axes; the
        // project keeps it (the owner, 2026-10-26).
        ToolbarComboBox {
            readonly property var steps: ApplicationInfo.stackedSpacings

            objectName: "scanView.stacked.toolbar.spacing"
            toolbarGroup: "spacing"
            visible: chart.mode === "stacked"
            toolTip: qsTr("Spacing: from every pattern on one baseline to each in its own band")
            model: ApplicationInfo.stackedSpacingTitles
            closedTexts: ApplicationInfo.stackedSpacingTitles.map(title => qsTr("spacing: %1").arg(title))
            shownIndex: Math.max(0, steps.indexOf(chart.project ? chart.project.stackedSpacing : "wide"))
            onActivated: index => {
                if (chart.project)
                    chart.project.stackedSpacing = steps[index];
            }
        }
        // The Map's colour map, each with its colour bar, and its direction, a group of their own after the axes (the
        // owner, 2026-10-26).
        ColourMapComboBox {
            objectName: "scanView.map.toolbar.colourMap"
            toolbarGroup: "colours"
            visible: chart.mode === "map"
            toolTip: qsTr("The map's colours")
            maps: chart.mapChoices
            direction: chart.mapDirection
            chartBackground: chart.colors.chartBackground
            dark: chart.colors.isDarkPalette
            shownIndex: Math.max(0, chart.mapChoices.indexOf(chart.mapColours))
            onActivated: index => Preferences.scanMapColours = chart.mapChoices[index]
        }
        ToolbarComboBox {
            readonly property var directions: ApplicationInfo.scanMapDirections

            objectName: "scanView.map.toolbar.direction"
            toolbarGroup: "colours"
            visible: chart.mode === "map"
            toolTip: qsTr("Direction: Auto starts the map at the chart's background in either theme")
            model: ApplicationInfo.scanMapDirectionTitles
            closedTexts: ApplicationInfo.scanMapDirectionTitles.map(title => qsTr("direction: %1").arg(title))
            shownIndex: Math.max(0, directions.indexOf(chart.mapDirection))
            onActivated: index => {
                if (chart.project)
                    chart.project.mapDirection = directions[index];
            }
        }
        Row {
            id: buttons

            spacing: AppSizes.toolbarSpacing

            // The Stacked legend, as the pattern chart's button.
            ChartToolButton {
                objectName: "scanView.stacked.toolbar.legend"
                visible: chart.mode === "stacked"
                fontIcon: "align-left"
                toolTip: Preferences.scanStackedLegendShown ? qsTr("Hide legend") : qsTr("Show legend")
                checked: Preferences.scanStackedLegendShown
                onClicked: Preferences.scanStackedLegendShown = !Preferences.scanStackedLegendShown
            }
            // The Stacked colours in reverse order; the Map's direction is its own selector.
            ChartToolButton {
                objectName: "scanView.stacked.toolbar.reverse"
                visible: chart.mode === "stacked"
                fontIcon: "exchange-alt"
                toolTip: qsTr("Reverse the patterns' colours")
                checked: Preferences.scanStackedReversed
                onClicked: Preferences.scanStackedReversed = !Preferences.scanStackedReversed
            }
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
            // Every pattern less its background, the pattern chart's button and app setting (the owner, 2026-10-26):
            // offered when some dataset has a background set, fitted or not.
            ChartToolButton {
                objectName: "scanView." + chart.mode + ".toolbar.subtractBackground"
                available: chart.scan !== null && chart.scan.backgroundAvailable
                fontIcon: "chart-area"
                toolTip: available ? qsTr("Subtract each pattern's background") : qsTr("Subtract the background: no shown pattern has a background set")
                checked: Preferences.chartSubtractBackground && available
                onClicked: Preferences.chartSubtractBackground = !Preferences.chartSubtractBackground
            }
            // The shown dataset on top and the others faded, or all alike with its row label in bold: the one app
            // setting single-crystal Stacked uses too.
            ChartToolButton {
                objectName: "scanView." + chart.mode + ".toolbar.highlight"
                fontIcon: "highlighter"
                toolTip: qsTr("Highlight the selected dataset")
                checked: Preferences.chartHighlightSelected
                onClicked: Preferences.chartHighlightSelected = !Preferences.chartHighlightSelected
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
        y: chart.toolbarTop + scanToolbar.height + chart.em * 0.2
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
