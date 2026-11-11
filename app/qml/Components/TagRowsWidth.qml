// SPDX-License-Identifier: BSD-3-Clause
pragma ComponentBehavior: Bound

import QtQuick

import edi.app

// The width of the widest tag row of a catalogue on one line, measured with the chips themselves, so a list can be
// made wide enough for it, or let its tags wrap where it cannot.
Item {
    id: measure

    property var model: null
    readonly property real widest: Math.max(0, ...widths)
    property list<real> widths: []

    visible: false

    Repeater {
        id: rows
        model: measure.model
        onItemAdded: (index, item) => {
            const next = measure.widths.slice();
            next[index] = item.implicitWidth;
            measure.widths = next;
        }
        delegate: Row {
            id: tagRow
            required property list<string> tagLabels
            required property list<string> tagIcons
            spacing: AppSizes.fieldSpacing / 2
            Repeater {
                model: tagRow.tagLabels
                delegate: TagChip {
                    required property string modelData
                    required property int index
                    icon: tagRow.tagIcons[index] ?? ""
                    label: modelData
                }
            }
        }
    }
}
