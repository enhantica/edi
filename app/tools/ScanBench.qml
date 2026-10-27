// SPDX-License-Identifier: BSD-3-Clause
import QtQuick
import QtGraphs

import edi.app

// The scan views' renderer benchmark's scene (edi ADR-0041): candidate a, one GraphsView with a LineSeries per
// pattern, made here, or candidate b, the ScanLines item over the GraphsView's plot area; both filled from C++
// (app/tools/scan_bench.cpp).
Item {
    id: root

    property var series: []

    function makeSeries(count: int, width: real) {
        const made = [];
        for (let i = 0; i < count; ++i) {
            const line = lineSeries.createObject(view, {
                "width": width
            });
            view.addSeries(line);
            made.push(line);
        }
        series = made;
    }

    Component {
        id: lineSeries

        LineSeries {}
    }

    GraphsView {
        id: view

        objectName: "view"
        anchors.fill: parent
        axisX: ValueAxis {
            objectName: "axisX"
        }
        axisY: ValueAxis {
            id: axisY

            objectName: "axisY"
        }
    }

    ScanLines {
        objectName: "lines"
        x: view.x + view.plotArea.x
        y: view.y + view.plotArea.y
        width: view.plotArea.width
        height: view.plotArea.height
        yMin: axisY.min
        yMax: axisY.max
    }
}
