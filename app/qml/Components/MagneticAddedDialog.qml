// SPDX-License-Identifier: BSD-3-Clause
pragma ComponentBehavior: Bound

import QtQuick
import QtQuick.Controls

import EasyApplication.Gui.Style as EaStyle
import EasyApplication.Gui.Elements as EaElements

import edi.app

// After a magnetic Add from the pattern chart (owner decision 2026-11-27, replacing the line above the chart): each
// added structure with its BNS symbol, and under it, in the app's warning style, any marked peak or reflection where
// it gives no magnetic intensity. Nothing stays on the chart once it closes.
AppDialog {
    id: dialog
    objectName: "chart.findK.addedDialog"

    // One entry per added structure, in the order of its groups: {name, symbol, note}.
    property var entries: []
    signal openStructure

    title: qsTr("Magnetic structures added")
    anchors.centerIn: parent
    onClosed: destroy()

    // The intensity check of the first, enabled structure reports after the recalculation: its note joins that
    // structure's entry.
    function addNote(index, note) {
        if (index < 0 || index >= entries.length || note === "")
            return;
        const next = entries.slice();
        const entry = Object.assign({}, next[index]);
        entry.note = entry.note === "" || entry.note === undefined ? note : entry.note + " · " + note;
        next[index] = entry;
        entries = next;
    }

    Column {
        spacing: EaStyle.Sizes.fontPixelSize * 0.75
        Repeater {
            model: dialog.entries
            delegate: Column {
                id: entry
                required property var modelData
                required property int index
                spacing: EaStyle.Sizes.fontPixelSize * 0.25
                EaElements.Label {
                    objectName: `chart.findK.added.${entry.index}`
                    text: `${entry.modelData.name} · ${entry.modelData.symbol}`
                }
                Row {
                    visible: (entry.modelData.note ?? "") !== ""
                    spacing: EaStyle.Sizes.fontPixelSize * 0.4
                    EaElements.Label {
                        font.family: EaStyle.Fonts.iconsFamily
                        color: EaStyle.Colors.orange
                        text: "exclamation-triangle"
                    }
                    EaElements.Label {
                        objectName: `chart.findK.added.${entry.index}.note`
                        color: EaStyle.Colors.orange
                        text: entry.modelData.note ?? ""
                    }
                }
            }
        }
    }

    // Close and Open in Structure page at the right, as the app's other dialogs place their actions.
    footer: Item {
        implicitHeight: actions.implicitHeight + 2 * EaStyle.Sizes.fontPixelSize
        Row {
            id: actions
            anchors.right: parent.right
            anchors.rightMargin: dialog.rightPadding
            anchors.verticalCenter: parent.verticalCenter
            spacing: EaStyle.Sizes.fontPixelSize
            EaElements.Button {
                objectName: "chart.findK.addedDialog.close"
                fontIcon: "times"
                text: qsTr("Close")
                onClicked: dialog.close()
            }
            EaElements.Button {
                objectName: "chart.findK.openStructure"
                fontIcon: "layer-group"
                text: qsTr("Open in Structure page")
                onClicked: {
                    dialog.close();
                    dialog.openStructure();
                }
            }
        }
    }
}
