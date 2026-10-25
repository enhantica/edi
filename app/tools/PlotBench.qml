// SPDX-License-Identifier: BSD-3-Clause
import QtQuick
import QtGraphs

import edi.app

// The plotting benchmark's scene (app/tools/plot_bench.cpp): one GraphsView whose series the benchmark makes here, a
// line or an area per curve, and edi's ScanLines over the plot area for the reference candidates. The QML routes feed
// a series from JavaScript.
Item {
    id: root

    // Per curve, the series the benchmark feeds: a line's own series, or an area's upper and lower series.
    property var feeds: []
    // Per curve, the series that takes its colour: the line, or the area.
    property var owners: []

    function makeCurves(areas: list<bool>, width: real) {
        const feeds = [];
        const owners = [];
        for (let i = 0; i < areas.length; ++i) {
            if (areas[i]) {
                const area = areaSeries.createObject(view, {
                    "borderWidth": width
                });
                view.addSeries(area);
                feeds.push([area.upperSeries, area.lowerSeries]);
                owners.push(area);
            } else {
                const line = lineSeries.createObject(view, {
                    "width": width
                });
                view.addSeries(line);
                feeds.push([line]);
                owners.push(line);
            }
        }
        root.feeds = feeds;
        root.owners = owners;
    }

    // The QML routes: the points handed to JavaScript, then one replace, or one append per point.
    function replaceFromQml(series: XYSeries, points: list<point>) {
        series.replace(points);
    }
    function appendFromQml(series: XYSeries, points: list<point>) {
        series.clear();
        for (let i = 0; i < points.length; ++i)
            series.append(points[i].x, points[i].y);
    }

    Component {
        id: lineSeries

        LineSeries {}
    }
    Component {
        id: areaSeries

        AreaSeries {
            upperSeries: LineSeries {}
            lowerSeries: LineSeries {}
        }
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
