// SPDX-License-Identifier: BSD-3-Clause
pragma ComponentBehavior: Bound

import QtQuick

import EasyApplication.Gui.Style as EaStyle

import edi.app

// A chart's legend (easydiffractionbeta's QtCharts1dTab.qml; edi ADR-0017 §15): one line per series in the
// series' colour — its mark and its name, and for a structure's ticks "Bragg peaks", the structure icon and
// the structure's name — in the order the core's presentation lists them.
Rectangle {
    id: legend

    // The rows: the chart controller's legend model, with the roles `label`, `color`, `mark` and `bragg`.
    property ChartLegendModel entries: null

    width: column.width
    height: column.height
    color: EaStyle.Colors.mainContentBackgroundHalfTransparent
    border.color: EaStyle.Colors.chartGridLine
    border.width: EaStyle.Sizes.borderThickness

    Column {
        id: column

        leftPadding: EaStyle.Sizes.fontPixelSize
        rightPadding: EaStyle.Sizes.fontPixelSize
        topPadding: EaStyle.Sizes.fontPixelSize * 0.5
        bottomPadding: EaStyle.Sizes.fontPixelSize * 0.5

        Repeater {
            model: legend.entries
            delegate: IconLine {
                id: entry

                required property string label
                required property color color
                required property string mark
                required property bool bragg

                objectName: "chart.legend.entry"
                textColor: color
                segments: bragg ? [
                    {
                        "text": mark + "  " + qsTr("Bragg peaks")
                    },
                    {
                        "icon": "layer-group",
                        "color": color
                    },
                    {
                        "text": label
                    }
                ] : [
                    {
                        "text": mark + "  " + label
                    }
                ]
            }
        }
    }
}
