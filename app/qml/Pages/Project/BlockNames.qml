// SPDX-License-Identifier: BSD-3-Clause
pragma ComponentBehavior: Bound

import QtQuick

import EasyApplication.Gui.Style as EaStyle

import edi.app

// A block list in a Description row, one line per block (the owner, 2026-10-13): its icon in its colour, then the
// datablock name, " · " and its file, a structure's `.edi` file or an experiment's data file (a scan's listed file),
// on one centre line (IconLine; edi ADR-0017 §8–§10). More than 11 blocks (a scan's datasets) show the first 5, a "…"
// line and the last 5, so the row stays short and reads only those rows.
Column {
    id: names

    property var blocks: null
    property string blockKind: ""
    readonly property int count: blocks ? blocks.count : 0
    // Bumped by every change of the rows' values, so a renamed block reads again.
    property int revision: 0
    // The rows shown, -1 for the "…" between the two ends.
    readonly property var shown: ApplicationInfo.blockNamesShown()

    // A block's line: a structure's label is already "name · name.edi"; an experiment's data file is its `file`.
    function line(row: int): string { return ApplicationInfo.blockNamesLine(row); }

    spacing: EaStyle.Sizes.fontPixelSize * 0.25

    Connections {
        target: names.blocks
        function onDataChanged() { ApplicationInfo.blockNamesChanged(); }
    }

    Repeater {
        model: names.shown
        delegate: IconLine {
            id: entry

            required property int modelData

            segments: entry.modelData < 0 ? [
                {
                    "text": "…"
                }
            ] : [
                {
                    "icon": ParameterNames.blockIcon(names.blockKind),
                    "color": AppColors.block(names.blockKind, entry.modelData)
                },
                {
                    "text": names.line(entry.modelData)
                }
            ]
        }
    }
}
