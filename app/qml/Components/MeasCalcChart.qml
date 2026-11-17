// SPDX-License-Identifier: BSD-3-Clause
pragma ComponentBehavior: Bound

import QtQuick
import QtGraphs

import EasyApplication.Gui.Style as EaStyle
import EasyApplication.Gui.Elements as EaElements

import edi.app

// A powder's measured against calculated intensity, one point per data point with its s.u. as a bar, and the y = x
// line a perfect model puts them on: the Meas vs calc view (the owner, 2026-11-16). A single crystal's is
// SingleCrystalChart's comparison. Both axes share one range, so the line is the diagonal. Above the plot, as on every
// chart tab, one controls row: the axes' scale, the legend, and the pointer's pan, box zoom and reset.
Item {
    id: chart

    // What the main view's Save image takes when this is the shown tab: the item, its toolbar (hidden while the image
    // is taken), the file name, and whether the toolbar's band is cut off.
    readonly property Item imageItem: chart
    readonly property Item imageToolbar: toolbar
    readonly property string imageName: "meas-vs-calc"
    readonly property bool imageCropsToolbar: true

    objectName: "measCalc.chart"

    property ExperimentViewModel experiment: null
    property FigureColors colors: FigureColors {}
    property bool shown: true
    // Save image's background (SaveImageButton): none while a transparent image is taken.
    property bool transparentImage: false
    property var values: ({
            "calc": [],
            "meas": [],
            "su": [],
            "low": 0,
            "high": 1
        })
    readonly property bool hasData: values.calc.length > 0
    readonly property real em: EaStyle.Sizes.fontPixelSize
    // The single-crystal chart's layout: the controls row a gap below the selector row, centred over the plot, and the
    // plot the main area's margin below it.
    readonly property real topMargin: em
    readonly property real belowToolbar: AppSizes.mainAreaMargin
    readonly property real toolbarLeft: AppSizes.mainAreaMargin
    readonly property real toolbarRightInset: width - (view.x + view.plotArea.x + view.plotArea.width)
    // Both axes' scale, as the pattern chart's y scale: 0 linear, 1 square root, 2 log; one for every page's copy.
    readonly property int axesScale: AppState.measCalcScale
    readonly property var scalePrefixes: ["", "√", "log₁₀ "]
    // The zoomed or moved ranges, [xMin, xMax, yMin, yMax]; empty: the whole data. The pointer sets it, and every
    // page's copy follows it (AppState.measCalcZoom).
    property list<real> zoom: AppState.measCalcZoom
    onZoomChanged: {
        if (String(zoom) !== String(AppState.measCalcZoom))
            AppState.measCalcZoom = zoom;
    }
    Connections {
        target: AppState
        function onMeasCalcZoomChanged() {
            if (String(chart.zoom) !== String(AppState.measCalcZoom))
                chart.zoom = AppState.measCalcZoom;
        }
    }
    // Read by the pointer helpers the single-crystal chart shares: this chart is one dataset, never stacked.
    readonly property bool stacked: false

    function refresh() {
        if (!chart.shown)
            return;
        chart.values = chart.experiment ? chart.experiment.measCalcPoints(chart.axesScale) : {
            "calc": [],
            "meas": [],
            "su": [],
            "low": 0,
            "high": 1
        };
        layer.setPoints(chart.values.calc, chart.values.meas, chart.values.su);
        diagonal.clear();
        diagonal.append(chart.values.low, chart.values.low);
        diagonal.append(chart.values.high, chart.values.high);
        legendRows.setRows(chart.experiment ? [chart.experiment.name] : [], [String(layer.color)], -1, []);
        // Drawn: a followed sequential fit applies its next file once a shown chart has presented this one.
        if (chart.registered !== null && chart.registered === chart.experiment)
            chart.experiment.notePresented();
    }
    // While shown, the chart counts as one showing its experiment, so a running fit (a sequential fit's every
    // dataset) keeps publishing patterns to it as it does for the Pattern tab.
    property ExperimentViewModel registered: null
    function register() {
        const wanted = chart.shown ? chart.experiment : null;
        if (chart.registered === wanted)
            return;
        if (chart.registered)
            chart.registered.showChart(chart, false);
        chart.registered = wanted;
        if (wanted)
            wanted.showChart(chart, true);
    }
    // Another scale or experiment starts from the whole data; showing the tab on another page keeps the zoom.
    onAxesScaleChanged: {
        chart.zoom = [];
        refresh();
    }
    onExperimentChanged: {
        chart.zoom = [];
        register();
        refresh();
    }
    onShownChanged: {
        register();
        refresh();
    }
    Component.onCompleted: {
        register();
        refresh();
    }
    Component.onDestruction: {
        if (chart.registered)
            chart.registered.showChart(chart, false);
    }
    Connections {
        target: chart.experiment
        function onPatternSourceChanged() {
            chart.refresh();
        }
    }

    Rectangle {
        anchors.fill: parent
        color: chart.transparentImage ? "transparent" : chart.colors.chartBackground
    }

    // The controls row: the axes' scale, then the pattern chart's buttons without those that have nothing to act on
    // here (hover read-out, structure curves, included range, background).
    ToolbarLines {
        id: toolbar

        objectName: "measCalc.toolbar"
        x: 0
        y: chart.topMargin
        width: chart.width
        height: implicitHeight
        leftEdge: chart.toolbarLeft
        rightEdge: chart.width - chart.toolbarRightInset

        ToolbarComboBox {
            objectName: "measCalc.toolbar.scale"
            toolTip: qsTr("Axes scale")
            model: [qsTr("Linear"), qsTr("Square root"), qsTr("Log")]
            closedTexts: [qsTr("axes: Linear"), qsTr("axes: Square root"), qsTr("axes: Log")]
            shownIndex: chart.axesScale
            onActivated: index => AppState.measCalcScale = index
        }
        ChartToolbar {
            id: buttons

            legendShown: Preferences.patternLegendShown
            onLegendShownChanged: Preferences.patternLegendShown = legendShown
            hoverAvailable: false
            includedRangeAvailable: false
            pointerMode: Preferences.patternPointerMode
            onPointerModeChanged: Preferences.patternPointerMode = pointerMode
            onResetClicked: chart.zoom = []
        }
        // A click on a button sets the toolbar's own value, which ends the bindings above; these follow the
        // remembered settings again whenever another chart changes them.
        Binding {
            target: buttons
            property: "legendShown"
            value: Preferences.patternLegendShown
        }
        Binding {
            target: buttons
            property: "pointerMode"
            value: Preferences.patternPointerMode
        }
    }

    GraphsView {
        id: view

        y: chart.topMargin + toolbar.height + chart.belowToolbar
        width: parent.width
        height: parent.height - y - chart.em * 3
        marginLeft: AppSizes.mainAreaMargin + chart.em * 2
        marginRight: AppSizes.mainAreaMargin
        marginTop: 0
        theme: ChartTheme {
            labelTextColor: chart.colors.chartLabels
        }
        axisX: ValueAxis {
            id: axisX
            min: chart.zoom.length === 4 ? chart.zoom[0] : chart.values.low
            max: chart.zoom.length === 4 ? chart.zoom[1] : chart.values.high
            lineVisible: false
            gridVisible: false
            subGridVisible: false
        }
        axisY: ValueAxis {
            id: axisY
            min: chart.zoom.length === 4 ? chart.zoom[2] : chart.values.low
            max: chart.zoom.length === 4 ? chart.zoom[3] : chart.values.high
            lineVisible: false
            gridVisible: false
            subGridVisible: false
        }
        LineSeries {
            id: diagonal
            color: chart.colors.chartAxis
            width: 1
        }
    }
    Item {
        x: view.x + view.plotArea.x
        y: view.y + view.plotArea.y
        width: view.plotArea.width
        height: view.plotArea.height
        clip: true

        MeasuredLayer {
            id: layer

            objectName: "measCalc.points"
            anchors.fill: parent
            color: AppColors.experiment(0, chart.colors.isDarkPalette)
            fillColor: Qt.alpha(color, 0.3)
            markerSize: 4
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
        // The pointer, as on the single-crystal chart and with its helper: a box zoom or a move by dragging, by the
        // toolbar's mode; a zoom about the pointer by the wheel; a reset by a right click.
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

            objectName: "measCalc.pointer"
            anchors.fill: parent
            enabled: chart.hasData
            acceptedButtons: Qt.LeftButton | Qt.RightButton
            onPressed: mouse => ApplicationInfo.singlePointer(mouse, 0)
            onPositionChanged: mouse => ApplicationInfo.singlePointer(mouse, 1)
            onReleased: mouse => ApplicationInfo.singlePointer(mouse, 2)
            onWheel: wheel => ApplicationInfo.singlePointer(wheel, 3)

            Rectangle {
                objectName: "measCalc.zoom.box"
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
    // The shared pointer helper hides a hover read-out on every press; this chart has none to hide or fill.
    Item {
        id: hoverLabel

        function hide() {
        }
        function read(px: real, py: real) {
        }
    }
    ListedLegendModel {
        id: legendRows
    }
    // The legend, inside the plot's top left corner, behind the toolbar's legend button.
    ChartLegend {
        id: chartLegend

        objectName: "measCalc.legend"
        z: 1
        colors: chart.colors
        x: view.x + view.plotArea.x + chart.em
        y: view.y + view.plotArea.y + chart.em
        visible: buttons.legendShown && chart.hasData
        entries: legendRows
    }
    EaElements.Label {
        objectName: "measCalc.title.x"
        anchors.horizontalCenter: view.horizontalCenter
        y: view.y + view.height + chart.em * 0.5
        color: chart.colors.chartLabels
        text: chart.scalePrefixes[chart.axesScale] + Session.label("data.intensity_calc")
    }
    EaElements.Label {
        objectName: "measCalc.title.y"
        x: AppSizes.mainAreaMargin
        y: view.y + view.plotArea.y + view.plotArea.height / 2
        rotation: -90
        transformOrigin: Item.TopLeft
        color: chart.colors.chartLabels
        text: chart.scalePrefixes[chart.axesScale] + Session.label("data.intensity_meas")
    }
    EaElements.Label {
        anchors.centerIn: view
        visible: !chart.hasData
        color: chart.colors.chartLabels
        text: qsTr("Measured and calculated intensities are needed: calculate the pattern first")
    }
}
