// SPDX-License-Identifier: BSD-3-Clause
import QtQuick

import EasyApplication.Gui.Animations as EaAnimations
import EasyApplication.Gui.Globals as EaGlobals
import EasyApplication.Gui.Style as EaStyle
import EasyApplication.Gui.Elements as EaElements

// One entry of a Load menu: its icon and action, and in grey further right the formats or sources it takes. It
// answers the pointer as the app bar's tabs do: a pointing hand, and the icon and label turning to the accent
// colour over the hovered row (the owner, 2026-11-04). Any explanation is a tool tip, never text in the panel
// (the owner, 2026-11-03).
EaElements.MenuItem {
    id: item

    property string hint: ""
    property string toolTip: ""
    property string fontIcon: ""

    readonly property color foreground: !item.enabled ? EaStyle.Colors.themeForegroundDisabled : item.hovered ? EaStyle.Colors.themeForegroundHovered : EaStyle.Colors.themeForeground

    textFormat: Text.PlainText
    contentItem: Row {
        spacing: EaStyle.Sizes.fontPixelSize * 0.5
        EaElements.Label {
            anchors.verticalCenter: parent.verticalCenter
            width: EaStyle.Sizes.fontPixelSize * 1.25
            horizontalAlignment: Text.AlignHCenter
            font.family: EaStyle.Fonts.iconsFamily
            font.pixelSize: item.font.pixelSize
            color: item.foreground
            Behavior on color {
                EaAnimations.ThemeChange {}
            }
            text: item.fontIcon
        }
        EaElements.Label {
            anchors.verticalCenter: parent.verticalCenter
            font: item.font
            color: item.foreground
            Behavior on color {
                EaAnimations.ThemeChange {}
            }
            text: item.text
        }
        EaElements.Label {
            anchors.verticalCenter: parent.verticalCenter
            leftPadding: EaStyle.Sizes.fontPixelSize * 0.75
            font: item.font
            color: EaStyle.Colors.themeForegroundMinor
            text: item.hint
        }
    }
    HoverHandler {
        enabled: item.enabled
        cursorShape: Qt.PointingHandCursor
    }
    EaElements.ToolTip {
        text: item.toolTip
        visible: item.hovered && item.toolTip !== "" && EaGlobals.Vars.showToolTips
    }
}
