// SPDX-License-Identifier: BSD-3-Clause
import QtQuick

import EasyApplication.Gui.Style as EaStyle
import EasyApplication.Gui.Elements as EaElements

// A group title inside a Load menu: a plain line, never a choice, so it takes no hover, click or keyboard focus
// (the owner, 2026-11-04). It starts at the items' icons; a section's first title sits close to the menu's top, a later
// one leaves a larger gap after the section above it, and its first item follows as closely as items follow each other.
Item {
    id: header

    property string text: ""
    // The menu's first title: no gap above it.
    property bool first: false
    property color color: EaStyle.Colors.themeForeground

    width: parent ? parent.width : implicitWidth
    implicitWidth: label.implicitWidth + label.anchors.leftMargin + label.anchors.rightMargin
    implicitHeight: label.implicitHeight + label.anchors.bottomMargin + (first ? EaStyle.Sizes.fontPixelSize * 0.25 : EaStyle.Sizes.fontPixelSize)

    EaElements.Label {
        id: label
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.bottom: parent.bottom
        // Where the items' icons start (the base MenuItem's 16 px padding), and the items' own top padding below
        // (LoadMenuItem), so the first item follows as closely as the next.
        anchors.leftMargin: 16
        anchors.rightMargin: EaStyle.Sizes.fontPixelSize
        anchors.bottomMargin: EaStyle.Sizes.fontPixelSize * 0.35
        font.bold: true
        color: header.color
        textFormat: Text.PlainText
        elide: Text.ElideRight
        text: header.text
    }
}
