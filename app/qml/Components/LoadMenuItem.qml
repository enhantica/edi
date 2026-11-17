// SPDX-License-Identifier: BSD-3-Clause
import QtQuick

import EasyApplication.Gui.Animations as EaAnimations
import EasyApplication.Gui.Style as EaStyle
import EasyApplication.Gui.Elements as EaElements

// One entry of a Load menu: its icon and action, and in grey further right the formats or sources it takes. It
// answers the pointer as the app bar's tabs do: a pointing hand, and the icon and label turning to the accent
// colour over the hovered row (the owner, 2026-11-04). Any explanation is a tool tip, never text in the panel
// (the owner, 2026-11-03).
EaElements.MenuItem {
    id: item

    property string hint: ""
    // The labels' column, one width for every item of a menu (its widest label, at least 7.5 em): a menu as wide as
    // its items' implicitWidth then shows every label and hint whole.
    property real labelWidth: EaStyle.Sizes.fontPixelSize * 7.5
    implicitWidth: leftPadding + rightPadding + EaStyle.Sizes.fontPixelSize * 1.25 + labelWidth + 2 * EaStyle.Sizes.fontPixelSize * 0.5 + (item.hint !== "" ? hintMetrics.advanceWidth + EaStyle.Sizes.fontPixelSize * 0.75 : 0)
    TextMetrics {
        id: hintMetrics
        font: item.font
        text: item.hint
    }
    property string toolTip: ""

    readonly property color foreground: !item.enabled ? EaStyle.Colors.themeForegroundDisabled : item.hovered ? EaStyle.Colors.themeForegroundHovered : EaStyle.Colors.themeForeground

    Accessible.name: item.text
    Accessible.description: item.hint
    textFormat: Text.PlainText
    // Items of one section close together (the owner, 2026-11-04); LoadMenuHeader leaves the same gap above the first.
    topPadding: EaStyle.Sizes.fontPixelSize * 0.35
    bottomPadding: EaStyle.Sizes.fontPixelSize * 0.35
    contentItem: Row {
        spacing: EaStyle.Sizes.fontPixelSize * 0.5
        EaElements.Label {
            Accessible.ignored: true
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
            width: item.labelWidth
            elide: Text.ElideRight
            font: item.font
            color: item.foreground
            Behavior on color {
                EaAnimations.ThemeChange {}
            }
            text: item.text
        }
        EaElements.Label {
            Accessible.ignored: true
            anchors.verticalCenter: parent.verticalCenter
            width: Math.max(0, item.availableWidth - EaStyle.Sizes.fontPixelSize * 2.25 - item.labelWidth)
            leftPadding: EaStyle.Sizes.fontPixelSize * 0.75
            elide: Text.ElideRight
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
        requested: item.hovered
    }
}
