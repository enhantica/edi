// SPDX-License-Identifier: BSD-3-Clause
import QtQuick

import EasyApplication.Gui.Style as EaStyle
import EasyApplication.Gui.Elements as EaElements

// One entry of a Load menu: its action and, in grey after it, the formats or sources it takes. Any explanation is
// a tool tip, never text in the panel (the owner, 2026-11-03).
EaElements.MenuItem {
    id: item

    property string hint: ""
    property string toolTip: ""

    textFormat: Text.PlainText
    contentItem: Row {
        spacing: EaStyle.Sizes.fontPixelSize * 0.75
        EaElements.Label {
            anchors.verticalCenter: parent.verticalCenter
            font: item.font
            color: item.enabled ? EaStyle.Colors.themeForeground : EaStyle.Colors.themeForegroundDisabled
            text: item.text
        }
        EaElements.Label {
            anchors.verticalCenter: parent.verticalCenter
            font: item.font
            color: EaStyle.Colors.themeForegroundMinor
            text: item.hint
        }
    }
    EaElements.ToolTip {
        text: item.toolTip
        visible: item.hovered && item.toolTip !== ""
    }
}
