// SPDX-License-Identifier: BSD-3-Clause
import QtQuick
import QtGraphs

import edi.app

// The measured-layer benchmark's scene (edi ADR-0017 §15): one GraphsView with either candidate A — a
// ScatterSeries for the markers and a NaN-separated LineSeries for the bars — or candidate B, the
// MeasuredLayer item over the plot area. app/tools/chart_bench.cpp fills and times it.
Item {
    id: root

    property string candidate: "a"
    property color markColor: "#03A9F4"

    GraphsView {
        id: view

        objectName: "view"
        anchors.fill: parent
        axisX: ValueAxis {
            id: axisX
            objectName: "axisX"
        }
        axisY: ValueAxis {
            id: axisY
            objectName: "axisY"
        }

        LineSeries {
            objectName: "bars"
            visible: root.candidate === "a"
            color: root.markColor
            width: 1
        }
        ScatterSeries {
            objectName: "markers"
            visible: root.candidate === "a"
            color: root.markColor
            pointDelegate: Rectangle {
                width: 4
                height: 4
                radius: 2
                color: root.markColor
            }
        }
    }

    MeasuredLayer {
        objectName: "layer"
        visible: root.candidate === "b"
        x: view.x + view.plotArea.x
        y: view.y + view.plotArea.y
        width: view.plotArea.width
        height: view.plotArea.height
        color: root.markColor
        xMin: axisX.min
        xMax: axisX.max
        yMin: axisY.min
        yMax: axisY.max
    }
}
