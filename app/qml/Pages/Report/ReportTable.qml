// SPDX-License-Identifier: BSD-3-Clause
pragma ComponentBehavior: Bound

import QtQuick

import EasyApplication.Gui.Style as EaStyle
import EasyApplication.Gui.Elements as EaElements

// A table of the report preview (a model's `columns` and `rows` of texts): a header line, then the rows on the
// tables' alternating background.
Column {
    id: table

    property var content: ({
            "columns": [],
            "rows": []
        })
    readonly property var columns: content && content.columns ? content.columns : []
    readonly property var rows: content && content.rows ? content.rows : []

    visible: columns.length > 0 && rows.length > 0

    Grid {
        id: grid

        columns: table.columns.length
        columnSpacing: EaStyle.Sizes.fontPixelSize * 1.5
        rowSpacing: 0

        Repeater {
            model: table.columns.length * (table.rows.length + 1)
            delegate: Rectangle {
                id: cell

                required property int index
                readonly property int line: Math.floor(index / table.columns.length)
                readonly property int column: index % table.columns.length

                width: label.implicitWidth
                height: EaStyle.Sizes.fontPixelSize * 1.9
                color: "transparent"

                EaElements.Label {
                    id: label
                    anchors.verticalCenter: parent.verticalCenter
                    color: cell.line === 0 ? EaStyle.Colors.themeForegroundMinor : EaStyle.Colors.themeForeground
                    text: cell.line === 0 ? table.columns[cell.column] : table.rows[cell.line - 1][cell.column] || " "
                }
            }
        }
    }
}
