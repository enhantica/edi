// SPDX-License-Identifier: BSD-3-Clause
import QtQuick
import QtQuick.Controls

import EasyApplication.Gui.Elements as EaElements
import edi.app

// The note a button opens when the part of the app it needs is missing: the AI assistant's (ADR-0071; on the web
// ADR-0023 §6) and the microphone's (ADR-0107 §8), one design. It says what is missing and, where Maintenance Tool
// can add it, leads to Updates in Preferences. Its parts are named "<objectName>.message" and "<objectName>.updates".
AppDialog {
    id: dialog

    property string message
    property string updatesText
    // Only an installation Maintenance Tool manages can add a component.
    property bool updatesShown: false
    // The web build's note leads to the desktop download page instead.
    property bool downloadShown: false

    parent: Overlay.overlay
    standardButtons: downloadShown ? Dialog.Close : Dialog.Ok
    enterAccepts: true
    contentWidth: AppSizes.messagesDialogContentWidth
    contentHeight: column.implicitHeight

    Column {
        id: column
        width: dialog.contentWidth
        spacing: AppSizes.unit
        EaElements.Label {
            objectName: dialog.objectName + ".message"
            width: parent.width
            wrapMode: Text.Wrap
            text: dialog.message
        }
        IconLink {
            objectName: dialog.objectName + ".updates"
            visible: dialog.updatesShown
            fontIcon: "cog"
            text: dialog.updatesText
            onClicked: {
                dialog.close();
                Preferences.dialogTab = "updates";
                Preferences.dialogShown = true;
            }
        }
        AssistantDownloadLink {
            visible: dialog.downloadShown
        }
    }
}
