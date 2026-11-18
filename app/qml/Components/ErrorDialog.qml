// SPDX-License-Identifier: BSD-3-Clause
import QtQuick
import QtQuick.Controls

import EasyApplication.Gui.Style as EaStyle
import EasyApplication.Gui.Elements as EaElements

import edi.app

// An error, said in a popup with what went wrong, never a silent close (edi ADR-0062): Send to developers opens Help
// and feedback as a problem with the message, this run's log and, for a file edi could not read, the file attached;
// OK closes it.
AppDialog {
    id: dialog

    property string message: ""
    // The file a refused load was reading, attached when the user sends the problem; empty when there is none.
    property string file: ""

    // Shows `text` under `heading`; `path` is the unreadable file, or empty.
    function show(heading, text, path) {
        title = heading;
        message = text;
        file = path ?? "";
        open();
    }

    parent: Overlay.overlay
    title: qsTr("Something went wrong")
    contentWidth: AppSizes.messagesDialogContentWidth
    contentHeight: column.implicitHeight
    enterAccepts: true
    standardButtons: Dialog.Ok

    Column {
        id: column

        width: dialog.contentWidth
        spacing: EaStyle.Sizes.fontPixelSize

        EaElements.Label {
            objectName: dialog.objectName + ".message"
            width: parent.width
            wrapMode: Text.Wrap
            text: dialog.message
        }
        Row {
            spacing: EaStyle.Sizes.fontPixelSize

            EaElements.Button {
                objectName: dialog.objectName + ".send"
                fontIcon: "paper-plane"
                text: qsTr("Send to developers")
                onClicked: {
                    AppState.problemReported(dialog.message, dialog.file);
                    dialog.close();
                }
            }
        }
    }
}
