// SPDX-License-Identifier: BSD-3-Clause
import QtQuick

import EasyApplication.Gui.Style as EaStyle
import EasyApplication.Gui.Elements as EaElements

// A group title inside a Load menu, not a choice.
EaElements.MenuItem {
    id: header

    enabled: false
    textFormat: Text.PlainText
    contentItem: EaElements.Label {
        leftPadding: EaStyle.Sizes.fontPixelSize * 2.25
        font.family: header.font.family
        font.pixelSize: header.font.pixelSize
        font.bold: true
        color: EaStyle.Colors.themeForeground
        elide: Text.ElideRight
        text: header.text
    }
}
