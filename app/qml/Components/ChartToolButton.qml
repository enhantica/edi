// SPDX-License-Identifier: BSD-3-Clause
import QtQuick

import EasyApplication.Gui.Style as EaStyle
import EasyApplication.Gui.Globals as EaGlobals
import EasyApplication.Gui.Elements as EaElements

// One square button of a chart's toolbar (easydiffractionbeta's QtCharts1dTab.qml; edi ADR-0017 §15): a Font
// Awesome icon on the content background inside a border in the chart's axis colour, the icon in the accent
// colour while hovered or checked. Shared by the pattern chart and, with, the structure view.
Rectangle {
    id: button

    property string fontIcon: ""
    property string toolTip: ""
    property bool checked: false
    signal clicked

    width: Math.round(EaStyle.Sizes.fontPixelSize * 2.5)
    height: width
    color: EaStyle.Colors.contentBackground
    border.color: EaStyle.Colors.chartAxis
    border.width: EaStyle.Sizes.borderThickness

    EaElements.Label {
        anchors.centerIn: parent
        font.family: EaStyle.Fonts.iconsFamily
        font.pixelSize: EaStyle.Sizes.fontPixelSize * 1.15
        color: hover.hovered || button.checked ? EaStyle.Colors.themeAccent : EaStyle.Colors.themeForeground
        text: button.fontIcon
    }
    HoverHandler {
        id: hover
    }
    TapHandler {
        onTapped: button.clicked()
    }
    EaElements.ToolTip {
        text: button.toolTip
        visible: text !== "" && hover.hovered && EaGlobals.Vars.showToolTips
    }
}
