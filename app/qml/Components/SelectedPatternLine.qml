// SPDX-License-Identifier: BSD-3-Clause
import QtQuick

// The shown dataset's line on the Evolution, Stacked and Map charts, one look on all three (the owner, 2026-10-22): a
// 2 px line with a 1 px half-transparent edge on each side, black edged in white in the light theme and white edged in
// black in the dark one, so it shows on the plot background and on every colour of a map. `position` is the line's
// centre in the parent's pixels; the line stays inside its parent, so a first or last dataset's line shows whole.
Item {
    id: line

    property bool vertical: false
    property bool dark: false
    property real position: NaN
    readonly property real thickness: 4
    readonly property color core: dark ? "white" : "black"
    readonly property color edge: Qt.alpha(dark ? "black" : "white", 0.5)
    readonly property real span: parent ? (vertical ? parent.width : parent.height) : 0
    readonly property real start: Math.max(0, Math.min(span - thickness, Math.round(position) - thickness / 2))

    visible: !isNaN(position)
    x: vertical ? start : 0
    y: vertical ? 0 : start
    width: vertical ? thickness : parent ? parent.width : 0
    height: vertical ? (parent ? parent.height : 0) : thickness

    Rectangle {
        width: line.vertical ? 1 : line.width
        height: line.vertical ? line.height : 1
        color: line.edge
    }
    Rectangle {
        x: line.vertical ? 1 : 0
        y: line.vertical ? 0 : 1
        width: line.vertical ? 2 : line.width
        height: line.vertical ? line.height : 2
        color: line.core
    }
    Rectangle {
        x: line.vertical ? 3 : 0
        y: line.vertical ? 0 : 3
        width: line.vertical ? 1 : line.width
        height: line.vertical ? line.height : 1
        color: line.edge
    }
}
