// SPDX-License-Identifier: BSD-3-Clause
import QtQuick
import QtQuick.Controls

import edi.app

// Diagnostics (the owner, 2026-10-06; opened from Preferences › Advanced), an information window (InfoDialog): what
// this app runs on and with, one "name: value" line each — the platform and, on the web, the browser and why the start
// page chose its build — read when the dialog opens, selectable, and copied whole with Copy as text, left of OK (the
// owner, 2026-11-10).
InfoDialog {
    id: dialog

    property string objectNamePrefix: "diagnostics"
    property var readText: () => ApplicationInfo.diagnostics()

    objectName: "diagnostics"
    title: qsTr("Diagnostics")
    standardButtons: Dialog.Ok
    monospace: true
    textObjectName: objectNamePrefix + ".text"

    onAboutToShow: dialog.text = dialog.readText()

    actions: [
        InfoDialog.InfoButton {
            objectName: dialog.objectNamePrefix + ".copy"
            fontIcon: "copy"
            text: qsTr("Copy as text")
            onClicked: ApplicationInfo.copyText(dialog.text)
        }
    ]
}
