// SPDX-License-Identifier: BSD-3-Clause
import QtQuick

import EasyApplication.Gui.Style as EaStyle
import EasyApplication.Gui.Elements as EaElements

import edi.app

// One tag as the Examples and Tutorials lists draw it: its icon, if any, and its label in the tag's colour on a light
// tint of it, slightly rounded. The online sources' kinds use it too.
Rectangle {
    id: chip

    property string label: ""
    property string icon: ""
    property color ink: EaStyle.Colors.themeForeground

    radius: 3
    color: Qt.rgba(ink.r, ink.g, ink.b, 0.13)
    width: content.implicitWidth + 2 * AppSizes.fieldSpacing
    height: EaStyle.Sizes.fontPixelSize * 1.65

    Row {
        id: content

        anchors.centerIn: parent
        spacing: AppSizes.fieldSpacing / 2

        EaElements.Label {
            visible: text !== ""
            anchors.verticalCenter: parent.verticalCenter
            font.family: EaStyle.Fonts.iconsFamily
            font.pixelSize: EaStyle.Sizes.fontPixelSize * 0.8
            color: chip.ink
            text: chip.icon
        }
        EaElements.Label {
            anchors.verticalCenter: parent.verticalCenter
            horizontalAlignment: Text.AlignHCenter
            font.pixelSize: EaStyle.Sizes.fontPixelSize * 0.9
            color: chip.ink
            text: chip.label
        }
    }
}
