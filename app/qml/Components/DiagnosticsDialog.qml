// SPDX-License-Identifier: BSD-3-Clause
import QtQuick
import QtQuick.Controls

import EasyApplication.Gui.Style as EaStyle
import EasyApplication.Gui.Elements as EaElements

import edi.app

// Diagnostics (the owner, 2026-10-06; opened from Preferences › Develop): what this app runs on and with, one
// "name: value" line each — the platform and, on the web, the browser and why the start page chose its build — read
// when the dialog opens, selectable, and copied whole with Copy.
AppDialog {
    id: dialog

    property string text: ""

    objectName: "diagnostics"
    title: qsTr("Diagnostics")
    standardButtons: Dialog.Ok

    contentWidth: AppSizes.messagesDialogContentWidth
    contentHeight: column.implicitHeight

    onAboutToShow: dialog.text = ApplicationInfo.diagnostics()

    Column {
        id: column

        width: dialog.contentWidth
        spacing: EaStyle.Sizes.fontPixelSize

        ScrollView {
            width: parent.width
            height: Math.min(textArea.implicitHeight, EaStyle.Sizes.fontPixelSize * 24)
            clip: true

            EaElements.TextArea {
                id: textArea

                objectName: "diagnostics.text"
                readOnly: true
                selectByMouse: true
                wrapMode: TextEdit.Wrap
                font.family: EaStyle.Fonts.monoFontFamily
                text: dialog.text
            }
        }
        EaElements.SideBarButton {
            objectName: "diagnostics.copy"
            width: parent.width
            fontIcon: "copy"
            text: qsTr("Copy as text")
            onClicked: ApplicationInfo.copyText(dialog.text)
        }
    }
}
