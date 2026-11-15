// SPDX-License-Identifier: BSD-3-Clause
pragma ComponentBehavior: Bound

import QtQuick
import QtGraphs

import EasyApplication.Gui.Style as EaStyle
import EasyApplication.Gui.Elements as EaElements

import edi.app

// A powder's measured against calculated intensity, one point per data point with its s.u. as a bar, and the y = x
// line a perfect model puts them on: the Meas vs calc view (the owner, 2026-11-16). A single crystal's is
// SingleCrystalChart's comparison. Both axes share one range, so the line is the diagonal.
Item {
    id: chart

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

    function refresh() {
        if (!chart.shown)
            return;
        chart.values = chart.experiment ? chart.experiment.measCalcPoints() : {
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
    }
    onExperimentChanged: refresh()
    onShownChanged: refresh()
    Component.onCompleted: refresh()
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

    Row {
        id: toolbar

        anchors.right: parent.right
        anchors.rightMargin: AppSizes.mainAreaMargin
        y: chart.em
        SaveImageButton {
            objectName: "measCalc.toolbar.save"
            target: chart
            fileName: "meas-vs-calc"
        }
    }

    GraphsView {
        id: view

        y: toolbar.y + toolbar.height + AppSizes.mainAreaMargin
        width: parent.width
        height: parent.height - y - chart.em * 3
        marginLeft: AppSizes.mainAreaMargin + chart.em * 2
        marginRight: AppSizes.mainAreaMargin
        theme: ChartTheme {
            labelTextColor: chart.colors.chartLabels
        }
        axisX: ValueAxis {
            id: axisX
            min: chart.values.low
            max: chart.values.high
            lineVisible: false
            gridVisible: false
            subGridVisible: false
        }
        axisY: ValueAxis {
            id: axisY
            min: chart.values.low
            max: chart.values.high
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
    }
    EaElements.Label {
        objectName: "measCalc.title.x"
        anchors.horizontalCenter: view.horizontalCenter
        y: view.y + view.height + chart.em * 0.5
        color: chart.colors.chartLabels
        text: Session.label("data.intensity_calc")
    }
    EaElements.Label {
        objectName: "measCalc.title.y"
        x: AppSizes.mainAreaMargin
        y: view.y + view.plotArea.y + view.plotArea.height / 2
        rotation: -90
        transformOrigin: Item.TopLeft
        color: chart.colors.chartLabels
        text: Session.label("data.intensity_meas")
    }
    EaElements.Label {
        anchors.centerIn: view
        visible: !chart.hasData
        color: chart.colors.chartLabels
        text: qsTr("Measured and calculated intensities are needed: calculate the pattern first")
    }
}
