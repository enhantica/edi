// SPDX-License-Identifier: BSD-3-Clause
import QtQuick

import EasyApplication.Gui.Style as EaStyle
import EasyApplication.Gui.Elements as EaElements

// A button of the likes and survey bars: an optional coloured icon and its text, 14 px, no side padding (the bar's one
// gap is the space between items).
EaElements.Button {
    id: choice

    property color iconColor: foregroundColor()

    height: 32
    font.pixelSize: 14
    leftPadding: 0
    rightPadding: 0
    contentItem: Row {
        spacing: EaStyle.Sizes.fontPixelSize * 0.5

        EaElements.Label {
            anchors.verticalCenter: parent.verticalCenter
            visible: choice.fontIcon !== ""
            font.family: EaStyle.Fonts.iconsFamily
            font.pixelSize: 14
            color: choice.iconColor
            text: choice.fontIcon
        }
        EaElements.Label {
            anchors.verticalCenter: parent.verticalCenter
            font.pixelSize: 14
            color: choice.foregroundColor()
            text: choice.text
        }
    }
}
