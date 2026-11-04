// SPDX-License-Identifier: BSD-3-Clause
import QtQuick

import EasyApplication.Gui.Style as EaStyle
import EasyApplication.Gui.Elements as EaElements

// A group title inside a Load menu: a plain line, never a choice, so it takes no hover, click or keyboard focus
// (the owner, 2026-11-04). Its text starts where the items' labels do.
Item {
    id: header

    property string text: ""

    width: parent ? parent.width : implicitWidth
    implicitWidth: label.implicitWidth + label.anchors.leftMargin + label.anchors.rightMargin
    implicitHeight: label.implicitHeight + EaStyle.Sizes.fontPixelSize

    EaElements.Label {
        id: label
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.verticalCenter: parent.verticalCenter
        // The items' padding (16, the base MenuItem's), their icon column and the gap after it.
        anchors.leftMargin: 16 + EaStyle.Sizes.fontPixelSize * 1.75
        anchors.rightMargin: EaStyle.Sizes.fontPixelSize
        font.bold: true
        textFormat: Text.PlainText
        elide: Text.ElideRight
        text: header.text
    }
}
