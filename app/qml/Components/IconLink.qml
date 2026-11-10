// SPDX-License-Identifier: BSD-3-Clause
import QtQuick

import EasyApplication.Gui.Style as EaStyle
import EasyApplication.Gui.Elements as EaElements

// A light link with an icon before its text, as the popup windows' buttons are: Home's links and About's feedback
// link, laid out from the left. Its click runs the app's own action; only an http(s) address goes to the system's
// browser.
EaElements.Button {
    id: link

    contentItem: Row {
        spacing: EaStyle.Sizes.fontPixelSize * 0.5

        EaElements.Label {
            anchors.verticalCenter: parent.verticalCenter
            font.family: EaStyle.Fonts.iconsFamily
            font.pixelSize: link.font.pixelSize
            color: link.foregroundColor()
            text: link.fontIcon
        }
        EaElements.Label {
            anchors.verticalCenter: parent.verticalCenter
            font: link.font
            color: link.foregroundColor()
            text: link.text
        }
    }
}
