// SPDX-License-Identifier: BSD-3-Clause
pragma ComponentBehavior: Bound

import QtQuick
import QtQuick.Controls
import QtQuick.Window
import QtQml.Models
import QtGraphs

import EasyApplication.Gui.Style as EaStyle
import EasyApplication.Gui.Elements as EaElements
import EasyApplication.Gui.Globals as EaGlobals

import edi.app

// The pattern chart (edi ADR-0017 §15, ADR-0021): three panes on one shared x range — the main pane
// (measured with uncertainty, calculated, background), one row of Bragg ticks per structure, the residual
// — under a toolbar. Its proportions, borders, tick counts, legend and toolbar are
// easydiffractionbeta's (its QtCharts1dTab.qml). It computes nothing: PatternChartController asks the core for
// the presentation and replaces the series below; this file only lays them out and passes the pointer on.
Item {
    id: chart

    // Find k on the chart (owner, 2026-11-27; crysta ADR-0137 A11): the peaks the parent's kept fit leaves unexplained,
    // the strongest marked to start with; a click marks or drops the one nearest it, and Find k ranks the propagation
    // vectors the marked ones allow.
    property bool findKPage: false
    property bool peakMode: false
    property var peakCandidates: []
    property var peakMarks: []
    property int peakParent: -1
    property string peakNote: ""
    // Each marked peak's role under the best-ranked k of the last search, by candidate index.
    property var peakRoles: ({})
    onPeakMarksChanged: peakRoles = ({})
    // The Experiment page's chart is the one the sidebar's k search group edits.
    Binding {
        target: AppState
        property: "kChart"
        value: chart
        when: chart.findKPage
        restoreMode: Binding.RestoreBindingOrValue
    }
    property string addedNote: ""
    property string addedBase: ""
    // Set while this chart's own analysis is open, so the Add it makes does not retire the marks it reads after.
    property bool addingCandidates: false
    readonly property Component kVector: kVectorComponent
    readonly property Component analysis: analysisComponent

    function setPeakMode(on) {
        peakNote = "";
        addedNote = "";
        peakCandidates = [];
        peakMarks = [];
        peakMode = on;
        if (!on || !chart.axisProject)
            return;
        const project = chart.axisProject;
        const experiment = project.currentExperimentIndex;
        peakParent = project.magneticParentOf(experiment);
        if (peakParent === -2) {
            peakNote = qsTr("Several crystal structures are enabled here; disable all but the one to search k for.");
            return;
        }
        if (peakParent < 0) {
            peakNote = qsTr("Link and enable the crystal structure to search k for.");
            return;
        }
        const peaks = project.magneticMarkCandidates(peakParent, experiment);
        if (peaks.length === 0) {
            peakNote = project.lastError !== "" ? project.lastError : qsTr("No peak found in the measured pattern.");
            return;
        }
        peakCandidates = peaks;
        // Pre-marked: the peaks at no reflection the crystal's space group allows; the others stay unmarked.
        const marked = [];
        for (let i = 0; i < peaks.length; ++i)
            if (!peaks[i].suggestion)
                marked.push(i);
        peakMarks = marked;
        if (marked.length === 0)
            peakNote = qsTr("No peak at a forbidden reflection; click peaks to mark them.");
    }
    // Find k: the ranked vectors for the marked peaks; a chosen one opens the analysis here, over this page, so its
    // Add notification comes back to this chart.
    function openKVectors() {
        const popup = chart.kVector.createObject(Overlay.overlay, {
            project: chart.axisProject,
            structureIndex: chart.peakParent,
            experimentIndex: chart.axisProject.currentExperimentIndex,
            marked: chart.peakMarks,
            markedPeaks: chart.peakMarks.map(i => chart.peakCandidates[i])
        }) as KVectorPopup;
        popup.chosen.connect(k => chart.openAnalysis(k));
        popup.open();
    }
    function openAnalysis(k) {
        // The parent the chosen row was found for, by its snapshot, never the chart's current one (review 15, F4).
        const parent = chart.axisProject.propagationParent();
        if (parent < 0) {
            chart.peakNote = qsTr("The data or the structures changed; mark the peaks again.");
            return;
        }
        chart.addingCandidates = true;
        const analysis = chart.analysis.createObject(Overlay.overlay, {
            project: chart.axisProject,
            structureIndex: parent,
            structure: chart.axisProject.structureAt(parent),
            initialK: k,
            selectAfterAdd: false
        }) as MagneticPopup;
        analysis.closed.connect(() => chart.addingCandidates = false);
        analysis.added.connect(count => {
            const base = count === 1 ? qsTr("1 magnetic structure added") : qsTr("%1 magnetic structures added").arg(count);
            const note = chart.axisProject.lastMagneticNote();
            chart.addedNote = note === "" ? base : base + " · " + note;
            chart.addedBase = chart.addedNote;
            intensityCheck.tries = 0;
            intensityCheck.start();
        });
        analysis.open();
    }
    function togglePeakAt(x) {
        let best = -1;
        for (let i = 0; i < peakCandidates.length; ++i) {
            const gap = Math.abs(peakCandidates[i].x - x);
            if (gap <= peakCandidates[i].halfWidth && (best < 0 || gap < Math.abs(peakCandidates[best].x - x)))
                best = i;
        }
        if (best < 0) {
            peakNote = qsTr("No candidate peak there.");
            return;
        }
        peakNote = "";
        addedNote = "";
        const next = peakMarks.slice();
        const at = next.indexOf(best);
        if (at >= 0)
            next.splice(at, 1);
        else
            next.push(best);
        peakMarks = next;
    }

    // One accessible part in the browser, where Qt reads a flat page again for each of its items.
    Accessible.role: Accessible.Grouping
    Accessible.ignored: Qt.platform.os !== "wasm"

    // What the main view's Save image takes when this is the shown tab: the item, its toolbar (hidden while the image
    // is taken), the file name, and whether the toolbar's band is cut off.
    readonly property Item imageItem: chart
    readonly property Item imageToolbar: toolbarLines
    readonly property string imageName: "pattern"
    readonly property bool imageCropsToolbar: true

    objectName: "chart"

    property ExperimentViewModel experiment: null
    // The report's input (edi ADR-0036): set, the chart draws the report model's presentation of `reportExperiment`
    // as it is, with no toolbar and no pointer, so the wheel scrolls what holds it.
    property ReportViewModel report: null
    // The theme colours the chart draws with; a PDF's figure takes the light ones.
    property FigureColors colors: FigureColors {}
    property string reportExperiment: ""
    // Set on the Report page's preview figure: its toolbar with the buttons that act on this figure alone (hover, pan,
    // box zoom, reset); the PDF's copies leave it unset and draw no toolbar.
    property bool reportToolbar: false
    // The pointer, the hover read-outs and the toolbar: an app chart's, or a report preview figure's.
    readonly property bool interactive: !chart.report || chart.reportToolbar
    // Set: the x axis is this project's `_pattern_chart.x_axis` (the Analysis page's chart, which the report follows),
    // an undoable edit saved with the project; else the chart's own choice.
    property ProjectViewModel axisProject: null
    // "pattern" for the app's one pattern chart, whose y scale is an app setting (edi ADR-0031 §2); none for a report
    // figure, whose options are its own.
    property string settingsPage: ""
    // A single crystal's reflections on Q or sinθ/λ (SingleCrystalChart): the x box offers the single crystal's
    // views, a second box F² or F, and the measured styles add Bars (the owner, 2026-11-16).
    property bool singleCrystal: false
    // The single crystal's structure colour, its ticks' (the calculated colour until there are ticks).
    readonly property color structureColor: controller.braggColors.length > 0 ? controller.braggColors[0] : controller.calculatedColor
    // The y scale's tokens as the settings keep them, in PatternChartController.YScale's order.
    readonly property var scaleTokens: ["linear", "sqrt", "log"]
    // The chart is on the page and the tab the window shows: its page binds it (the owner's one-redraw
    // rule). A chart not shown keeps its last drawing and refreshes once, with the latest result, when it
    // is shown again; a chart no page hides is shown.
    property bool shown: true
    // Every curve hidden but the measured data, with the panes left empty (PatternChartController).
    function hideAllButMeasured() {
        controller.hideAllButMeasured();
    }

    readonly property real em: EaStyle.Sizes.fontPixelSize
    // A report figure has the same padding on all four sides as its control buttons have above its plot (the owner,
    // 2026-11-24): the main area's margin.
    // Less what the y title's line keeps beside its letters, so the letters stand at the margin.
    readonly property real sideMargin: chart.report ? AppSizes.mainAreaMargin - Math.round(em * 0.35) : em
    // The room round the chart, as in easydiffractionbeta: above the toolbar, and between the plot areas' right
    // border and the chart's edge.
    // Every length the panes are laid out by is a whole number of pixels, so the plot areas begin and end on
    // pixels: their 1 px borders and grid lines are sharp, and a pointer position is a position in the plot.
    // One gap (the owner, 2026-10-02): above the toolbar and below the x title.
    readonly property real toolbarGap: chart.report ? AppSizes.mainAreaMargin : em
    readonly property real topMargin: toolbarGap
    readonly property real bottomMargin: chart.report ? toolbarGap - Math.round(em * 0.3) : toolbarGap  // as at the side
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
    readonly property real topHeight: chart.report && !chart.reportToolbar ? Math.max(sideMargin, rightMargin) + (chart.reliability !== "" ? Math.round(em * 1.5) : 0) : topMargin + toolbarLines.height + addedLine.room + belowToolbar + (chart.reliability !== "" ? Math.round(em * 1.5) : 0)
    // A report figure's reliability text (edi::reliability_text), above its main plot at the left; the app's own
    // charts show it in the page's selector line.
    readonly property string reliability: chart.report && chart.report.modelRevision >= 0 ? chart.report.reliability(chart.reportExperiment) : ""
    // The panes' heights, as easydiffractionbeta divides them: of what the toolbar and the x axis leave, the
    // main pane takes 0.7 and the residual 0.3, each less half of what the tick rows take between them. A
    // structure's row is 1.5 em high, in a pane half an em higher.
    readonly property real paneGap: em
    readonly property real braggPaneHeight: controller.braggRows > 0 ? Math.round((0.5 + 1.5 * controller.braggRows) * em) : 0
    readonly property real between: controller.braggRows > 0 ? braggPaneHeight + 2 * paneGap : paneGap
    readonly property real shared: Math.max(0, height - topHeight - xLabelsHeight + labelLift - xTitleHeight - bottomMargin)
    // With no residual (nothing measured) the tick rows are directly under the main pane, which takes the rest.
    // In a low window both panes keep their least height where the room holds them.
    readonly property real panes: shared - between
    readonly property real residualShare: shared * 0.3 - between / 2
    readonly property real mainHeight: Math.round(controller.hasResidual ? (residualHeight === Math.round(residualShare) ? shared * 0.7 - between / 2 : panes - residualHeight) : controller.braggRows > 0 ? shared - paneGap - braggPaneHeight : shared)
    readonly property real residualHeight: !controller.hasResidual ? 0 : Math.round(!chart.report && panes >= AppSizes.paneMinimum + AppSizes.residualMinimum - em ? Math.min(Math.max(residualShare, AppSizes.residualMinimum), Math.max(AppSizes.residualMinimum - em, panes - AppSizes.paneMinimum)) : residualShare)
    // The pane the x labels and the x title are under: the lowest one shown — the residual, else the tick
    // rows, else the main pane.
    readonly property GraphsView bottomView: controller.hasResidual ? residualView : controller.braggRows > 0 ? braggView : mainView

    // The values at an axis' ticks: its anchor and every whole interval from it, within its range.
    function tickValues(axis: ValueAxis): list<real> {
        return ApplicationInfo.patternTickValues(axis);
    }
    // The y labels are NumberText's (the owner, 2026-10-11): `2.5e8` on an axis of large intensities, one
    // exponent for the axis. Each axis' ticks are written in one form, on the main pane in their original
    // values on its scale.
    function yValues(axis: ValueAxis, scale: int): list<real> {
        return ApplicationInfo.patternYValues(axis, scale);
    }
    // Each tick on its own by the rule for numbers (NumberText.axisFormat): 500, 1×10³, 1.5×10³. The controller picks
    // each step so the widest label, written in `labelFont`, leaves room between neighbours.
    readonly property var mainYFormat: NumberText.axisFormat(yValues(mainY, controller.yScale), false)
    readonly property var residualYFormat: NumberText.axisFormat(yValues(residualY, PatternChartController.Linear), false)
    // The x labels by the same rule, every pane's from the main pane's ticks (they share the x range). Qt Graphs prints
    // each tick with enough decimals for `yLabelText` to find it, so 2.5 is never read as 3.
    readonly property var xFormat: NumberText.axisFormat(tickValues(mainX), false)
    // A y label's text: Qt Graphs gives the label its own text of the tick's display value, which names the
    // nearest tick.
    function yLabelText(text: string, axis: ValueAxis, scale: int, format: var): string {
        return ApplicationInfo.patternYLabelText(text, axis, scale, format);
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
    readonly property real yLabelsRoom: ApplicationInfo.patternYLabelsRoom()
    onYLabelsRoomChanged: Qt.callLater(alignPanes)

    // The three plot areas share their left edge. Each view lays its own y labels out, and their widths
    // differ, so each view's left margin makes up the difference. Assigned, not bound: the plot area follows
    // the margin, and a binding on it would read as a loop.
    function alignPanes() {
        ApplicationInfo.patternAlignPanes();
    }

    // A pane's theme (ChartTheme): the labels themselves are `AxisLabel`s; the theme's font is the size the axis keeps
    // room for.
    component PaneTheme: ChartTheme {
        labelTextColor: chart.colors.chartLabels
    }

    // An axis label: the app's label, in the app's font and size (easydiffractionbeta's chart labels), placed
    // as Qt Graphs asks. With `original`, it shows the original value of the display value Qt Graphs printed
    // (edi ADR-0021 §5): the main y axis on the square-root and log scales.
    // The axes take their labels as literals: a delegate named by its id is bound only after Qt Graphs, in a chart made a
    // slice at a time, may have drawn its own labels, which it then keeps.
    component AxisLabel: Item {
        id: axisLabel

        property string text: ""
        property int horizontalAlignment: Text.AlignHCenter
        property int verticalAlignment: Text.AlignVCenter
        // A label is written by NumberText (`yLabelText`) from the tick Qt Graphs printed.
        property ValueAxis axis: null
        property var format: null
        // The scale the axis' values are read on: the label is printed again when it changes.
        property int valueScale: PatternChartController.Linear
        // Where the label is moved to, from where Qt Graphs put it.
        property real moveX: 0
        property real moveY: 0

        implicitWidth: axisText.implicitWidth
        implicitHeight: axisText.implicitHeight

        // As wide as its text at least: Qt Graphs sizes the box from its own text and font, narrower than the app's,
        // and the label then ran past it (N1). It keeps its aligned edge: a right-aligned y label grows to the left,
        // into the room the chart keeps for the widest one (yLabelsRoom); a centred one both ways.
        EaElements.Label {
            id: axisText
            readonly property real grown: Math.max(0, implicitWidth - axisLabel.width)
            x: axisLabel.moveX - (axisLabel.horizontalAlignment === Text.AlignRight ? grown : axisLabel.horizontalAlignment === Text.AlignHCenter ? grown / 2 : 0)
            y: axisLabel.moveY
            width: Math.max(axisLabel.width, implicitWidth)
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
            return ApplicationInfo.patternGridTicks(axis);
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
        // The title in full, and a short form shown instead when the full one does not fit its pane at the standard
        // axis-title size: never a smaller font, never cut, never a symbol (the owner, 2026-11-23: "resid" when
        // "meas − calc" does not fit). A title that `shrinks` first takes a smaller font, down to three quarters, and its
        // short form only where that does not fit either.
        property string fullText: ""
        property string shortText: ""
        property bool shrinks: false
        readonly property bool fits: Math.max(0, pane.plotArea.height) >= fullTitle.implicitWidth
        readonly property bool fitsSmall: Math.max(0, pane.plotArea.height) >= fullTitle.implicitWidth * 0.75
        readonly property bool shortShown: (shrinks ? !fitsSmall : !fits) && shortText !== ""
        text: shortShown ? shortText : fullText

        rotation: -90
        color: chart.colors.chartLabels
        font.pixelSize: shortText !== "" && !shrinks ? EaStyle.Sizes.fontPixelSize : Math.round(EaStyle.Sizes.fontPixelSize * Math.max(0.75, Math.min(1, Math.max(0, pane.plotArea.height) / Math.max(1, shortShown ? shortTitle.implicitWidth : fullTitle.implicitWidth))))
        // No longer than its pane is tall, so a short pane's title never runs into the next pane's.
        width: Math.min(implicitWidth, Math.max(0, pane.plotArea.height))
        elide: shortText !== "" && !shrinks ? Text.ElideNone : Text.ElideRight

        Text {
            id: fullTitle
            visible: false
            text: parent.fullText
            textFormat: parent.textFormat
            font.family: parent.font.family
            font.pixelSize: EaStyle.Sizes.fontPixelSize
        }
        Text {
            id: shortTitle
            visible: false
            text: parent.shortText
            textFormat: parent.textFormat
            font.family: parent.font.family
            font.pixelSize: EaStyle.Sizes.fontPixelSize
        }
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
        colourScheme: Preferences.colourScheme
        // Each structure's curve, a report figure never (edi ADR-0017 §15).
        structureCurves: !chart.report && Preferences.structureCurves
        // Hiding a curve from the legend keeps the y range, or fits it to the curves still shown (Preferences).
        hiddenFitsRange: Preferences.chartHiddenRange === "fit"
        // The app's one pattern chart follows the project's x axis (which the report follows too) and the app's y scale.
        xAxis: chart.singleCrystal ? (Preferences.singleCrystalXAxis === "sin_theta_over_lambda" ? "sin_theta_over_lambda" : "q") : chart.axisProject ? chart.axisProject.patternXAxis : "native"
        squared: Preferences.singleCrystalPatternQuantity !== "f"
        thinBars: Preferences.singleCrystalThinBars
        includedOnly: !chart.report && Preferences.chartIncludedOnly
        subtractBackground: !chart.report && Preferences.chartSubtractBackground
        yScale: chart.settingsPage === "pattern" ? Math.max(0, chart.scaleTokens.indexOf(Preferences.patternYScale)) : PatternChartController.Linear
        reportExperiment: chart.reportExperiment
        dark: chart.colors.isDarkPalette
        plotWidth: mainView.plotArea.width
        plotHeight: mainView.plotArea.height
        labelFont: titleProbe.font
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
        // A single crystal without measured reflections draws its calculated ones as bars (the owner, 2026-11-16).
        measuredStyle: !chart.singleCrystal ? Preferences.patternMeasuredStyle : chart.experiment !== null && chart.experiment.singleCrystalReflections.simulated ? "bars" : Preferences.singleCrystalMeasuredStyle
    }

    // Save image's background (SaveImageButton): none while a transparent image is taken.
    property bool transparentImage: false
    Rectangle {
        anchors.fill: parent
        color: chart.transparentImage ? "transparent" : chart.colors.chartBackground
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
        // A single crystal's measured points are filled light, as the band is (the owner, 2026-11-16).
        fillColor: chart.singleCrystal ? Qt.alpha(controller.measuredColor, 0.3) : controller.measuredColor
        markerSize: 5
        xMin: controller.xMin
        xMax: controller.xMax
        yMin: controller.yMin
        yMax: controller.yMax
    }

    // How far the plot areas' right border is from the chart's edge: the block selector row above ends there too.
    readonly property real toolbarRightInset: width - (mainView.x + mainView.plotArea.x + mainView.plotArea.width)

    // The toolbar, the one rule of every chart's (ToolbarLines; the owner, 2026-10-24): every control on one line,
    // centred under the block selector row, when they fit; else the comboboxes above and the buttons below. The
    // comboboxes: the y scale, linear, square root or log, the x axis, the experiment's own (2θ or time-of-flight) or
    // d-spacing (owner, 2026-10-05), and how the measured data are drawn; the buttons, the chart toolbar's.
    ToolbarLines {
        id: toolbarLines

        objectName: "chart.toolbar"
        x: 0
        y: chart.topMargin
        width: chart.width
        height: implicitHeight
        visible: chart.interactive
        leftEdge: chart.toolbarLeft
        rightEdge: chart.width - chart.toolbarRightInset

        ToolbarComboBox {
            objectName: "chart.toolbar.yscale"
            // An app setting: a report figure keeps the project's.
            visible: !chart.report
            toolTip: qsTr("Y scale")
            model: [qsTr("Linear"), qsTr("Square root"), qsTr("Log")]
            // The closed box names its axis (owner, 2026-10-05), its value capitalised (the owner, 2026-10-27).
            closedTexts: [qsTr("y: Linear"), qsTr("y: Square root"), qsTr("y: Log")]
            shownIndex: controller.yScale
            onActivated: index => ApplicationInfo.patternChoice(index, 0)
        }
        // A single crystal's views: calc against meas (SingleCrystalChart's own), or its reflections on Q or sinθ/λ.
        ToolbarComboBox {
            // The comparison of measured with calculated values is the Meas vs calc tab's (the owner, 2026-11-16).
            readonly property var tokens: ["q", "sin_theta_over_lambda"]

            objectName: "chart.toolbar.singleCrystalXAxis"
            visible: chart.singleCrystal && !chart.report
            toolTip: qsTr("X axis")
            model: [qsTr("x: Q"), qsTr("x: %1").arg(Session.label("refln.sin_theta_over_lambda"))]
            shownIndex: Math.max(0, tokens.indexOf(controller.xAxis))
            onActivated: index => Preferences.singleCrystalXAxis = tokens[index]
        }
        ToolbarComboBox {
            objectName: "chart.toolbar.singleCrystalQuantity"
            visible: chart.singleCrystal && !chart.report
            toolTip: qsTr("Plotted quantity")
            model: [qsTr("F²"), Session.optionLabel("reflns.threshold_basis", "amplitude")]
            closedTexts: [qsTr("y: F²"), qsTr("y: F")]
            shownIndex: controller.squared ? 0 : 1
            onActivated: index => Preferences.singleCrystalPatternQuantity = index === 0 ? "f_squared" : "f"
        }
        ToolbarComboBox {
            objectName: "chart.toolbar.xaxis"
            visible: !chart.singleCrystal && !chart.report
            // d, Q and sinθ/λ can be chosen once a calculation has given the experiment its d column (the owner,
            // 2026-10-22); the box shows the axis drawn, and names it as its list does; the d axis is "x: d-spacing"
            // in both (the owner, 2026-10-22). Q = 4π sinθ/λ and sinθ/λ come from d (the owner, 2026-11-14).
            enabled: chart.experiment !== null && controller.dAvailable
            toolTip: controller.dAvailable ? qsTr("X axis") : qsTr("X axis: d-spacing, Q and sinθ/λ can be chosen after a calculation")
            readonly property var tokens: ["native", "d_spacing", "q", "sin_theta_over_lambda"]
            readonly property var entries: [Session.label(chart.nativeAxis === "timeOfFlight" ? "data.time_of_flight" : "data.two_theta"), qsTr("x: %1").arg(Session.optionLabel("pattern_chart.x_axis", "d_spacing")), qsTr("x: Q"), qsTr("x: %1").arg(Session.label("refln.sin_theta_over_lambda"))]
            model: entries
            closedTexts: ApplicationInfo.patternClosedTexts(false)
            shownIndex: controller.dAvailable ? Math.max(0, tokens.indexOf(controller.xAxis)) : 0
            onActivated: index => ApplicationInfo.patternChoice(index, 1)
        }
        // How the measured pattern is drawn (the owner, 2026-10-22), one box of four choices named as the axis boxes
        // name theirs: the band of measured ± s.u., the default, with the residual drawn the same way; the line; the
        // points with their error bars; or both.
        // A single crystal's reflections may also be drawn as bars, one per reflection (the owner, 2026-11-16).
        ToolbarComboBox {
            readonly property var tokens: chart.singleCrystal ? ["band", "line", "points", "linePoints", "bars"] : ["band", "line", "points", "linePoints"]
            readonly property var entries: chart.singleCrystal ? [qsTr("Band"), qsTr("Line"), qsTr("Points"), qsTr("Line + points"), qsTr("Bars")] : [qsTr("Band"), qsTr("Line"), qsTr("Points"), qsTr("Line + points")]

            objectName: "chart.toolbar.measuredStyle"
            // Its own group, apart from the axes (the owner, 2026-11-01).
            toolbarGroup: "measured"
            visible: !chart.report
            toolTip: qsTr("How the measured data are drawn")
            model: entries
            closedTexts: ApplicationInfo.patternClosedTexts(true)
            fitShown: true
            shownIndex: Math.max(0, tokens.indexOf(controller.measuredStyle))
            onActivated: index => {
                if (chart.singleCrystal)
                    Preferences.singleCrystalMeasuredStyle = tokens[index];
                else
                    ApplicationInfo.patternChoice(index, 2);
            }
        }
        // Bars with a width on the axis, or thin lines that stay one pixel at any zoom (the owner, 2026-11-16).
        ChartToolButton {
            objectName: "chart.toolbar.thinBars"
            visible: chart.singleCrystal && controller.measuredStyle === "bars" && !chart.report
            fontIcon: "grip-lines-vertical"
            toolTip: Preferences.singleCrystalThinBars ? qsTr("Draw the reflections as bars") : qsTr("Draw the reflections as thin lines")
            checked: Preferences.singleCrystalThinBars
            onClicked: Preferences.singleCrystalThinBars = !Preferences.singleCrystalThinBars
        }
        ChartToolbar {
            id: toolbar

            // The y titles carry the series' colours, so the legend box waits behind its button.
            legendShown: false
            structureCurvesAvailable: !chart.report && controller.hasCalculated
            // A single crystal's reflections have no excluded regions or background, and leaving their buttons out keeps
            // its controls on one row (two rows above every chart, the owner, 2026-11-16).
            includedRangeAvailable: !chart.singleCrystal && !chart.report
            includedOnly: Preferences.chartIncludedOnly
            subtractBackground: Preferences.chartSubtractBackground
            backgroundAvailable: controller.backgroundAvailable
            onResetClicked: controller.reset()
            onIncludedOnlyToggled: ApplicationInfo.chartToolbarAction(5)
            onSubtractBackgroundToggled: ApplicationInfo.chartToolbarAction(6)
            findKAvailable: chart.findKPage && !chart.report && !chart.singleCrystal && chart.axisProject !== null
            findKActive: chart.peakMode
            onFindKToggled: chart.setPeakMode(!chart.peakMode)
        }
    }

    // After Add, the message on a line of its own under the toolbar, wrapping, so the no-intensity note reads whole
    // and the toolbar keeps its controls (owner, 2026-11-27).
    Item {
        id: addedLine
        readonly property real room: visible ? height + chart.em * 0.5 : 0
        objectName: "chart.findK.added"
        visible: chart.interactive && chart.addedNote !== ""
        x: chart.toolbarLeft
        y: chart.topMargin + toolbarLines.height + chart.em * 0.25
        width: chart.width - chart.toolbarRightInset - chart.toolbarLeft
        height: Math.max(addedText.implicitHeight, openStructure.height)
        EaElements.Label {
            id: addedText
            anchors.left: parent.left
            anchors.right: openStructure.left
            anchors.rightMargin: AppSizes.inputSpacing
            anchors.verticalCenter: parent.verticalCenter
            wrapMode: Text.Wrap
            text: chart.addedNote
        }
        StripButton {
            id: openStructure
            objectName: "chart.findK.openStructure"
            anchors.right: parent.right
            anchors.verticalCenter: parent.verticalCenter
            text: qsTr("Open in Structure page")
            onClicked: {
                chart.addedNote = "";
                EaGlobals.Vars.appBarCurrentIndex = 2;
            }
        }
    }

    // A text button as the chart toolbar draws its buttons: its height, border and colours.
    component StripButton: Rectangle {
        id: strip
        property string text: ""
        signal clicked
        width: stripLabel.implicitWidth + chart.em
        height: AppSizes.toolbarControlSize
        color: EaStyle.Colors.contentBackground
        border.color: enabled ? (stripMouse.containsMouse ? EaStyle.Colors.themeAccent : EaStyle.Colors.chartAxis) : EaStyle.Colors.themeBackgroundDisabled
        border.width: EaStyle.Sizes.borderThickness
        EaElements.Label {
            id: stripLabel
            anchors.centerIn: parent
            text: strip.text
            color: strip.enabled ? EaStyle.Colors.themeForeground : EaStyle.Colors.themeForegroundDisabled
        }
        MouseArea {
            id: stripMouse
            anchors.fill: parent
            hoverEnabled: true
            onClicked: strip.clicked()
        }
    }

    ChartView {
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
            labelDecimals: 6
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
            labelDelegate: AxisLabel {
                moveY: -chart.labelLift
                axis: mainX
                format: chart.xFormat
            }
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
            // One delegate on every scale: Qt Graphs keeps the labels it made when the delegate is replaced, so a delegate
            // per scale left the square-root axis printing its display values.
            labelDelegate: AxisLabel {
                horizontalAlignment: Text.AlignRight
                moveX: chart.tickRoom
                axis: mainY
                format: chart.mainYFormat
                valueScale: controller.yScale
            }
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
        // The calculated bars (the Bars style of a single crystal's reflections): filled as the measured band is,
        // outlined in the calculated colour.
        // A single crystal's are filled in its structure's colour inside the calculated (total) red outline, and drawn in
        // that colour as thin lines (the owner, 2026-11-16).
        AreaSeries {
            id: calculatedBars
            objectName: "chart.series.calc.bars"
            color: Qt.alpha(chart.singleCrystal ? chart.structureColor : controller.calculatedColor, chart.singleCrystal ? 0.6 : 0.3)
            borderWidth: 0
            upperSeries: LineSeries {}
            lowerSeries: LineSeries {}
            Component.onCompleted: controller.setBandSeries(2, calculatedBars.upperSeries, calculatedBars.lowerSeries, calculatedBarsTop, calculatedBarsBottom)
        }
        // Each bar's fill, a line as wide as the bar, under its outline.
        LineSeries {
            id: calculatedBarsBottom
            objectName: "chart.series.calc.bars.fill"
            color: calculatedBars.color
            width: controller.barWidth
            capStyle: Qt.FlatCap
        }
        LineSeries {
            id: calculatedBarsTop
            objectName: "chart.series.calc.bars.top"
            color: chart.singleCrystal && controller.thinBars ? chart.structureColor : controller.calculatedColor
            width: 1
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
            return ApplicationInfo.patternSameRanges(a, b);
        }
        function onViewRangesChanged() {
            ApplicationInfo.patternViewChanged(0);
        }
    }
    Connections {
        target: toolbar
        enabled: chart.followsSharedView && chart.shown
        function onLegendShownChanged() {
            ApplicationInfo.patternViewChanged(1);
        }
        function onHoverShownChanged() {
            ApplicationInfo.patternViewChanged(2);
        }
        function onPointerModeChanged() {
            ApplicationInfo.patternViewChanged(3);
        }
    }

    // Each structure's curve (edi ADR-0017 §15): a soft fill from the background up to the curve and an outline, in
    // its structure's colour, drawn under the other series and not stacked. The chart keeps one area per structure it
    // has drawn; one not drawn now holds no points and no colour. Qt Graphs kept the last drawing of an area it hid or
    // removed (the owner's Mac, 2026-10-21), so none is.
    // A chart made while the curves are on has its colours before this handler is connected: it counts them once made.
    property int structureCurveSlots: 0
    onStructureCurveSlotsChanged: {
        while (structureSlots.count < structureCurveSlots)
            structureSlots.append({
                "slot": structureSlots.count
            });
    }
    // A row each, not a number: a changed number makes every area again, and those before stay drawn for one layout,
    // out of the controller's hands.
    ListModel {
        id: structureSlots
    }
    Connections {
        target: controller
        function onStructureCurveColorsChanged() {
            ApplicationInfo.patternViewChanged(4);
        }
        Component.onCompleted: onStructureCurveColorsChanged()
    }
    Instantiator {
        model: structureSlots
        delegate: AreaSeries {
            id: area

            required property int index
            readonly property bool drawn: controller.structureCurves && area.index < controller.structureCurveColors.length
            readonly property color lineColour: controller.structureCurveColors[index] ?? "transparent"
            readonly property color fillColour: controller.structureCurveFills[index] ?? "transparent"
            // As bars (a single crystal's nuclear and magnetic parts), the line is each bar's fill, as wide as the bar and
            // opaque enough to tell the two parts apart, or a thin line in the part's colour.
            property LineSeries outline: LineSeries {
                objectName: "chart.series.structure.outline." + area.index
                color: !area.drawn ? "transparent" : controller.componentBars && !controller.thinBars ? Qt.alpha(area.lineColour, 0.6) : area.lineColour
                width: controller.componentBars ? controller.barWidth : 1.5
                capStyle: controller.componentBars ? Qt.FlatCap : Qt.SquareCap
            }

            objectName: "chart.series.structure." + area.index
            color: area.drawn ? area.fillColour : "transparent"
            borderWidth: 0
            upperSeries: LineSeries {}
            lowerSeries: LineSeries {}

            Component.onCompleted: ApplicationInfo.patternStructureReady()
        }
    }

    ChartView {
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
            labelDecimals: 6
            min: controller.xMin
            max: controller.xMax
            tickInterval: controller.xTickInterval
            tickAnchor: controller.xTickAnchor
            visible: chart.bottomView === braggView
            lineVisible: false
            gridVisible: false
            subGridVisible: false
            labelDelegate: AxisLabel {
                moveY: -chart.labelLift
                axis: mainX
                format: chart.xFormat
            }
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
    // its structure's colour, made as structures are added and handed to the controller to fill. The chart keeps every
    // series it has made, as it keeps its structure curves: Qt Graphs forgets a removed series only at its next polish,
    // and a hover before that reached the deleted series (a crash on the owner's Mac, 2026-11-18). One past the
    // structures now shown holds no ticks and no colour.
    property int braggSlots: 0
    Connections {
        target: controller
        function onBraggColorsChanged() {
            chart.braggSlots = Math.max(chart.braggSlots, controller.braggColors.length);
        }
        Component.onCompleted: onBraggColorsChanged()
    }
    Instantiator {
        model: chart.braggSlots
        delegate: LineSeries {
            required property int index
            objectName: "chart.series.bragg." + index
            color: controller.braggColors[index] ?? "transparent"
            width: 1
        }
        onObjectAdded: (index, series) => ApplicationInfo.patternBraggSeries(index, series, true)
        // A series removed or emptied can keep its last drawing, so it holds one undrawable point first.
        onObjectRemoved: (index, series) => ApplicationInfo.patternBraggSeries(index, series, false)
    }

    ChartView {
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
            labelDecimals: 6
            objectName: "chart.axis.x.bottom"
            min: controller.xMin
            max: controller.xMax
            tickInterval: controller.xTickInterval
            tickAnchor: controller.xTickAnchor
            lineVisible: false
            gridVisible: false
            subGridVisible: false
            labelDelegate: AxisLabel {
                moveY: -chart.labelLift
                axis: mainX
                format: chart.xFormat
            }
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
            labelDelegate: AxisLabel {
                horizontalAlignment: Text.AlignRight
                moveX: chart.tickRoom
                axis: residualY
                format: chart.residualYFormat
            }
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
        // The band's lower edge, or in the Bars style each residual bar's fill, a line as wide as the bar.
        LineSeries {
            id: residualBandBottom
            readonly property bool bars: controller.measuredStyle === "bars"
            objectName: "chart.series.resid.band.bottom"
            color: bars ? residualBand.color : controller.residualColor
            width: bars ? controller.barWidth : 1
            capStyle: bars ? Qt.FlatCap : Qt.SquareCap
        }
    }

    PaneTitle {
        objectName: "chart.title.y"
        pane: mainView
        fullText: controller.yTitle
        // Its first two names, never "meas, calc, …".
        shrinks: true
        shortText: fullText.split("</font>").length > 3 ? fullText.split("</font>").slice(0, 2).join("</font>") + "</font>" : ""
        visible: controller.hasData
    }
    // Each Bragg row's label at its left (edi::BraggRowLabel): the structure's icon and name in its colour. The widest
    // label sets how far right the panes' shared left edge must be (alignPanes), so a long name never runs into them.
    readonly property real braggLabelGap: Math.round(chart.em * 0.4)
    readonly property real braggLabelsRoom: ApplicationInfo.patternBraggLabelsRoom()
    onBraggLabelsRoomChanged: Qt.callLater(alignPanes)
    Repeater {
        id: braggLabelRepeater
        model: controller.braggLabels
        delegate: IconLine {
            id: braggLabel

            required property var modelData

            // Disabled with its ticks hidden from the legend, as the legend's entry is.
            readonly property color ink: modelData.hidden ? chart.colors.themeForegroundDisabled : modelData.color

            objectName: "chart.bragg.label"
            visible: braggView.visible
            height: AppSizes.legendRowHeight
            textColor: ink
            // A name longer than 20 characters is cut in its middle to about as many, as the legend's, and the full name
            // shows on hover (C1); the panes' left edge (alignPanes) follows the label.
            readonly property string named: modelData.text
            maximumWidth: named.length > 20 ? otherWidth + Math.ceil(braggMetrics.advanceWidth(named.slice(0, 10) + "…" + named.slice(-9))) : 0
            FontMetrics {
                id: braggMetrics
                font.family: EaStyle.Fonts.fontFamily
                font.pixelSize: EaStyle.Sizes.fontPixelSize
            }
            elide: Text.ElideMiddle
            segments: [
                {
                    // A magnetic structure's magnetic row: the magnet, as its group's icon (the owner, 2026-11-03).
                    "icon": modelData.magnetic ? "magnet" : "layer-group",
                    "color": ink
                },
                {
                    // The magnetic row says so beside the name, so its two rows read apart (owner test, 2026-11-27).
                    "text": modelData.magnetic ? qsTr("%1 · magnetic").arg(modelData.text) : modelData.text,
                    "elides": true
                }
            ]
            HoverHandler {
                id: braggLabelHover
            }
            EaElements.ToolTip {
                text: braggLabel.modelData.text
                visible: braggLabelHover.hovered && braggLabel.fullWidth > braggLabel.width + 0.5
            }
            x: Math.max(0, braggView.x + braggView.plotArea.x - width - chart.braggLabelGap)
            y: braggView.y + braggView.plotArea.y + (1 - modelData.centre / Math.max(1, controller.braggRows)) * braggView.plotArea.height - height / 2
        }
    }
    PaneTitle {
        objectName: "chart.title.residual"
        pane: residualView
        fullText: controller.residualTitle
        // "resid" when "meas − calc" does not fit the pane (the owner, 2026-11-23), in the residual's own colour.
        shortText: `<font color="${(controller.residualTitle.match(/color="([^"]+)"/) ?? [])[1] ?? chart.colors.chartLabels}">resid</font>`
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
    // "dSpacing", "q" or "sinThetaOverLambda" (the toolbar's x box).
    readonly property string nativeAxis: chart.experiment && chart.experiment.beamMode === ExperimentViewModel.TimeOfFlight ? "timeOfFlight" : "twoTheta"
    readonly property string xAxis: ({
            "d_spacing": "dSpacing",
            "q": "q",
            "sin_theta_over_lambda": "sinThetaOverLambda"
        })[controller.xAxis] ?? nativeAxis

    EaElements.Label {
        objectName: "chart.reliability"
        visible: chart.reliability !== ""
        x: mainView.x + mainView.plotArea.x
        y: Math.max(0, mainView.y + mainView.plotArea.y - height - Math.round(chart.em * 0.25))
        color: chart.colors.chartLabels
        textFormat: Text.RichText
        text: FactorText.rich(chart.reliability)
    }

    // The legend starts at the top right on a 2θ, Q or sinθ/λ axis and at the top left on a time-of-flight or
    // d-spacing one, where the strong peaks are at the other end (owner, 2026-10-05).
    ChartLegend {
        id: chartLegend

        objectName: "chart.legend"
        // Over the pointer's area for its hover cue; a click reaches the pointer area, which passes it back.
        z: 1
        colors: chart.colors
        x: chart.xAxis === "twoTheta" || chart.xAxis === "q" || chart.xAxis === "sinThetaOverLambda" ? mainView.x + mainView.plotArea.x + mainView.plotArea.width - width - chart.em : mainView.x + mainView.plotArea.x + chart.em
        y: mainView.y + mainView.plotArea.y + chart.em
        visible: toolbar.legendShown && controller.hasData
        entries: controller.legend
        toggles: !chart.report
        onToggled: key => controller.toggleSeries(key)
    }

    // The pointer over the main plot area: a box zoom or a pan by dragging, a zoom about the pointer by the
    // wheel, a reset by a right click, and the nearest point's coordinates while hover coordinates are on.
    MouseArea {
        id: pointer

        property real pressX: 0
        property real pressY: 0
        property real lastX: 0

        objectName: "chart.pointer"
        enabled: chart.interactive
        x: mainView.x + mainView.plotArea.x
        y: mainView.y + mainView.plotArea.y
        width: mainView.plotArea.width
        height: mainView.plotArea.height
        acceptedButtons: Qt.LeftButton | Qt.RightButton
        hoverEnabled: toolbar.hoverShown

        onPressed: mouse => ApplicationInfo.patternPointer(mouse, 0)
        onPositionChanged: mouse => ApplicationInfo.patternPointer(mouse, 1)
        onReleased: mouse => ApplicationInfo.patternPointer(mouse, 2)
        // On the report's preview the wheel scrolls the page, not the chart.
        onWheel: wheel => {
            if (chart.report) {
                wheel.accepted = false;
                return;
            }
            controller.wheelAt(wheel.x, wheel.angleDelta.y);
        }
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
        visible: braggView.visible && toolbar.hoverShown && chart.interactive
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
        visible: residualView.visible && toolbar.hoverShown && chart.interactive
        acceptedButtons: Qt.NoButton
        hoverEnabled: true
        onPositionChanged: mouse => hoverLabel.read(2, residualPointer, mouse)
        onExited: hoverLabel.show("", 0, 0)
    }

    // The hover read-out, beside the pointer: diffraction-lib's lines, each value in its series' colour
    // Find k's marks over the main plot area, on the native axis, and the clicks that mark and drop them.
    Item {
        id: peakLayer
        objectName: "chart.peaks"
        visible: chart.peakMode
        x: mainView.x + mainView.plotArea.x
        y: mainView.y + mainView.plotArea.y
        width: mainView.plotArea.width
        height: mainView.plotArea.height
        readonly property bool native_: controller.xAxis === "native"
        function px(value) {
            return (value - controller.xMin) / Math.max(1e-12, controller.xMax - controller.xMin) * width;
        }

        Repeater {
            model: peakLayer.native_ ? chart.peakCandidates : []
            delegate: Item {
                id: mark
                required property var modelData
                required property int index
                readonly property bool marked: chart.peakMarks.indexOf(index) >= 0
                objectName: `chart.peak.${index}`
                x: peakLayer.px(modelData.x)
                visible: x >= 0 && x <= peakLayer.width
                // A marked peak: a short tick at the top of the plot and a faint line through it; a candidate not
                // marked: the tick alone, grey.
                Rectangle {
                    x: -width / 2
                    width: 1
                    height: peakLayer.height
                    visible: mark.marked
                    color: EaStyle.Colors.themeAccent
                    opacity: 0.35
                }
                Rectangle {
                    x: -width / 2
                    width: mark.marked ? 4 : 2
                    height: chart.em * 0.8
                    radius: 1
                    color: mark.marked ? EaStyle.Colors.themeAccent : EaStyle.Colors.themeForegroundDisabled
                }
            }
        }
        MouseArea {
            anchors.fill: parent
            enabled: chart.peakMode && peakLayer.native_
            onClicked: mouse => chart.togglePeakAt(controller.xMin + mouse.x / Math.max(1, width) * (controller.xMax - controller.xMin))
        }
    }

    // Marks belong to the bank and model they were taken on: a bank change, or an edit or Undo other than this chart's
    // own Add, retires them (review 15, F4).
    Connections {
        target: chart.axisProject
        enabled: chart.peakMode
        function onCurrentExperimentIndexChanged() {
            chart.retireMarks();
        }
        function onEdited() {
            if (!chart.addingCandidates && chart.addedNote === "")
                chart.retireMarks();
        }
        // The roles the best-ranked k gives the peaks it was searched for, in the order they were ticked.
        function onPropagationVectorsFound(found) {
            const roles = {};
            if (found.length > 0)
                chart.peakMarks.forEach((index, at) => roles[index] = found[0].roles[at] ?? "");
            chart.peakRoles = roles;
        }
    }
    function retireMarks() {
        if (chart.peakMarks.length === 0 && chart.peakCandidates.length === 0)
            return;
        chart.peakCandidates = [];
        chart.peakMarks = [];
        chart.peakNote = qsTr("The data or the structures changed; mark the peaks again.");
    }

    // After Add: once the recalculated pattern holds the first new structure, the marked peaks where it puts no
    // magnetic intensity are named (owner, 2026-11-27).
    Timer {
        id: intensityCheck
        property int tries: 0
        interval: 500
        repeat: true
        onTriggered: {
            if (++tries > 40 || !chart.axisProject) {
                stop();
                return;
            }
            const marks = chart.peakMarks.map(i => chart.peakCandidates[i]).filter(p => p !== undefined);
            const found = chart.axisProject.magneticIntensityAt(chart.axisProject.currentExperimentIndex, marks.map(p => p.x), marks.map(p => p.halfWidth));
            if (found.values === undefined)
                return;
            stop();
            const none = [];
            for (let i = 0; i < marks.length; ++i)
                if (found.values[i] < Math.max(1.0, 0.01 * found.max))
                    none.push(marks[i].x.toFixed(2) + "°");
            if (none.length > 0)
                chart.addedNote = qsTr("%1 · %2 gives no magnetic intensity at %3").arg(chart.addedBase).arg(found.structure).arg(none.join(", "));
        }
    }

    Component {
        id: kVectorComponent
        KVectorPopup {}
    }
    Component {
        id: analysisComponent
        MagneticPopup {}
    }

    // (PatternChartController.hoverReadout).
    Rectangle {
        id: hoverLabel

        // The point near the pointer in `pane` (over `area`), if any: its read-out, by the point.
        function read(pane, area, mouse) {
            ApplicationInfo.patternHoverRead(pane, area, mouse);
        }
        // Right of and above the point, or on the other side where the chart ends.
        function show(text, atX, atY) {
            ApplicationInfo.patternHoverShow(text, atX, atY);
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
