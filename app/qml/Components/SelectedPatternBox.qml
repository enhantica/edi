// SPDX-License-Identifier: BSD-3-Clause
import QtQuick

// The shown dataset's mark on the Stacked and Map charts (the owner, 2026-10-22): an open rectangle whose border is the
// selected-pattern line's look at 1 px, black in the light theme and white in the dark, with a 1 px half-transparent
// line of the opposite colour just outside it and another just inside, so it shows on the background and on every
// colour of a map. The chart places and sizes it; the border is drawn inside its bounds.
Item {
    id: box

    property bool dark: false
    readonly property color core: dark ? "white" : "black"
    readonly property color edge: Qt.alpha(dark ? "black" : "white", 0.5)

    Rectangle {
        anchors.fill: parent
        color: "transparent"
        border.color: box.edge
        border.width: 1
    }
    Rectangle {
        anchors.fill: parent
        anchors.margins: 1
        color: "transparent"
        border.color: box.core
        border.width: 1
    }
    Rectangle {
        anchors.fill: parent
        anchors.margins: 2
        color: "transparent"
        border.color: box.edge
        border.width: 1
    }
}
