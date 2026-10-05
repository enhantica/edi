// SPDX-License-Identifier: BSD-3-Clause
pragma ComponentBehavior: Bound

import QtQuick
import QtQuick.Window
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
    // One gap (the owner, 2026-10-02): between the toolbar buttons' bottom and the main pane's top border, above
    // the toolbar, and below the x title.
    readonly property real toolbarGap: em
    readonly property real topMargin: toolbarGap
    readonly property real bottomMargin: toolbarGap
    readonly property real rightMargin: em * 2
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
    // The toolbar ends at the plot areas' right border, one em above the main one.
    readonly property real topHeight: topMargin + toolbar.height + toolbarGap
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
        const edge = Math.round(sideMargin + titleGutter + Math.max(mainAxis, residualAxis));
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

    // An axis label: the app's label, in the app's font and size (easydiffractionbeta's chart labels), placed
    // as Qt Graphs asks. With `original`, it shows the original value of the display value Qt Graphs printed
    // (edi ADR-0021 §5): the main y axis on the square-root and log scales.
    component AxisLabel: Item {
        id: axisLabel

        property string text: ""
        property int horizontalAlignment: Text.AlignHCenter
        property int verticalAlignment: Text.AlignVCenter
        property bool original: false
        // The scale `original` values are read on: the label is printed again when it changes.
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
            color: EaStyle.Colors.chartLabels
            text: axisLabel.original ? controller.axisLabel(axisLabel.text, axisLabel.valueScale) : axisLabel.text
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
            const out = [];
            const span = axis.max - axis.min;
            if (!(axis.tickInterval > 0) || !(span > 0))
                return out;
            const first = Math.ceil((axis.min - axis.tickAnchor) / axis.tickInterval - 1e-9);
            for (let i = first; out.length < 64; ++i) {
                const share = (axis.tickAnchor + i * axis.tickInterval - axis.min) / span;
                if (share > 1 + 1e-9)
                    break;
                out.push(share);
            }
            return out;
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
                color: EaStyle.Colors.chartGridLine
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
                color: EaStyle.Colors.chartGridLine
            }
        }
        // The border, over the grid: the four sides in the axis colour.
        Rectangle {
            anchors.fill: parent
            color: "transparent"
            border.color: EaStyle.Colors.chartAxis
            border.width: EaStyle.Sizes.borderThickness
        }
    }

    // A y title, turned, in the gutter beside its pane's plot area.
    component PaneTitle: EaElements.Label {
        required property GraphsView pane

        rotation: -90
        color: EaStyle.Colors.chartLabels
        x: chart.sideMargin + (chart.titleGutter - width) / 2
        y: pane.y + pane.plotArea.y + (pane.plotArea.height - height) / 2
    }

    PatternChartController {
        id: controller

        // First, so a chart made where it is not shown draws nothing until it is.
        active: chart.shown && chart.visible
        experiment: chart.experiment
        dark: EaStyle.Colors.isDarkPalette
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
        braggSeries0: bragg0
        braggSeries1: bragg1
        braggSeries2: bragg2
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
        }
    }
    // The main y axis has one delegate on every scale: Qt Graphs keeps the labels it made when the delegate is
    // replaced, so a delegate per scale left the square-root axis printing its display values.
    Component {
        id: mainYLabel

        AxisLabel {
            horizontalAlignment: Text.AlignRight
            moveX: chart.tickRoom
            original: controller.yScale !== PatternChartController.Linear
            valueScale: controller.yScale
        }
    }

    Rectangle {
        anchors.fill: parent
        color: EaStyle.Colors.chartBackground
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

    // How far the toolbar's right edge is from the chart's: the block selector row above ends there too.
    readonly property real toolbarRightInset: width - (toolbar.x + toolbar.width)

    ChartToolbar {
        id: toolbar

        x: mainView.x + mainView.plotArea.x + mainView.plotArea.width - width
        y: chart.topMargin
        onResetClicked: controller.reset()
    }
    // The y scale, linear, square root or log, and the x axis, 2θ, time-of-flight or d-spacing, at the chart's
    // left (owner, 2026-10-05). The x axis shows the experiment's own and is disabled until switching exists.
    Row {
        x: chart.sideMargin
        y: chart.topMargin
        spacing: AppSizes.toolbarSpacing

        ToolbarComboBox {
            objectName: "chart.toolbar.yscale"
            toolTip: qsTr("Y scale")
            model: [qsTr("linear"), qsTr("square root"), qsTr("log")]
            // The closed box names its axis (owner, 2026-10-05).
            closedTexts: [qsTr("y: linear"), qsTr("y: square root"), qsTr("y: log")]
            currentIndex: controller.yScale
            onActivated: index => controller.yScale = index
        }
        ToolbarComboBox {
            objectName: "chart.toolbar.xaxis"
            enabled: false
            toolTip: qsTr("X axis")
            model: [qsTr("2θ"), qsTr("time-of-flight"), qsTr("d-spacing")]
            closedTexts: [qsTr("x: 2θ"), qsTr("x: TOF"), qsTr("x: d")]
            currentIndex: ["twoTheta", "timeOfFlight", "dSpacing"].indexOf(chart.xAxis)
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
        }
        LineSeries {
            id: calculatedLine
            objectName: "chart.series.calc"
            color: controller.calculatedColor
            width: 2
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

        LineSeries {
            id: bragg0
            objectName: "chart.series.bragg.0"
            color: controller.braggColor0
            width: 1  // edi::pattern_style_table's `bragg.0` (ADR-0017 §15)
        }
        LineSeries {
            id: bragg1
            objectName: "chart.series.bragg.1"
            color: controller.braggColor1
            width: 1  // edi::pattern_style_table's `bragg.1` (ADR-0017 §15)
        }
        LineSeries {
            id: bragg2
            objectName: "chart.series.bragg.2"
            color: controller.braggColor2
            width: 1  // edi::pattern_style_table's `bragg.2` (ADR-0017 §15)
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
    }

    PaneTitle {
        objectName: "chart.title.y"
        pane: mainView
        text: controller.yTitle
        visible: controller.hasData
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
        color: EaStyle.Colors.chartLabels
        text: controller.xTitle
        visible: controller.hasData
    }

    // The legend, inside the main plot's top right corner.
    // The x axis the pattern is drawn on: "twoTheta", "timeOfFlight" or "dSpacing". Only the experiment's own
    // axis is drawn for now (no switching yet).
    readonly property string xAxis: chart.experiment && chart.experiment.beamMode === ExperimentViewModel.TimeOfFlight ? "timeOfFlight" : "twoTheta"

    // The legend starts at the top right on a 2θ axis and at the top left on a time-of-flight or d-spacing one,
    // where the strong peaks are at the other end (owner, 2026-10-05).
    ChartLegend {
        objectName: "chart.legend"
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

    // The Bragg rows' hover: a tick's structure, position and Miller indices.
    MouseArea {
        id: braggPointer

        objectName: "chart.pointer.bragg"
        x: braggView.x + braggView.plotArea.x
        y: braggView.y + braggView.plotArea.y
        width: braggView.plotArea.width
        height: braggView.plotArea.height
        visible: braggView.visible && toolbar.hoverShown
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
        visible: residualView.visible && toolbar.hoverShown
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
        color: EaStyle.Colors.mainContentBackgroundHalfTransparent
        border.color: EaStyle.Colors.chartGridLine
        border.width: EaStyle.Sizes.borderThickness

        EaElements.Label {
            id: hoverText
            objectName: "chart.hover.text"
            anchors.centerIn: parent
            textFormat: Text.RichText
            color: EaStyle.Colors.themeForeground
        }
    }
}
