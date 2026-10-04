// SPDX-License-Identifier: BSD-3-Clause
pragma ComponentBehavior: Bound

import QtQuick

import EasyApplication.Gui.Style as EaStyle

import edi.app

// A block list's names in a Description row, comma-separated, each after its icon in its colour on one centre
// line (IconLine; edi ADR-0017 §8–§10). Wraps when the names do not fit one line.
Flow {
    id: names

    property var blocks: null
    property string blockKind: ""

    spacing: EaStyle.Sizes.fontPixelSize * 0.5

    Repeater {
        model: names.blocks
        delegate: IconLine {
            id: entry

            required property int index
            required property string name

            segments: [
                {
                    "icon": ParameterNames.blockIcon(names.blockKind),
                    "color": AppColors.block(names.blockKind, entry.index)
                },
                {
                    // The list can go before its rows do (a reset closes the project): no comma then.
                    "text": names.blocks && entry.index < names.blocks.count - 1 ? `${entry.name},` : entry.name
                }
            ]
        }
    }
}
