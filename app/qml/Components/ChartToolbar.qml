// SPDX-License-Identifier: BSD-3-Clause
import QtQuick

import EasyApplication.Gui.Style as EaStyle

import edi.app

// A chart's toolbar (easydiffractionbeta's QtCharts1dTab.qml; edi ADR-0017 §15): a row of square buttons above
// the plot's right edge — the legend, hover coordinates, a spacer, pan, box zoom, reset (Home, as the structure
// view's) — then, after a spacer, the y scale as a drop-down, linear, square root or log, in the structure view's
// drop-down style (the owner, 2026-10-02). The legend and the hover coordinates are on at the start, as there;
// pan and box zoom exclude each other, and box zoom is on at the start.
Row {
    id: toolbar

    // The y scale shown: 0 linear, 1 square root, 2 log (PatternChartController.YScale).
    property int yScale: 0
    property bool legendShown: true
    property bool hoverShown: true
    property string pointerMode: "zoom"  // "zoom" or "pan"
    signal yScaleChosen(int scale)
    signal resetClicked

    spacing: EaStyle.Sizes.fontPixelSize * 0.25

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
    Item {
        width: EaStyle.Sizes.fontPixelSize * 0.5
        height: 1
    }
    ToolbarComboBox {
        objectName: "chart.toolbar.yscale"
        toolTip: qsTr("Y scale")
        model: [qsTr("linear"), qsTr("square root"), qsTr("log")]
        currentIndex: toolbar.yScale
        onActivated: index => toolbar.yScaleChosen(index)
    }
}
