// SPDX-License-Identifier: BSD-3-Clause
pragma ComponentBehavior: Bound

import QtQuick
import QtQuick.Controls

import EasyApplication.Gui.Style as EaStyle
import EasyApplication.Gui.Elements as EaElements

import edi.app

// After a magnetic Add from the pattern chart (owner decision 2026-11-27, replacing the line above the chart): each
// added structure with its name and BNS symbol (owner, 2026-11-28: no note). Nothing stays on the chart once it closes.
AppDialog {
    id: dialog
    objectName: "chart.findK.addedDialog"

    // One entry per added structure, in the order of its groups: {name, symbol}.
    property var entries: []
    signal openStructure

    title: qsTr("Magnetic structures added")
    anchors.centerIn: parent
    onClosed: destroy()

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
