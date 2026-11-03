// SPDX-License-Identifier: BSD-3-Clause
import QtQuick

import EasyApplication.Gui.Style as EaStyle
import EasyApplication.Gui.Globals as EaGlobals
import EasyApplication.Gui.Elements as EaElements

import edi.app

// One square button of a chart's toolbar (easydiffractionbeta's QtCharts1dTab.qml; edi ADR-0017 §15): a Font
// Awesome icon on the content background inside a border in the chart's axis colour, the icon in the accent
// colour while hovered or checked; disabled, both in the theme's disabled colours, as the toolbar's boxes. Shared by
// the pattern chart and, with, the structure view. Not `available`, it looks disabled and ignores clicks but keeps its
// tooltip, which says why.
Rectangle {
    id: button

    property string fontIcon: ""
    property string toolTip: ""
    property bool checked: false
    property bool available: true
    readonly property bool active: enabled && available
    // A button that asks for attention while enabled (the Text tab's ✓): the theme's red, the icon white.
    property bool alert: false
    signal clicked

    width: AppSizes.toolbarControlSize
    height: width
    color: button.alert && button.active ? EaStyle.Colors.red : EaStyle.Colors.contentBackground
    border.color: button.alert && button.active ? EaStyle.Colors.red : button.active ? EaStyle.Colors.chartAxis : EaStyle.Colors.themeBackgroundDisabled
    border.width: EaStyle.Sizes.borderThickness

    EaElements.Label {
        anchors.centerIn: parent
        font.family: EaStyle.Fonts.iconsFamily
        font.pixelSize: EaStyle.Sizes.fontPixelSize * 1.15
        color: !button.active ? EaStyle.Colors.themeForegroundDisabled : button.alert ? "white" : hover.hovered || button.checked ? EaStyle.Colors.themeAccent : EaStyle.Colors.themeForeground
        text: button.fontIcon
    }
    HoverHandler {
        id: hover

        cursorShape: button.available ? Qt.PointingHandCursor : Qt.ArrowCursor
    }
    TapHandler {
        enabled: button.available
        onTapped: button.clicked()
    }
    EaElements.ToolTip {
        text: button.toolTip
        visible: text !== "" && hover.hovered && EaGlobals.Vars.showToolTips
    }
}
