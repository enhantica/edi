// SPDX-License-Identifier: BSD-3-Clause
pragma ComponentBehavior: Bound

import QtQuick

import EasyApplication.Gui.Style as EaStyle
import EasyApplication.Gui.Elements as EaElements

// Labelled values of the report preview (a model's rows): the label, then the value with its units.
Grid {
    id: grid

    property var entries: []

    columns: 2
    columnSpacing: EaStyle.Sizes.fontPixelSize * 1.5
    rowSpacing: EaStyle.Sizes.fontPixelSize * 0.4

    Repeater {
        model: grid.entries.length * 2
        delegate: EaElements.Label {
            required property int index
            readonly property var row: grid.entries[Math.floor(index / 2)]
            readonly property bool isLabel: index % 2 === 0
            color: isLabel ? EaStyle.Colors.themeForegroundMinor : EaStyle.Colors.themeForeground
            text: !row ? " " : isLabel ? row.label : row.units ? row.text + " " + row.units : row.text || " "
        }
    }
}
