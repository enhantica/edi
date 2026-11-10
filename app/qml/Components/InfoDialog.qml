// SPDX-License-Identifier: BSD-3-Clause
import QtQuick
import QtQuick.Controls

import EasyApplication.Gui.Style as EaStyle
import EasyApplication.Gui.Elements as EaElements

import edi.app

// An information window (the owner, 2026-11-10): its text in the app's white panel with a light border, selectable and
// scrolling when long, and one bottom row of background-less buttons, the caller's `actions` left of the standard
// button. How to cite, Diagnostics and About's licence texts share it.
AppDialog {
    id: dialog

    property string text: ""
    property string textObjectName: ""
    property bool monospace: false
    // Wrapped at the panel's width, or kept as written (a licence text).
    property bool wrapped: true
    // The panel's height: its text's, up to this.
    property real maximumTextHeight: EaStyle.Sizes.fontPixelSize * 24
    // The bottom row's buttons before the standard one, each an InfoButton.
    property alias actions: buttons.contentData

    // A bottom-row button: background-less, an icon before its text.
    component InfoButton: EaElements.Button {
        DialogButtonBox.buttonRole: DialogButtonBox.ActionRole
    }

    contentWidth: AppSizes.messagesDialogContentWidth
    contentHeight: panel.height

    footer: EaElements.DialogButtonBox {
        id: buttons
    }

    ScrollView {
        id: panel

        width: dialog.contentWidth
        height: Math.min(textArea.implicitHeight, dialog.maximumTextHeight)
        clip: true

        EaElements.TextArea {
            id: textArea

            objectName: dialog.textObjectName
            readOnly: true
            selectByMouse: true
            wrapMode: dialog.wrapped ? TextEdit.Wrap : TextEdit.NoWrap
            textFormat: TextEdit.PlainText
            font.family: dialog.monospace ? EaStyle.Fonts.monoFontFamily : EaStyle.Fonts.fontFamily
            text: dialog.text
        }
    }
}
