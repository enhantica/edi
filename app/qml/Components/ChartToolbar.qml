// SPDX-License-Identifier: BSD-3-Clause
import QtQuick

import EasyApplication.Gui.Style as EaStyle

import edi.app

// A chart's toolbar (easydiffractionbeta's QtCharts1dTab.qml; edi ADR-0017 §15): a row of square buttons above
// the plot's right edge — the legend, hover coordinates, the included range only (ADR-0044), a spacer, pan, box
// zoom, reset (Home, as the structure view's), Home last (owner, 2026-10-05). The y scale drop-down is at the chart's left (PatternChart). The legend
// and the hover coordinates are on at the start, as there; pan and box zoom exclude each other, and box zoom is on
// at the start.
Row {
    id: toolbar

    property bool legendShown: true
    property bool hoverShown: true
    // Whether the chart has a calculated pattern, which each structure's curve needs; the curves' own switch is
    // Preferences.structureCurves, remembered between sessions.
    property bool structureCurvesAvailable: false
    property string pointerMode: "zoom"  // "zoom" or "pan"
    // Only the included range (edi ADR-0044), with the Excluded regions group's eraser icon.
    property bool includedOnly: false
    // Every curve with the background subtracted (edi ADR-0017 §15; one app setting with the scan views), offered when
    // the shown experiment has a background.
    property bool subtractBackground: false
    property bool backgroundAvailable: false
    // A chart without a legend or excluded regions (the single-crystal chart) leaves those buttons out.
    property bool legendAvailable: true
    property bool includedRangeAvailable: true
    signal resetClicked
    signal includedOnlyToggled
    signal subtractBackgroundToggled

    spacing: AppSizes.toolbarSpacing

    ChartToolButton {
        objectName: "chart.toolbar.legend"
        visible: toolbar.legendAvailable
        fontIcon: "align-left"
        toolTip: toolbar.legendShown ? qsTr("Hide legend") : qsTr("Show legend")
        checked: toolbar.legendShown
        onClicked: ApplicationInfo.chartToolbarAction(0)
    }
    ChartToolButton {
        objectName: "chart.toolbar.hover"
        fontIcon: "comment-alt"
        toolTip: qsTr("Show coordinates tooltip on hover")
        checked: toolbar.hoverShown
        onClicked: ApplicationInfo.chartToolbarAction(1)
    }
    ChartToolButton {
        objectName: "chart.toolbar.structureCurves"
        visible: toolbar.structureCurvesAvailable
        fontIcon: "layer-group"
        toolTip: qsTr("Show each structure's curve")
        checked: Preferences.structureCurves
        onClicked: ApplicationInfo.chartToolbarAction(2)
    }
    ChartToolButton {
        objectName: "chart.toolbar.includedRange"
        visible: toolbar.includedRangeAvailable
        fontIcon: "eraser"
        toolTip: qsTr("Show only the included range")
        checked: toolbar.includedOnly
        onClicked: toolbar.includedOnlyToggled()
    }
    ChartToolButton {
        objectName: "chart.toolbar.subtractBackground"
        visible: toolbar.includedRangeAvailable
        available: toolbar.backgroundAvailable
        fontIcon: "chart-area"
        toolTip: toolbar.backgroundAvailable ? qsTr("Subtract the background") : qsTr("Subtract the background: this pattern has no background set")
        checked: toolbar.subtractBackground && toolbar.backgroundAvailable
        onClicked: toolbar.subtractBackgroundToggled()
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
        onClicked: ApplicationInfo.chartToolbarAction(3)
    }
    ChartToolButton {
        objectName: "chart.toolbar.zoom"
        fontIcon: "expand"
        toolTip: qsTr("Enable box zoom")
        checked: toolbar.pointerMode === "zoom"
        onClicked: ApplicationInfo.chartToolbarAction(4)
    }
    ChartToolButton {
        objectName: "chart.toolbar.reset"
        fontIcon: "home"
        toolTip: qsTr("Reset axes")
        onClicked: toolbar.resetClicked()
    }
}
