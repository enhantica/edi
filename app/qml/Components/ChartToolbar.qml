// SPDX-License-Identifier: BSD-3-Clause
import QtQuick

import EasyApplication.Gui.Style as EaStyle

import edi.app

// A chart's toolbar (easydiffractionbeta's QtCharts1dTab.qml; edi ADR-0017 §15): a row of square buttons above
// the plot's right edge — the legend, hover coordinates, a spacer, pan, box zoom, reset (Home, as the structure
// view's), Home last (owner, 2026-10-05). The y scale drop-down is at the chart's left (PatternChart). The legend
// and the hover coordinates are on at the start, as there; pan and box zoom exclude each other, and box zoom is on
// at the start.
Row {
    id: toolbar

    property bool legendShown: true
    property bool hoverShown: true
    property string pointerMode: "zoom"  // "zoom" or "pan"
    signal resetClicked

    spacing: AppSizes.toolbarSpacing

    ChartToolButton {
        objectName: "chart.toolbar.legend"
        fontIcon: "align-left"
        toolTip: toolbar.legendShown ? qsTr("Hide legend") : qsTr("Show legend")
        checked: toolbar.legendShown
        onClicked: toolbar.legendShown = !toolbar.legendShown
    }
    ChartToolButton {
        objectName: "chart.toolbar.hover"
        fontIcon: "comment-alt"
        toolTip: qsTr("Show coordinates tooltip on hover")
        checked: toolbar.hoverShown
        onClicked: toolbar.hoverShown = !toolbar.hoverShown
    }
    Item {
        width: EaStyle.Sizes.fontPixelSize * 0.5
        height: 1
    }
    ChartToolButton {
        objectName: "chart.toolbar.pan"
        fontIcon: "arrows-alt"
        toolTip: qsTr("Enable pan")
        checked: toolbar.pointerMode === "pan"
        onClicked: toolbar.pointerMode = "pan"
    }
    ChartToolButton {
        objectName: "chart.toolbar.zoom"
        fontIcon: "expand"
        toolTip: qsTr("Enable box zoom")
        checked: toolbar.pointerMode === "zoom"
        onClicked: toolbar.pointerMode = "zoom"
    }
    ChartToolButton {
        objectName: "chart.toolbar.reset"
        fontIcon: "home"
        toolTip: qsTr("Reset axes")
        onClicked: toolbar.resetClicked()
    }
}
