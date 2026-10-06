// SPDX-License-Identifier: BSD-3-Clause
pragma ComponentBehavior: Bound

import QtQuick

import EasyApplication.Gui.Style as EaStyle

import edi.app

// A block list's names in a Description row, comma-separated, each after its icon in its colour on one centre
// line (IconLine; edi ADR-0017 §8–§10). Wraps when the names do not fit one line. A long list (a scan's datasets)
// shows its first and last few names with "…" between, so the row stays short and reads only those rows.
Flow {
    id: names

    property var blocks: null
    property string blockKind: ""
    // At most this many names; more show the first and last half of it.
    readonly property int limit: 14
    readonly property int count: blocks ? blocks.count : 0
    // Bumped by every change of the rows' values, so a renamed block reads again.
    property int revision: 0
    // The rows shown, -1 for the "…" between the two ends.
    readonly property var shown: {
        const rows = [];
        if (count <= limit + 1) {
            for (let row = 0; row < count; ++row)
                rows.push(row);
            return rows;
        }
        for (let row = 0; row < limit / 2; ++row)
            rows.push(row);
        rows.push(-1);
        for (let row = count - limit / 2; row < count; ++row)
            rows.push(row);
        return rows;
    }

    spacing: EaStyle.Sizes.fontPixelSize * 0.5

    Connections {
        target: names.blocks
        function onDataChanged() {
            ++names.revision;
        }
    }

    Repeater {
        model: names.shown
        delegate: IconLine {
            id: entry

            required property int modelData
            readonly property string name: names.revision >= 0 && names.blocks && modelData >= 0 ? names.blocks.text(modelData, "name") : ""

            segments: entry.modelData < 0 ? [
                {
                    "text": "…,"
                }
            ] : [
                {
                    "icon": ParameterNames.blockIcon(names.blockKind),
                    "color": AppColors.block(names.blockKind, entry.modelData)
                },
                {
                    // The list can go before its rows do (a reset closes the project): no comma then.
                    "text": entry.modelData < names.count - 1 ? `${entry.name},` : entry.name
                }
            ]
        }
    }
}
