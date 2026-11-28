// SPDX-License-Identifier: BSD-3-Clause
pragma ComponentBehavior: Bound

import QtQuick
import QtQuick.Controls

import EasyApplication.Gui.Style as EaStyle
import EasyApplication.Gui.Elements as EaElements

import edi.app

// After a magnetic Add from the pattern chart: each added structure with its name and BNS symbol (owner, 2026-11-28: no
// note). Nothing stays on the chart once it closes.
AppDialog {
    id: dialog
    objectName: "chart.findK.addedDialog"

    // One entry per added structure, in the order of its groups: {name, symbol}.
    property var entries: []
    signal openStructure

    // The width, padding and placement of the app's standard dialogs (Messages, the error dialog): AppDialog
    // centres it on whole pixels (owner: it was too narrow, its buttons clipped, and offset).
    title: qsTr("Magnetic structures added")
    contentWidth: AppSizes.messagesDialogContentWidth
    contentHeight: column.implicitHeight
    onClosed: destroy()

    Column {
        id: column
        width: dialog.contentWidth
        spacing: EaStyle.Sizes.fontPixelSize * 0.75
        Repeater {
            model: dialog.entries
            delegate: Column {
                id: entry
                required property var modelData
                required property int index
                spacing: EaStyle.Sizes.fontPixelSize * 0.25
                EaElements.Label {
                    width: column.width
                    elide: Text.ElideRight
                    objectName: `chart.findK.added.${entry.index}`
                    text: `${entry.modelData.name} · ${entry.modelData.symbol}`
                }
            }
        }
    }

    // Close and Open in Structure page in the standard button row at the right.
    footer: EaElements.DialogButtonBox {
        EaElements.Button {
            objectName: "chart.findK.addedDialog.close"
            fontIcon: "times"
            text: qsTr("Close")
            DialogButtonBox.buttonRole: DialogButtonBox.RejectRole
            onClicked: dialog.close()
        }
        EaElements.Button {
            objectName: "chart.findK.openStructure"
            fontIcon: "layer-group"
            text: qsTr("Open in Structure page")
            DialogButtonBox.buttonRole: DialogButtonBox.AcceptRole
            onClicked: {
                dialog.close();
                dialog.openStructure();
            }
        }
    }
}
