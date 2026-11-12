// SPDX-License-Identifier: BSD-3-Clause
import QtQuick
import QtQuick.Controls
import EasyApplication.Gui.Style as EaStyle
import EasyApplication.Gui.Elements as EaElements
import edi.app

Popup {
    id: notice
    parent: Overlay.overlay
    modal: false
    closePolicy: Popup.NoAutoClose
    visible: NativeDialogs.busy || NativeDialogs.error !== ""
    width: Math.min(parent.width - EaStyle.Sizes.fontPixelSize * 2, EaStyle.Sizes.fontPixelSize * 36)
    x: (parent.width - width) / 2
    y: parent.height - height - EaStyle.Sizes.fontPixelSize * 4
    padding: EaStyle.Sizes.fontPixelSize
    contentItem: Column {
        spacing: EaStyle.Sizes.fontPixelSize * 0.5
        EaElements.Label {
            width: parent.width
            wrapMode: Text.Wrap
            text: NativeDialogs.error !== "" ? NativeDialogs.error : NativeDialogs.opening ? qsTr("Opening the system file chooser…") : qsTr("Choose a file or folder in the system file chooser.")
        }
        EaElements.Button {
            anchors.right: parent.right
            objectName: "nativeDialog.cancel"
            text: NativeDialogs.busy ? qsTr("Cancel") : qsTr("Dismiss")
            onClicked: NativeDialogs.busy ? NativeDialogs.cancel() : NativeDialogs.dismissError()
        }
    }
}
