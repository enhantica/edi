// SPDX-License-Identifier: BSD-3-Clause
pragma ComponentBehavior: Bound

import QtQuick
import QtQuick.Window
import QtQml.Models
import QtGraphs

import EasyApplication.Gui.Style as EaStyle
import EasyApplication.Gui.Elements as EaElements

import edi.app

// The pattern chart (edi ADR-0017 §15, ADR-0021): three panes on one shared x range — the main pane
// (measured with uncertainty, calculated, background), one row of Bragg ticks per structure, the residual
// — under a toolbar. Its proportions, borders, tick counts, legend and toolbar are
// easydiffractionbeta's (its QtCharts1dTab.qml). It computes nothing: PatternChartController asks the core for
// the presentation and replaces the series below; this file only lays them out and passes the pointer on.
Item {
    id: chart

    objectName: "chart"

    property ExperimentViewModel experiment: null
    // The report's input (edi ADR-0036): set, the chart draws the report model's presentation of `reportExperiment`
    // as it is, with no toolbar and no pointer, so the wheel scrolls what holds it.
    property ReportViewModel report: null
    // The theme colours the chart draws with; a PDF's figure takes the light ones.
    property FigureColors colors: FigureColors {}
    property string reportExperiment: ""
    // Set: the x axis is this project's `_pattern_chart.x_axis` (the Analysis page's chart, which the report follows),
    // an undoable edit saved with the project; else the chart's own choice.
    property ProjectViewModel axisProject: null
    // "pattern" for the app's one pattern chart, whose y scale is an app setting (edi ADR-0031 §2); none for a report
    // figure, whose options are its own.
    property string settingsPage: ""
    // The y scale's tokens as the settings keep them, in PatternChartController.YScale's order.
    readonly property var scaleTokens: ["linear", "sqrt", "log"]
    // The chart is on the page and the tab the window shows: its page binds it (the owner's one-redraw
    // rule). A chart not shown keeps its last drawing and refreshes once, with the latest result, when it
    // is shown again; a chart no page hides is shown.
    property bool shown: true

    readonly property real em: EaStyle.Sizes.fontPixelSize
    readonly property real sideMargin: em
    // The room round the chart, as in easydiffractionbeta: above the toolbar, and between the plot areas' right
    // border and the chart's edge.
    // Every length the panes are laid out by is a whole number of pixels, so the plot areas begin and end on
    // pixels: their 1 px borders and grid lines are sharp, and a pointer position is a position in the plot.
    // One gap (the owner, 2026-10-02): above the toolbar and below the x title.
    readonly property real toolbarGap: em
    readonly property real topMargin: toolbarGap
    readonly property real bottomMargin: toolbarGap
    // The main area's margin (owner, 2026-10-05): right of the plot areas, left of the toolbar's drop-downs, and
    // from the toolbar down to the main plot area.
    readonly property real rightMargin: AppSizes.mainAreaMargin
    readonly property real toolbarLeft: AppSizes.mainAreaMargin
    readonly property real belowToolbar: AppSizes.mainAreaMargin
    // The x labels and the x title, under the bottom pane only; and the gutter the y titles are drawn in. The
    // titles are this file's own labels: Qt Graphs draws an axis title over the axis labels. A view keeps room
    // for its x axis under its plot area, labelled or not: `alignPanes` measures it, so the panes' heights
    // below are their plot areas' heights.
    property real xLabelsHeight: Math.round(em * 1.9)
    property real mainAxisHeight: 0
    readonly property real xTitleHeight: Math.round(em * 1.7)
    // Qt Graphs keeps 15 px between a plot area and its labels for the tick marks, which this chart does not
    // draw: the y labels are moved right by it, to end beside the plot area as easydiffractionbeta's do, and
    // the x labels and the x title up by `labelLift`.
    readonly property real tickRoom: 15
    readonly property real labelLift: tickRoom - Math.round(em * 0.4)
    readonly property real titleGutter: Math.round(em * 1.6)
    // The toolbar ends at the plot areas' right border, one em above the main one. A report figure has no toolbar; its
    // plot starts no closer to the frame's top than to its sides (the owner, 2026-10-13).
    readonly property real topHeight: chart.report ? Math.max(sideMargin, rightMargin) + (chart.reliability !== "" ? Math.round(em * 1.5) : 0) : topMargin + toolbarLines.height + belowToolbar
    // A report figure's reliability text (edi::reliability_text), above its main plot at the left; the app's own
    // charts show it in the page's selector line.
    readonly property string reliability: chart.report && chart.report.model ? chart.report.reliability(chart.reportExperiment) : ""
    // The panes' heights, as easydiffractionbeta divides them: of what the toolbar and the x axis leave, the
    // main pane takes 0.7 and the residual 0.3, each less half of what the tick rows take between them. A
    // structure's row is 1.5 em high, in a pane half an em higher.
    readonly property real paneGap: em
    readonly property real braggPaneHeight: controller.braggRows > 0 ? Math.round((0.5 + 1.5 * controller.braggRows) * em) : 0
    readonly property real between: controller.braggRows > 0 ? braggPaneHeight + 2 * paneGap : paneGap
    readonly property real shared: Math.max(0, height - topHeight - xLabelsHeight + labelLift - xTitleHeight - bottomMargin)
    // With no residual (nothing measured) the tick rows are directly under the main pane, which takes the rest.
    readonly property real mainHeight: Math.round(controller.hasResidual ? shared * 0.7 - between / 2 : controller.braggRows > 0 ? shared - paneGap - braggPaneHeight : shared)
    readonly property real residualHeight: controller.hasResidual ? Math.round(shared * 0.3 - between / 2) : 0
    // The pane the x labels and the x title are under: the lowest one shown — the residual, else the tick
    // rows, else the main pane.
    readonly property GraphsView bottomView: controller.hasResidual ? residualView : controller.braggRows > 0 ? braggView : mainView

    // The values at an axis' ticks: its anchor and every whole interval from it, within its range.
    function tickValues(axis: ValueAxis): list<real> {
        const out = [];
        const span = axis.max - axis.min;
        if (!(axis.tickInterval > 0) || !(span > 0))
            return out;
        const first = Math.ceil((axis.min - axis.tickAnchor) / axis.tickInterval - 1e-9);
        for (let i = first; out.length < 64; ++i) {
            const value = axis.tickAnchor + i * axis.tickInterval;
            if ((value - axis.min) / span > 1 + 1e-9)
                break;
            out.push(value);
        }
        return out;
    }
    // The y labels are NumberText's (the owner, 2026-10-11): `2.5e8` on an axis of large intensities, one
    // exponent for the axis. Each axis' ticks are written in one form, on the main pane in their original
    // values on its scale.
    function yValues(axis: ValueAxis, scale: int): list<real> {
        return tickValues(axis).map(value => controller.originalValue(value, scale));
    }
    readonly property var mainYFormat: NumberText.axisFormat(yValues(mainY, controller.yScale), controller.yScale !== PatternChartController.Log10)
    readonly property var residualYFormat: NumberText.axisFormat(yValues(residualY, PatternChartController.Linear), true)
    // A y label's text: Qt Graphs gives the label its own text of the tick's display value, which names the
    // nearest tick.
    function yLabelText(text: string, axis: ValueAxis, scale: int, format: var): string {
        const shown = Number(text);
        let display = NaN;
        for (const value of tickValues(axis)) {
            if (isNaN(display) || Math.abs(value - shown) < Math.abs(display - shown))
                display = value;
        }
        return isFinite(shown) && !isNaN(display) ? NumberText.axisTick(controller.originalValue(display, scale), format) : text;
    }
    FontMetrics {
        id: labelMetrics
        font: titleProbe.font
    }
    EaElements.Label {
        id: titleProbe
        visible: false
    }
    // The room the widest y label takes beside the plot areas, so the y titles stay clear of the labels.
    readonly property real yLabelsRoom: {
        let widest = 0;
        for (const value of yValues(mainY, controller.yScale))
            widest = Math.max(widest, labelMetrics.advanceWidth(NumberText.axisTick(value, mainYFormat)));
        if (controller.hasResidual) {
            for (const value of yValues(residualY, PatternChartController.Linear))
                widest = Math.max(widest, labelMetrics.advanceWidth(NumberText.axisTick(value, residualYFormat)));
        }
        return Math.ceil(widest + em * 0.5);
    }
    onYLabelsRoomChanged: Qt.callLater(alignPanes)

    // The three plot areas share their left edge. Each view lays its own y labels out, and their widths
    // differ, so each view's left margin makes up the difference. Assigned, not bound: the plot area follows
    // the margin, and a binding on it would read as a loop.
    function alignPanes() {
        const under = view => view.height - view.plotArea.y - view.plotArea.height;
        if (bottomView.plotArea.height > 0 && Math.abs(xLabelsHeight - under(bottomView)) > 0.5)
            xLabelsHeight = under(bottomView);
        if (bottomView !== mainView && mainView.plotArea.height > 0 && Math.abs(mainAxisHeight - under(mainView)) > 0.5)
            mainAxisHeight = under(mainView);
        const mainAxis = mainView.plotArea.x - mainView.marginLeft;
        const residualAxis = residualView.visible ? residualView.plotArea.x - residualView.marginLeft : 0;
        // Far enough right for the y titles and labels, and for the longest structure name of the tick rows (4.8).
        const edge = Math.round(Math.max(sideMargin + titleGutter + Math.max(mainAxis, residualAxis, yLabelsRoom), sideMargin + braggLabelsRoom + braggLabelGap));
        const set = (view, margin) => {
            if (Math.abs(view.marginLeft - margin) > 0.5)
                view.marginLeft = margin;
        };
        set(mainView, edge - mainAxis);
        set(residualView, edge - residualAxis);
        set(braggView, edge - (braggView.plotArea.x - braggView.marginLeft));
    }

    // A pane's theme: Qt Graphs draws the series and nothing else. The chart draws the background, each pane's
    // grid and each pane's border itself (below). Qt Graphs' own tick marks, axis lines and grid are shader
    // effects two pixels wide, over the labels and the measured points; they are transparent here, on every
    // axis of every pane, the Bragg rows' included. (The offscreen platform's software renderer never draws
    // them, so only a capture on an OpenGL platform shows whether they are gone.) The font is the size the
    // axis keeps room for; the labels themselves are `AxisLabel`s. The colour scheme is fixed: every colour the
    // chart shows is its own and follows the app's theme, while a scheme change makes Qt Graphs restore its own
    // axis colours, and the tick marks appeared after a switch of the app's theme (the owner, 2026-10-02).
    component PaneTheme: GraphsTheme {
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

    // An axis label: the app's label, in the app's font and size (easydiffractionbeta's chart labels), placed
    // as Qt Graphs asks. With `original`, it shows the original value of the display value Qt Graphs printed
    // (edi ADR-0021 §5): the main y axis on the square-root and log scales.
    component AxisLabel: Item {
        id: axisLabel

        property string text: ""
        property int horizontalAlignment: Text.AlignHCenter
        property int verticalAlignment: Text.AlignVCenter
        // A y axis' label is written by NumberText (`yLabelText`); an x label is Qt Graphs' text.
        property ValueAxis axis: null
        property var format: null
        // The scale the axis' values are read on: the label is printed again when it changes.
        property int valueScale: PatternChartController.Linear
        // Where the label is moved to, from where Qt Graphs put it.
        property real moveX: 0
        property real moveY: 0

        implicitWidth: axisText.implicitWidth
        implicitHeight: axisText.implicitHeight

        EaElements.Label {
            id: axisText
            x: axisLabel.moveX
            y: axisLabel.moveY
            width: axisLabel.width
            height: axisLabel.height
            horizontalAlignment: axisLabel.horizontalAlignment
            verticalAlignment: axisLabel.verticalAlignment
            color: chart.colors.chartLabels
            text: axisLabel.axis !== null && axisLabel.format !== null ? chart.yLabelText(axisLabel.text, axisLabel.axis, axisLabel.valueScale, axisLabel.format) : axisLabel.text
        }
    }

    // A pane's grid and border, behind everything the pane draws: a hairline at each tick of its two axes
    // in the chart's grid colour, and the plot area's rectangle, closed on all four sides, in the chart's axis
    // colour.
    component PaneGrid: Rectangle {
        id: grid

        required property GraphsView pane
        required property ValueAxis horizontal
        required property ValueAxis vertical
        // The grid lines across the pane, one at each y tick. The lines down it, one at each x tick, are in
        // every pane, so each is one column through all of them; the Bragg rows have those and no others.
        property bool rows: true

        // The ticks of one axis as shares of its range: the anchor and every whole interval from it.
        function ticks(axis: ValueAxis): list<real> {
            return chart.tickValues(axis).map(value => (value - axis.min) / (axis.max - axis.min));
        }

        x: pane.x + pane.plotArea.x
        y: pane.y + pane.plotArea.y
        width: pane.plotArea.width
        height: pane.plotArea.height
        visible: pane.visible
        color: "transparent"
        clip: true

        // The excluded regions (edi ADR-0021 §4): one band in each pane's plot area, under its grid and border, so
        // no band crosses the gaps between the panes or covers a border (the owner, 2026-10-02).
        Repeater {
            model: controller.excludedBands
            delegate: Rectangle {
                required property real xMin
                required property real xMax
                readonly property real span: controller.xMax - controller.xMin

                objectName: "chart.band"
                x: (xMin - controller.xMin) / span * grid.width
                width: (xMax - xMin) / span * grid.width
                height: grid.height
                color: controller.excludedColor
            }
        }
        // A grid line on the pane's edge is the border's place: it is not drawn there, so every border keeps the
        // axis colour (a tick at a range's end had drawn its lighter grid line over the border; the owner,
        // 2026-10-02).
        Repeater {
            model: grid.ticks(grid.horizontal)
            delegate: Rectangle {
                required property real modelData

                x: Math.round(modelData * (grid.width - width))
                visible: x > 0 && x < grid.width - width
                width: EaStyle.Sizes.borderThickness
                height: grid.height
                color: chart.colors.chartGridLine
            }
        }
        Repeater {
            model: grid.rows ? grid.ticks(grid.vertical) : []
            delegate: Rectangle {
                required property real modelData

                y: Math.round((1 - modelData) * (grid.height - height))
                visible: y > 0 && y < grid.height - height
                width: grid.width
                height: EaStyle.Sizes.borderThickness
                color: chart.colors.chartGridLine
            }
        }
        // The border, over the grid: the four sides in the axis colour.
        Rectangle {
            anchors.fill: parent
            color: "transparent"
            border.color: chart.colors.chartAxis
            border.width: EaStyle.Sizes.borderThickness
        }
    }

    // A y title, turned, in the gutter beside its pane's plot area.
    component PaneTitle: EaElements.Label {
        required property GraphsView pane

        rotation: -90
        color: chart.colors.chartLabels
        x: chart.sideMargin + (chart.titleGutter - width) / 2
        y: pane.y + pane.plotArea.y + (pane.plotArea.height - height) / 2
    }

    PatternChartController {
        id: controller

        // First, so a chart made where it is not shown draws nothing until it is. Qt Graphs cannot lay a view out
        // outside a window, so a chart leaving one (a report figure being replaced) draws nothing either.
        active: chart.shown && chart.visible && chart.Window.window !== null
        experiment: chart.experiment
        report: chart.report
        colourScheme: Preferences.patternColours
        structureColourScheme: Preferences.structureColours
        // Each structure's curve, a report figure never (edi ADR-0017 §15).
        structureCurves: !chart.report && Preferences.structureCurves
        // The app's one pattern chart follows the project's x axis (which the report follows too) and the app's y scale.
        dSpacing: chart.axisProject ? chart.axisProject.patternDSpacing : false
        includedOnly: !chart.report && Preferences.chartIncludedOnly
        yScale: chart.settingsPage === "pattern" ? Math.max(0, chart.scaleTokens.indexOf(Preferences.patternYScale)) : PatternChartController.Linear
        reportExperiment: chart.reportExperiment
        dark: chart.colors.isDarkPalette
        plotWidth: mainView.plotArea.width
        plotHeight: mainView.plotArea.height
        residualPlotHeight: residualView.visible ? residualView.plotArea.height : 0
        devicePixelRatio: Screen.devicePixelRatio
        // A box zoom, a wheel zoom and a reset move the ranges as easydiffractionbeta's charts did.
        animationDuration: EaStyle.Times.chartAnimation
        measuredSeries: measuredLine
        measuredLayer: measuredLayer
        calculatedSeries: calculatedLine
        backgroundSeries: backgroundLine
        residualSeries: residualLine
        // How the measured pattern is drawn, one app setting for every pattern chart; a report's chart keeps its own.
        measuredStyle: Preferences.patternMeasuredStyle
    }

    // An x label is centred under its tick; a y label ends beside the plot area.
    Component {
        id: xLabel

        AxisLabel {
            moveY: -chart.labelLift
        }
    }
    Component {
        id: yLabel

        AxisLabel {
            horizontalAlignment: Text.AlignRight
            moveX: chart.tickRoom
            axis: residualY
            format: chart.residualYFormat
        }
    }
    // The main y axis has one delegate on every scale: Qt Graphs keeps the labels it made when the delegate is
    // replaced, so a delegate per scale left the square-root axis printing its display values.
    Component {
        id: mainYLabel

        AxisLabel {
            horizontalAlignment: Text.AlignRight
            moveX: chart.tickRoom
            axis: mainY
            format: chart.mainYFormat
            valueScale: controller.yScale
        }
    }

    Rectangle {
        anchors.fill: parent
        color: chart.colors.chartBackground
    }

    PaneGrid {
        objectName: "chart.frame.main"
        pane: mainView
        horizontal: mainX
        vertical: mainY
    }
    PaneGrid {
        objectName: "chart.frame.bragg"
        pane: braggView
        horizontal: braggX
        vertical: braggY
        rows: false
    }
    PaneGrid {
        objectName: "chart.frame.residual"
        pane: residualView
        horizontal: residualX
        vertical: residualY
    }

    // The measured points and their error bars, over the grid and behind every line: the measured line and
    // the calculated curve are drawn over them.
    MeasuredLayer {
        id: measuredLayer

        objectName: "chart.measured"
        x: mainView.x + mainView.plotArea.x
        y: mainView.y + mainView.plotArea.y
        width: mainView.plotArea.width
        height: mainView.plotArea.height
        color: controller.measuredColor
        markerSize: 5
        xMin: controller.xMin
        xMax: controller.xMax
        yMin: controller.yMin
        yMax: controller.yMax
    }

    // How far the plot areas' right border is from the chart's edge: the block selector row above ends there too.
    readonly property real toolbarRightInset: width - (mainView.x + mainView.plotArea.x + mainView.plotArea.width)

    // The toolbar, the one rule of every chart's (ToolbarLines; the owner, 2026-10-24): every control on one line,
    // centred above the plot, when they fit; else the comboboxes above and the buttons below. The comboboxes: the y
    // scale, linear, square root or log, the x axis, the experiment's own (2θ or time-of-flight) or d-spacing (owner,
    // 2026-10-05), and how the measured data are drawn; the buttons, the chart toolbar's.
    ToolbarLines {
        id: toolbarLines

        x: 0
        y: chart.topMargin
        width: chart.width
        height: implicitHeight
        visible: !chart.report
        centre: mainView.x + mainView.plotArea.x + mainView.plotArea.width / 2
        leftEdge: chart.toolbarLeft
        rightEdge: chart.width - chart.toolbarRightInset

        ToolbarComboBox {
            objectName: "chart.toolbar.yscale"
            toolTip: qsTr("Y scale")
            model: [qsTr("linear"), qsTr("square root"), qsTr("log")]
            // The closed box names its axis (owner, 2026-10-05).
            closedTexts: [qsTr("y: linear"), qsTr("y: square root"), qsTr("y: log")]
            shownIndex: controller.yScale
            onActivated: index => {
                if (chart.settingsPage === "pattern")
                    Preferences.patternYScale = chart.scaleTokens[index];
                else
                    controller.yScale = index;
            }
        }
        ToolbarComboBox {
            objectName: "chart.toolbar.xaxis"
            // d can be chosen once a calculation has given the experiment its d column (the owner, 2026-10-22);
            // the box shows the axis drawn, and names it as its list does; the d axis is "x: d-spacing" in both
            // (the owner, 2026-10-22).
            enabled: chart.experiment !== null && controller.dAvailable
            toolTip: controller.dAvailable ? qsTr("X axis") : qsTr("X axis: d-spacing can be chosen after a calculation")
            readonly property var entries: [chart.nativeAxis === "timeOfFlight" ? qsTr("TOF") : qsTr("2θ"), qsTr("x: d-spacing")]
            model: entries
            closedTexts: entries.map(text => text.startsWith("x: ") ? text : qsTr("x: %1").arg(text))
            shownIndex: controller.dSpacing && controller.dAvailable ? 1 : 0
            onActivated: index => {
                if (chart.axisProject)
                    chart.axisProject.patternDSpacing = index === 1;
                else
                    controller.dSpacing = index === 1;
            }
        }
        // How the measured pattern is drawn (the owner, 2026-10-22), one box of four choices named as the axis boxes
        // name theirs: the band of measured ± s.u., the default, with the residual drawn the same way; the line; the
        // points with their error bars; or both.
        ToolbarComboBox {
            readonly property var tokens: ["band", "line", "points", "linePoints"]
            readonly property var entries: [qsTr("band"), qsTr("line"), qsTr("points"), qsTr("line + points")]

            objectName: "chart.toolbar.measuredStyle"
            visible: !chart.report
            toolTip: qsTr("How the measured data are drawn")
            model: entries
            closedTexts: entries.map(text => qsTr("meas: %1").arg(text))
            shownIndex: Math.max(0, tokens.indexOf(controller.measuredStyle))
            onActivated: index => Preferences.patternMeasuredStyle = tokens[index]
        }
        ChartToolbar {
            id: toolbar

            // The y titles carry the series' colours, so the legend box waits behind its button.
            legendShown: false
            structureCurvesAvailable: !chart.report && controller.hasCalculated
            includedOnly: Preferences.chartIncludedOnly
            onResetClicked: controller.reset()
            onIncludedOnlyToggled: Preferences.chartIncludedOnly = !Preferences.chartIncludedOnly
        }
    }

    GraphsView {
        id: mainView

        objectName: "chart.view.main"
        y: chart.topHeight
        width: parent.width
        height: chart.mainHeight + (chart.bottomView === mainView ? chart.xLabelsHeight : chart.mainAxisHeight)
        marginLeft: chart.sideMargin
        marginRight: chart.rightMargin
        marginTop: 0
        marginBottom: 0
        theme: PaneTheme {}
        onPlotAreaChanged: Qt.callLater(chart.alignPanes)
        axisX: ValueAxis {
            id: mainX
            objectName: "chart.axis.x"
            min: controller.xMin
            max: controller.xMax
            tickInterval: controller.xTickInterval
            tickAnchor: controller.xTickAnchor
            lineVisible: false
            gridVisible: false
            subGridVisible: false
            // The x labels are under the lowest pane only.
            labelsVisible: chart.bottomView === mainView
            labelDelegate: xLabel
        }
        axisY: ValueAxis {
            id: mainY
            objectName: "chart.axis.y"
            min: controller.yMin
            max: controller.yMax
            tickInterval: controller.yTickInterval
            tickAnchor: controller.yTickAnchor
            lineVisible: false
            gridVisible: false
            subGridVisible: false
            labelDelegate: mainYLabel
        }

        // The measured band: measured ± s.u., a soft fill between two thin lines (the band style).
        AreaSeries {
            id: measuredBand
            objectName: "chart.series.meas.band"
            color: Qt.alpha(controller.measuredColor, 0.3)
            borderWidth: 0
            upperSeries: LineSeries {}
            lowerSeries: LineSeries {}
            Component.onCompleted: controller.setBandSeries(0, measuredBand.upperSeries, measuredBand.lowerSeries, measuredBandTop, measuredBandBottom)
        }
        LineSeries {
            id: measuredBandTop
            objectName: "chart.series.meas.band.top"
            color: controller.measuredColor
            width: 1
        }
        LineSeries {
            id: measuredBandBottom
            objectName: "chart.series.meas.band.bottom"
            color: controller.measuredColor
            width: 1
        }
        LineSeries {
            id: measuredLine
            objectName: "chart.series.meas"
            color: controller.measuredColor
            width: 2
        }
        LineSeries {
            id: backgroundLine
            objectName: "chart.series.bkg"
            color: controller.backgroundColor
            width: 1
            // Dashed, as the style table's `line+dash` says (the owner, 2026-10-22).
            strokeStyle: LineSeries.StrokeStyle.DashLine
            dashPattern: [4, 3]
        }
        LineSeries {
            id: calculatedLine
            objectName: "chart.series.calc"
            color: controller.calculatedColor
            width: 2
        }
    }

    // A page's chart follows the app's one pattern view (edi ADR-0017 §15): its ranges and its toolbar's choices. Only
    // the shown chart writes them, so a chart being made or a hidden one never moves the others.
    readonly property bool followsSharedView: chart.settingsPage === "pattern"
    Binding {
        target: controller
        property: "viewRanges"
        value: AppState.patternViewRanges
        when: chart.followsSharedView
    }
    Binding {
        target: controller
        property: "viewRangesAxis"
        value: AppState.patternViewAxis
        when: chart.followsSharedView
    }
    Binding {
        target: toolbar
        property: "legendShown"
        value: Preferences.patternLegendShown
        when: chart.followsSharedView
    }
    Binding {
        target: toolbar
        property: "hoverShown"
        value: Preferences.patternHoverShown
        when: chart.followsSharedView
    }
    Binding {
        target: toolbar
        property: "pointerMode"
        value: Preferences.patternPointerMode
        when: chart.followsSharedView
    }
    Connections {
        target: controller
        enabled: chart.followsSharedView && chart.shown
        // Only different ranges are written: the view this chart was just given comes straight back, and writing it
        // again inside that binding is a loop. The axis the ranges are on goes with them.
        function sameRanges(a, b) {
            if (a.length !== b.length)
                return false;
            for (let i = 0; i < a.length; ++i) {
                if (a[i] !== b[i] && !(isNaN(a[i]) && isNaN(b[i])))
                    return false;
            }
            return true;
        }
        function onViewRangesChanged() {
            if (!sameRanges(controller.viewRanges, AppState.patternViewRanges)) {
                AppState.patternViewAxis = controller.viewRangesAxis;
                AppState.patternViewRanges = controller.viewRanges;
            }
        }
    }
    Connections {
        target: toolbar
        enabled: chart.followsSharedView && chart.shown
        function onLegendShownChanged() {
            Preferences.patternLegendShown = toolbar.legendShown;
        }
        function onHoverShownChanged() {
            Preferences.patternHoverShown = toolbar.hoverShown;
        }
        function onPointerModeChanged() {
            Preferences.patternPointerMode = toolbar.pointerMode;
        }
    }

    // Each structure's curve (edi ADR-0017 §15): a soft fill from the background up to the curve and an outline, in
    // its structure's colour, drawn under the other series and not stacked. The chart keeps one area per structure it
    // has drawn; one not drawn now holds no points and no colour. Qt Graphs kept the last drawing of an area it hid or
    // removed (the owner's Mac, 2026-10-21), so none is.
    // A chart made while the curves are on has its colours before this handler is connected: it counts them once made.
    property int structureCurveSlots: 0
    Connections {
        target: controller
        function onStructureCurveColorsChanged() {
            chart.structureCurveSlots = Math.max(chart.structureCurveSlots, controller.structureCurveColors.length);
        }
        Component.onCompleted: onStructureCurveColorsChanged()
    }
    Instantiator {
        model: chart.structureCurveSlots
        delegate: AreaSeries {
            id: area

            required property int index
            readonly property bool drawn: controller.structureCurves && area.index < controller.structureCurveColors.length
            readonly property color lineColour: controller.structureCurveColors[index] ?? "transparent"
            readonly property color fillColour: controller.structureCurveFills[index] ?? "transparent"
            property LineSeries outline: LineSeries {
                objectName: "chart.series.structure.outline." + area.index
                color: area.drawn ? area.lineColour : "transparent"
                width: 1.5
            }

            objectName: "chart.series.structure." + area.index
            color: area.drawn ? area.fillColour : "transparent"
            borderWidth: 0
            upperSeries: LineSeries {}
            lowerSeries: LineSeries {}

            Component.onCompleted: {
                mainView.insertSeries(0, area.outline);
                mainView.insertSeries(0, area);
                controller.setStructureSeries(area.index, area.upperSeries, area.lowerSeries, area.outline);
            }
        }
    }

    GraphsView {
        id: braggView

        objectName: "chart.view.bragg"
        y: mainView.y + chart.mainHeight + chart.paneGap
        width: parent.width
        height: chart.braggPaneHeight + (chart.bottomView === braggView ? chart.xLabelsHeight : 0)
        visible: controller.braggRows > 0
        marginLeft: chart.sideMargin
        marginRight: chart.rightMargin
        marginTop: 0
        marginBottom: 0
        theme: PaneTheme {}
        onPlotAreaChanged: Qt.callLater(chart.alignPanes)
        onVisibleChanged: Qt.callLater(chart.alignPanes)
        // The ticks, inside the pane's border and over the grid's columns, which PaneGrid draws as it does the
        // other panes' — and nothing else: no axis, no tick mark, no line across and no band behind them. The
        // rows are as high as the pane, on the main pane's x range and between its plot area's left and right
        // edges. With no residual pane under them the rows are the lowest pane, and the x labels are under them.
        axisX: ValueAxis {
            id: braggX
            min: controller.xMin
            max: controller.xMax
            tickInterval: controller.xTickInterval
            tickAnchor: controller.xTickAnchor
            visible: chart.bottomView === braggView
            lineVisible: false
            gridVisible: false
            subGridVisible: false
            labelDelegate: xLabel
        }
        axisY: ValueAxis {
            id: braggY
            min: 0
            max: Math.max(1, controller.braggRows)
            visible: false
            lineVisible: false
            gridVisible: false
            subGridVisible: false
        }
    }

    // One tick series per structure (edi::pattern_style_table's `bragg.<place>` rows, 1 px; ADR-0017 §15), each in
    // its structure's colour, made as structures are added and handed to the controller to fill.
    Instantiator {
        model: controller.braggColors.length
        delegate: LineSeries {
            required property int index
            objectName: "chart.series.bragg." + index
            color: controller.braggColors[index] ?? "transparent"
            width: 1
        }
        onObjectAdded: (index, series) => {
            braggView.addSeries(series);
            controller.setBraggSeries(index, series);
        }
        // A series removed or emptied can keep its last drawing, so it holds one undrawable point first.
        onObjectRemoved: (index, series) => {
            controller.setBraggSeries(index, null);
            const ticks = series as LineSeries;
            ticks.clear();
            ticks.append(NaN, NaN);
            braggView.removeSeries(ticks);
        }
    }

    GraphsView {
        id: residualView

        objectName: "chart.view.residual"
        y: mainView.y + chart.mainHeight + chart.between
        width: parent.width
        height: chart.residualHeight + chart.xLabelsHeight
        visible: controller.hasResidual
        marginLeft: chart.sideMargin
        marginRight: chart.rightMargin
        marginTop: 0
        marginBottom: 0
        theme: PaneTheme {}
        onPlotAreaChanged: Qt.callLater(chart.alignPanes)
        onVisibleChanged: Qt.callLater(chart.alignPanes)
        axisX: ValueAxis {
            id: residualX
            objectName: "chart.axis.x.bottom"
            min: controller.xMin
            max: controller.xMax
            tickInterval: controller.xTickInterval
            tickAnchor: controller.xTickAnchor
            lineVisible: false
            gridVisible: false
            subGridVisible: false
            labelDelegate: xLabel
        }
        axisY: ValueAxis {
            id: residualY
            objectName: "chart.axis.residual"
            min: controller.residualMin
            max: controller.residualMax
            // Three ticks: 0 and a round value on either side.
            tickInterval: controller.residualTickInterval
            tickAnchor: 0
            lineVisible: false
            gridVisible: false
            subGridVisible: false
            labelDelegate: yLabel
        }

        LineSeries {
            id: residualLine
            objectName: "chart.series.resid"
            color: controller.residualColor
            width: 1  // edi::pattern_style_table's `resid` (ADR-0017 §15)
        }
        // The residual's band in the band style: (meas − calc) ± s.u., as the measured band.
        AreaSeries {
            id: residualBand
            objectName: "chart.series.resid.band"
            color: Qt.alpha(controller.residualColor, 0.3)
            borderWidth: 0
            upperSeries: LineSeries {}
            lowerSeries: LineSeries {}
            Component.onCompleted: controller.setBandSeries(1, residualBand.upperSeries, residualBand.lowerSeries, residualBandTop, residualBandBottom)
        }
        LineSeries {
            id: residualBandTop
            objectName: "chart.series.resid.band.top"
            color: controller.residualColor
            width: 1
        }
        LineSeries {
            id: residualBandBottom
            objectName: "chart.series.resid.band.bottom"
            color: controller.residualColor
            width: 1
        }
    }

    PaneTitle {
        objectName: "chart.title.y"
        pane: mainView
        text: controller.yTitle
        visible: controller.hasData
    }
    // Each Bragg row's label at its left (edi::BraggRowLabel): the structure's icon and name in its colour. The widest
    // label sets how far right the panes' shared left edge must be (alignPanes), so a long name never runs into them.
    readonly property real braggLabelGap: Math.round(chart.em * 0.4)
    readonly property real braggLabelsRoom: {
        let widest = 0;
        for (let i = 0; i < braggLabelRepeater.count; ++i) {
            const label = braggLabelRepeater.itemAt(i);
            if (label && label.visible)
                widest = Math.max(widest, label.width);
        }
        return Math.ceil(widest);
    }
    onBraggLabelsRoomChanged: Qt.callLater(alignPanes)
    Repeater {
        id: braggLabelRepeater
        model: controller.braggLabels
        delegate: IconLine {
            required property var modelData

            objectName: "chart.bragg.label"
            visible: braggView.visible
            height: AppSizes.legendRowHeight
            textColor: modelData.color
            segments: [
                {
                    "icon": "layer-group",
                    "color": modelData.color
                },
                {
                    "text": modelData.text
                }
            ]
            x: Math.max(0, braggView.x + braggView.plotArea.x - width - chart.braggLabelGap)
            y: braggView.y + braggView.plotArea.y + (1 - modelData.centre / Math.max(1, controller.braggRows)) * braggView.plotArea.height - height / 2
        }
    }
    PaneTitle {
        objectName: "chart.title.residual"
        pane: residualView
        text: controller.residualTitle
        visible: controller.hasResidual
    }
    EaElements.Label {
        objectName: "chart.title.x"
        x: mainView.x + mainView.plotArea.x + (mainView.plotArea.width - width) / 2
        y: chart.height - chart.bottomMargin - chart.xTitleHeight + (chart.xTitleHeight - height) / 2
        color: chart.colors.chartLabels
        text: controller.xTitle
        visible: controller.hasData
    }

    // The legend, inside the main plot's top right corner.
    // The experiment's own x axis, "twoTheta" or "timeOfFlight", and the one the pattern is drawn on, that or
    // "dSpacing" (the toolbar's x box).
    readonly property string nativeAxis: chart.experiment && chart.experiment.beamMode === ExperimentViewModel.TimeOfFlight ? "timeOfFlight" : "twoTheta"
    readonly property string xAxis: controller.dSpacing ? "dSpacing" : nativeAxis

    EaElements.Label {
        objectName: "chart.reliability"
        visible: chart.reliability !== ""
        x: mainView.x + mainView.plotArea.x
        y: Math.max(0, mainView.y + mainView.plotArea.y - height - Math.round(chart.em * 0.25))
        color: chart.colors.chartLabels
        textFormat: Text.RichText
        text: FactorText.rich(chart.reliability)
    }

    // The legend starts at the top right on a 2θ axis and at the top left on a time-of-flight or d-spacing one,
    // where the strong peaks are at the other end (owner, 2026-10-05).
    ChartLegend {
        objectName: "chart.legend"
        colors: chart.colors
        x: chart.xAxis === "twoTheta" ? mainView.x + mainView.plotArea.x + mainView.plotArea.width - width - chart.em : mainView.x + mainView.plotArea.x + chart.em
        y: mainView.y + mainView.plotArea.y + chart.em
        visible: toolbar.legendShown && controller.hasData
        entries: controller.legend
    }

    // The pointer over the main plot area: a box zoom or a pan by dragging, a zoom about the pointer by the
    // wheel, a reset by a right click, and the nearest point's coordinates while hover coordinates are on.
    MouseArea {
        id: pointer

        property real pressX: 0
        property real pressY: 0
        property real lastX: 0

        objectName: "chart.pointer"
        enabled: !chart.report
        x: mainView.x + mainView.plotArea.x
        y: mainView.y + mainView.plotArea.y
        width: mainView.plotArea.width
        height: mainView.plotArea.height
        acceptedButtons: Qt.LeftButton | Qt.RightButton
        hoverEnabled: toolbar.hoverShown

        onPressed: mouse => {
            pressX = lastX = mouse.x;
            pressY = mouse.y;
        }
        onPositionChanged: mouse => {
            if (pressed && pressedButtons & Qt.LeftButton && toolbar.pointerMode === "pan") {
                controller.panBy(mouse.x - lastX);
                lastX = mouse.x;
            }
            if (toolbar.hoverShown && !pressed)
                hoverLabel.read(0, pointer, mouse);
            else
                hoverLabel.show("", 0, 0);
        }
        onReleased: mouse => {
            if (mouse.button === Qt.RightButton)
                controller.reset();
            else if (toolbar.pointerMode === "zoom")
                controller.zoomTo(pressX, mouse.x, pressY, mouse.y);
        }
        onWheel: wheel => controller.wheelAt(wheel.x, wheel.angleDelta.y)
        onExited: hoverLabel.show("", 0, 0)

        // The box being dragged, as the base's chart draws it (gui-components QtCharts1dBase.qml, easydiffractionbeta's
        // charts): a border in the theme's app-border colour, filled with the same colour half transparent (the
        // owner, 2026-10-02).
        Rectangle {
            objectName: "chart.zoom.box"
            visible: pointer.pressed && pointer.pressedButtons & Qt.LeftButton && toolbar.pointerMode === "zoom"
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

    // The Bragg rows' hover: a tick's structure, position and Miller indices.
    MouseArea {
        id: braggPointer

        objectName: "chart.pointer.bragg"
        x: braggView.x + braggView.plotArea.x
        y: braggView.y + braggView.plotArea.y
        width: braggView.plotArea.width
        height: braggView.plotArea.height
        visible: braggView.visible && toolbar.hoverShown && !chart.report
        acceptedButtons: Qt.NoButton
        hoverEnabled: true
        onPositionChanged: mouse => hoverLabel.read(1, braggPointer, mouse)
        onExited: hoverLabel.show("", 0, 0)
    }

    // The residual's hover: the same read-out as a data point's.
    MouseArea {
        id: residualPointer

        objectName: "chart.pointer.residual"
        x: residualView.x + residualView.plotArea.x
        y: residualView.y + residualView.plotArea.y
        width: residualView.plotArea.width
        height: residualView.plotArea.height
        visible: residualView.visible && toolbar.hoverShown && !chart.report
        acceptedButtons: Qt.NoButton
        hoverEnabled: true
        onPositionChanged: mouse => hoverLabel.read(2, residualPointer, mouse)
        onExited: hoverLabel.show("", 0, 0)
    }

    // The hover read-out, beside the pointer: diffraction-lib's lines, each value in its series' colour
    // (PatternChartController.hoverReadout).
    Rectangle {
        id: hoverLabel

        // The point near the pointer in `pane` (over `area`), if any: its read-out, by the point.
        function read(pane, area, mouse) {
            const at = controller.hoverPoint(mouse.x, mouse.y, pane, area.height);
            show(at.x < 0 ? "" : controller.hoverReadout(mouse.x, mouse.y, pane, area.height), area.x + at.x, area.y + at.y);
        }
        // Right of and above the point, or on the other side where the chart ends.
        function show(text, atX, atY) {
            hoverText.text = text;
            x = atX + chart.em + width <= chart.width ? atX + chart.em : atX - chart.em - width;
            y = atY - height - chart.em * 0.5 >= 0 ? atY - height - chart.em * 0.5 : atY + chart.em;
        }

        objectName: "chart.hover"
        visible: hoverText.text !== ""
        width: hoverText.implicitWidth + chart.em
        height: hoverText.implicitHeight + chart.em * 0.5
        color: chart.colors.mainContentBackgroundHalfTransparent
        border.color: chart.colors.chartGridLine
        border.width: EaStyle.Sizes.borderThickness

        EaElements.Label {
            id: hoverText
            objectName: "chart.hover.text"
            anchors.centerIn: parent
            textFormat: Text.RichText
            color: chart.colors.themeForeground
        }
    }
}
