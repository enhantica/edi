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

    // One accessible part in the browser, where Qt reads a flat page again for each of its items.
    Accessible.role: Accessible.Grouping
    Accessible.ignored: Qt.platform.os !== "wasm"

    // What the main view's Save image takes when this is the shown tab: the item, its toolbar (hidden while the image
    // is taken), the file name, and whether the toolbar's band is cut off.
    readonly property Item imageItem: chart.onAxis ? axisChart : chart
    readonly property Item imageToolbar: chart.onAxis ? axisChart.imageToolbar : toolbar
    readonly property string imageName: chart.onAxis ? "pattern" : chart.stacked ? "stacked" : "single-crystal"
    readonly property bool imageCropsToolbar: true

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
    readonly property list<SingleCrystalReflectionModel> models: ApplicationInfo.singleModels()
    // The experiments hidden by a click on their legend row (the owner, 2026-10-25), by name: kept while the app runs,
    // cleared when another project opens. Their reflection models; and the models the range is fitted to, which
    // leave the hidden ones out only when Preferences says hiding fits the range to the visible curves.
    property list<string> hiddenRows: []
    readonly property var hiddenModels: ApplicationInfo.singleHiddenModels()
    readonly property list<SingleCrystalReflectionModel> rangeModels: ApplicationInfo.singleRangeModels()
    // Bumped when any shown model's points change, so the bindings below read them again.
    property int revision: 0
    property FigureColors colors: FigureColors {}
    property bool shown: true
    // The report's input (edi ADR-0036): an experiment's `single_crystal` from the report model's JSON.
    property var reportData: null
    readonly property bool reportMode: reportData !== null
    // Which of a report's reflections the fit uses, by their reasons (empty for a used one); null for a report
    // without them, whose reflections are all used.
    readonly property var reportUsed: reportMode && reportData.reason ? reportData.reason.map(reason => reason === "") : null
    // How faint the reflections the fit leaves out are drawn.
    readonly property real leftOutOpacity: 0.3
    readonly property bool calculated: ApplicationInfo.singleCalculated()
    // The report's range: every bar end and every F²calc, padded as the app pads its own.
    readonly property list<real> reportRange: ApplicationInfo.singleReportRange()

    readonly property real em: EaStyle.Sizes.fontPixelSize
    // The pattern chart's layout: the toolbar line a gap below the page's block selector row, centred over the plot,
    // and the plot the main area's margin below it.
    // A report figure has that margin on all four sides, to the letters of its titles, whose lines reach past them (the
    // owner, 2026-11-24).
    readonly property real sideMargin: AppSizes.mainAreaMargin
    readonly property real topMargin: reportMode ? AppSizes.mainAreaMargin - Math.round(em * 0.3) : em
    readonly property real bottomMargin: reportMode ? AppSizes.mainAreaMargin - Math.round(em * 0.3) : em
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
    // Reflections calculated without measured ones: the calculated value against sin(θ)/λ, without the y = x line.
    readonly property bool simulated: !stacked && !reportMode && reflections !== null && reflections.simulated
    // On the Pattern tab the reflections are a pattern on Q or sinθ/λ (the owner, 2026-11-16), drawn by the pattern
    // chart over this one; on the Meas vs calc tab (`comparison`) measured against calculated values, with the y = x line.
    property bool comparison: false
    readonly property bool onAxis: !stacked && !reportMode && experiment !== null && !comparison
    readonly property string xItem: simulated ? "refln.sin_theta_over_lambda" : calculatedItem
    readonly property string yItem: simulated ? calculatedItem : measuredItem
    // The shown ranges, [xMin, xMax, yMin, yMax]; empty: every reflection, on one range for both axes. Each view's
    // zoom is one across the pages that show it (AppState.singleCrystalZoom); a report figure keeps its own.
    property list<real> zoom: []
    readonly property string zoomKey: reportMode ? "" : comparison ? "comparison" : stacked ? "stacked" : "axis"
    function sharedZoom() {
        return zoomKey !== "" ? (AppState.singleCrystalZoom[zoomKey] ?? []) : [];
    }
    function takeSharedZoom() {
        if (zoomKey !== "" && String(zoom) !== String(sharedZoom()))
            zoom = sharedZoom();
    }
    onZoomChanged: {
        if (zoomKey === "" || String(zoom) === String(sharedZoom()))
            return;
        const next = Object.assign({}, AppState.singleCrystalZoom);
        next[zoomKey] = Array.from(zoom);
        AppState.singleCrystalZoom = next;
    }
    onZoomKeyChanged: takeSharedZoom()
    Connections {
        target: AppState
        function onSingleCrystalZoomChanged() {
            chart.takeSharedZoom();
        }
    }
    readonly property real fullLow: ApplicationInfo.singleFullRange(false)
    readonly property real fullHigh: ApplicationInfo.singleFullRange(true)
    // The legend: the Stacked chart's experiments, or the one experiment, each name in its points' colour.
    // Sets the legend: the experiments shown, each in its colour, and the selected one marked when the chart does not
    // highlight it.
    function updateLegend() {
        ApplicationInfo.singleUpdateLegend();
    }
    // Hides an experiment's reflections, or shows them again; with the range fitted to the visible ones, fits it once.
    function toggleRow(key) {
        ApplicationInfo.singleToggleRow(key);
    }
    ListedLegendModel {
        id: legendRows
    }
    // The ranges shown move to a zoom or a reset as the Pattern chart's do (the owner, 2026-11-21): one shared animation.
    readonly property real xLow: viewRanges.ranges[0]
    readonly property real xHigh: viewRanges.ranges[1]
    readonly property real yLow: viewRanges.ranges[2]
    readonly property real yHigh: viewRanges.ranges[3]
    RangeAnimation {
        id: viewRanges
        zoom: chart.zoom
        fitted: [chart.simulated ? 0 : chart.fullLow, chart.simulated ? chart.reflections.positionHigh : chart.fullHigh, chart.fullLow, chart.fullHigh]
        duration: chart.reportMode ? 0 : EaStyle.Times.chartAnimation
        active: chart.shown
        immediate: pointer.pressed && Preferences.patternPointerMode !== "zoom"
    }

    // An axis' ticks, every whole step from 0 within its range, and how its labels write them: each tick on its own by
    // the rule for numbers (NumberText.axisFormat). The step leaves room for the widest label as written in the labels'
    // font (NumberText.axisStep), nearest xTicks or yTicks ticks.
    function ticks(low, high, step) {
        const out = [];
        if (!(step > 0) || !(high > low))
            return out;
        for (let i = Math.ceil(low / step - 1e-9); out.length < 64 && i * step <= high + step * 1e-9; ++i)
            out.push(i * step);
        return out;
    }
    readonly property var xFormat: NumberText.axisFormat(ticks(axisX.min, axisX.max, axisX.tickInterval), false)
    readonly property var yFormat: NumberText.axisFormat(ticks(axisY.min, axisY.max, axisY.tickInterval), false)
    EaElements.Label {
        id: labelProbe
        visible: false
    }
    // A tick label in the app's label font, written by that format from the tick Qt Graphs printed with all its
    // decimals.
    // The axes take it as a literal, as the pattern chart's axes do (PatternChart.AxisLabel).
    component TickLabel: Item {
        id: tick
        property string text: ""
        property var format: null
        property int horizontalAlignment: Text.AlignHCenter
        implicitWidth: tickText.implicitWidth
        implicitHeight: tickText.implicitHeight
        EaElements.Label {
            id: tickText
            anchors.fill: parent
            horizontalAlignment: tick.horizontalAlignment
            verticalAlignment: Text.AlignVCenter
            color: chart.colors.chartLabels
            text: tick.format !== null && isFinite(parseFloat(tick.text)) ? NumberText.axisTick(parseFloat(tick.text), tick.format) : tick.text
        }
    }

    // The points the fit uses (`want` true) or leaves out (false) of three parallel lists, by the model's `used`;
    // a report's points are all used.
    function part(x, y, su, used, want) {
        return ApplicationInfo.singlePart(x, y, su, used, want);
    }
    // Draws a model's points on `usedLayer` and the ones its fit leaves out, dimmed, on `leftOutLayer`.
    function drawModel(model, usedLayer, leftOutLayer) {
        ApplicationInfo.singleDrawModel(model, usedLayer, leftOutLayer);
    }

    // Each Stacked layer draws its experiment again.
    signal redrawStacked

    function redraw() {
        ApplicationInfo.singleRedraw();
    }

    // The y = x line across whatever both axes show.
    function drawDiagonal() {
        ApplicationInfo.singleDrawDiagonal();
    }

    onXLowChanged: drawDiagonal()
    onXHighChanged: drawDiagonal()
    onYLowChanged: drawDiagonal()
    onYHighChanged: drawDiagonal()
    Component.onCompleted: {
        takeSharedZoom();
        drawDiagonal();
    }
    onShownChanged: redraw()
    onSquaredChanged: ApplicationInfo.singleStateChanged(0)
    onReflectionsChanged: redraw()
    onReportDataChanged: redraw()
    onStackedExperimentsChanged: redraw()
    onSelectedIndexChanged: chart.updateLegend()
    onProjectChanged: ApplicationInfo.singleStateChanged(1)
    Connections {
        target: Preferences
        function onChartHighlightSelectedChanged() {
            chart.updateLegend();
        }
    }
    Connections {
        target: chart.reflections
        function onPointsChanged() {
            ApplicationInfo.singleModelChanged(false);
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
    // A report figure's reliability (edi::reliability_text) and its reflections' admission line, above its plot at
    // the left, as the pattern chart's.
    EaElements.Label {
        id: reliabilityLabel
        objectName: "singleCrystal.reliability"
        visible: chart.reportMode && text !== ""
        // At the plot's left, or as far right as the figure's margin leaves it whole.
        x: Math.max(chart.sideMargin, Math.min(view.x + view.plotArea.x, chart.width - chart.sideMargin - width))
        y: chart.topMargin
        color: chart.colors.chartLabels
        text: chart.reportMode ? [chart.reportData.title, chart.reportData.statistics || ""].filter(line => line !== "").join("\n") : ""
    }

    // The controls row (ToolbarLines), as the pattern chart's: what both axes plot, then the pattern chart's buttons.
    // Hidden while the reflections are drawn on an axis: the pattern chart below has its own.
    ToolbarLines {
        id: toolbar

        objectName: "singleCrystal.toolbar"
        visible: !chart.reportMode && !chart.onAxis
        x: 0
        y: chart.topMargin
        width: chart.width
        height: implicitHeight
        leftEdge: chart.toolbarLeft
        rightEdge: chart.width - chart.toolbarRightInset

        ToolbarComboBox {
            objectName: "singleCrystal.toolbar.quantity"
            toolTip: qsTr("Plotted quantity")
            model: [qsTr("F²"), qsTr("F")]
            closedTexts: [qsTr("axes: F²"), qsTr("axes: F")]
            shownIndex: chart.squared ? 0 : 1
            onActivated: index => ApplicationInfo.singleQuantityChoice(index)
        }
        // The pattern chart's toolbar, without the included-range button, which has nothing to act on here; the
        // tooltip toggle and the zoom or move mode are the same remembered settings.
        ChartToolbar {
            id: buttons

            // The legend starts shown on the Stacked chart and hidden on the Pattern chart, which follows the
            // pattern charts' remembered choice.
            legendShown: chart.stacked ? true : Preferences.patternLegendShown
            onLegendShownChanged: ApplicationInfo.singleStateChanged(2)
            includedRangeAvailable: false
            hoverShown: Preferences.patternHoverShown
            onHoverShownChanged: Preferences.patternHoverShown = hoverShown
            pointerMode: Preferences.patternPointerMode
            onPointerModeChanged: Preferences.patternPointerMode = pointerMode
            onResetClicked: chart.zoom = []
            // On the Stacked chart: the selected experiment on top and the others faded, or all alike. One app
            // setting for every chart of several datasets.
            highlightAvailable: chart.stacked
            highlightShown: Preferences.chartHighlightSelected
            highlightName: "singleCrystal.toolbar.highlight"
            onHighlightToggled: ApplicationInfo.singleStateChanged(3)
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

    ChartView {
        id: view

        y: chart.reportMode ? chart.topMargin + Math.ceil(reliabilityLabel.height) + Math.round(chart.em * 0.25) : chart.topMargin + toolbar.height + chart.belowToolbar
        width: parent.width
        height: parent.height - y - chart.xTitleHeight - chart.bottomMargin - (chart.reportMode ? Math.round(chart.em * 0.4) : 0)
        // A report figure's numbers reach into the view's margin, up to its title's letters.
        marginLeft: chart.sideMargin + chart.titleGutter + (chart.reportMode ? chart.em : 0)
        marginRight: chart.sideMargin
        marginTop: 0
        marginBottom: 0
        theme: ChartTheme {
            labelTextColor: chart.colors.chartLabels
        }
        axisX: ValueAxis {
            id: axisX
            labelDecimals: 6
            labelDelegate: TickLabel {
                format: chart.xFormat
            }
            min: chart.xLow
            max: chart.xHigh
            tickInterval: NumberText.axisStep(min, max, chart.xTicks, view.plotArea.width, labelProbe.font, true)
            tickAnchor: 0
            lineVisible: false
            gridVisible: false
            subGridVisible: false
        }
        axisY: ValueAxis {
            id: axisY
            labelDecimals: 6
            labelDelegate: TickLabel {
                format: chart.yFormat
                horizontalAlignment: Text.AlignRight
            }
            min: chart.yLow
            max: chart.yHigh
            tickInterval: NumberText.axisStep(min, max, chart.yTicks, view.plotArea.height, labelProbe.font, false)
            tickAnchor: 0
            lineVisible: false
            gridVisible: false
            subGridVisible: false
        }
        // The y = x line, on the chart's own axes, refilled whenever their range changes.
        LineSeries {
            id: diagonal
            visible: !chart.simulated
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
            return ApplicationInfo.singleNearest(px, py);
        }
        function read(px, py) {
            ApplicationInfo.singleHoverRead(px, py);
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
        id: chartLegend

        objectName: "singleCrystal.legend"
        // Over the pointer's area for its hover cue; a click reaches the pointer area, which passes it back.
        z: 1
        colors: chart.colors
        x: view.x + view.plotArea.x + chart.em
        y: view.y + view.plotArea.y + chart.em
        visible: !chart.reportMode && buttons.legendShown && chart.models.length > 0
        entries: legendRows
        toggles: !chart.reportMode
        onToggled: key => chart.toggleRow(key)
    }

    // The axis titles, the dictionary's names of the plotted items, found by name as the pattern chart's are.
    EaElements.Label {
        id: xTitle
        objectName: "singleCrystal.title.x"
        x: view.x + view.plotArea.x + (view.plotArea.width - width) / 2
        y: chart.reportMode ? chart.height - AppSizes.mainAreaMargin - baselineOffset - xInk.tightBoundingRect.y - xInk.tightBoundingRect.height : view.y + view.height + chart.em * 0.6
        color: chart.colors.chartLabels
        text: Session.label(chart.xItem)
        TextMetrics {
            id: xInk
            font: xTitle.font
            text: xTitle.text
        }
    }
    EaElements.Label {
        id: yTitle
        objectName: "singleCrystal.title.y"
        x: chart.sideMargin - Math.round(chart.em * (chart.reportMode ? 0.15 : 0.5))
        y: view.y + view.plotArea.y + (view.plotArea.height + width) / 2
        rotation: -90
        transformOrigin: Item.TopLeft
        color: chart.colors.chartLabels
        text: Session.label(chart.yItem)
    }

    Item {
        id: plot

        x: view.x + view.plotArea.x
        y: view.y + view.plotArea.y
        width: view.plotArea.width
        height: view.plotArea.height
        clip: true

        function ticks(axis: ValueAxis): list<real> {
            return ApplicationInfo.chartGridShares(axis);
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
                visible: !(modelData && chart.hiddenRows.includes(modelData.name))
                // The selected experiment on top and every other faded, while highlighting.
                z: chart.highlight && index === chart.selectedIndex ? 1 : 0
                opacity: chart.highlight && index !== chart.selectedIndex ? Preferences.chartFadedOpacity : 1
                color: AppColors.experiment(index, chart.colors.isDarkPalette)
                fillColor: Qt.alpha(color, 0.3)
                markerSize: 5
                xMin: axisX.min
                xMax: axisX.max
                yMin: axisY.min
                yMax: axisY.max
                Component.onCompleted: redraw()
                Connections {
                    target: stackedLayer.model
                    function onPointsChanged() {
                        ApplicationInfo.singleModelChanged(true);
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
                    fillColor: stackedLayer.fillColor
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
            visible: !chart.stacked && !(chart.experiment && chart.hiddenRows.includes(chart.experiment.name))
            anchors.fill: parent
            color: AppColors.experiment(0, chart.colors.isDarkPalette)
            // Filled light, as the pattern band is (the owner, 2026-11-16).
            fillColor: Qt.alpha(color, 0.3)
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
            visible: layer.visible
            anchors.fill: parent
            opacity: chart.leftOutOpacity
            color: layer.color
            fillColor: layer.fillColor
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
                return ApplicationInfo.chartCoordinate(px, false);
            }
            function yAt(py: real): real {
                return ApplicationInfo.chartCoordinate(py, true);
            }

            objectName: "singleCrystal.pointer"
            anchors.fill: parent
            // A report figure has no pointer, so the wheel scrolls the report.
            enabled: !chart.reportMode
            acceptedButtons: Qt.LeftButton | Qt.RightButton
            hoverEnabled: Preferences.patternHoverShown
            onPressed: mouse => ApplicationInfo.singlePointer(mouse, 0)
            onPositionChanged: mouse => ApplicationInfo.singlePointer(mouse, 1)
            onExited: hoverLabel.hide()
            onReleased: mouse => ApplicationInfo.singlePointer(mouse, 2)
            onWheel: wheel => ApplicationInfo.singlePointer(wheel, 3)

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

    // The reflections on Q or sinθ/λ, with the pattern chart's styles, Bars and colours (onAxis).
    PatternChart {
        id: axisChart

        anchors.fill: parent
        visible: chart.onAxis
        shown: chart.shown && chart.onAxis
        experiment: chart.onAxis ? chart.experiment : null
        singleCrystal: true
        colors: chart.colors
    }
}
