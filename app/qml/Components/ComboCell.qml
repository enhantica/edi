// SPDX-License-Identifier: BSD-3-Clause
import QtQuick

// A table cell holding one combo box (edi ADR-0029). It takes the paddings and alignment the table gives a text cell,
// so the box's shown value starts where its header does; the box is as wide as its value and arrow, or the whole cell
// with `fills`.
Item {
    id: cell

    property int horizontalAlignment: Text.AlignLeft
    property real leftPadding: 0
    property real rightPadding: 0
    property bool fills: false
    readonly property real room: Math.max(0, width - leftPadding - rightPadding)

    height: parent ? parent.height : 0

    Component.onCompleted: {
        for (const box of children) {
            box.width = Qt.binding(() => cell.fills ? cell.room : Math.min(cell.room, box.fittedWidth));
            box.x = Qt.binding(() => cell.leftPadding + (cell.horizontalAlignment === Text.AlignRight ? cell.room - box.width : cell.horizontalAlignment === Text.AlignLeft ? 0 : (cell.room - box.width) / 2));
        }
    }
}
