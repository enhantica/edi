// SPDX-License-Identifier: BSD-3-Clause
pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Controls
import EasyApplication.Gui.Elements as EaElements
import edi.app

AppDialog {
    id: dialog
    required property AssistantViewModel assistant
    title: assistant.connected ? qsTr("Approve outgoing project context") : qsTr("Connect your ChatGPT subscription")
    contentWidth: AppSizes.unit * 40
    contentHeight: content.implicitHeight
    standardButtons: Dialog.Ok | Dialog.Cancel
    onAccepted: assistant.signIn()
    Column {
        id: content
        width: dialog.contentWidth
        spacing: AppSizes.unit
        EaElements.Label {
            width: parent.width
            wrapMode: Text.Wrap
            textFormat: Text.PlainText
            text: qsTr("Your messages and the project context below will be sent to OpenAI. Inspect the actual parameter paths, values, units, free flags and diagnostics before continuing. Files and attachments are not sent in this slice. Project changes require your approved plan. Edi stores its connection privately on this computer; credentials do not travel with the project. Subscription availability and limits depend on your account.")
        }
        ScrollView {
            width: parent.width
            height: AppSizes.unit * 20
            clip: true
            TextArea {
                objectName: "assistant.contextPreview"
                text: dialog.assistant.contextPreview
                textFormat: TextEdit.PlainText
                readOnly: true
                selectByMouse: true
                wrapMode: TextEdit.WrapAnywhere
                Accessible.name: qsTr("Actual outgoing project context")
            }
        }
        EaElements.Label {
            width: parent.width
            wrapMode: Text.Wrap
            textFormat: Text.PlainText
            text: dialog.assistant.connected ? qsTr("Approve this scope to continue. A changed scope requires another inspection.") : qsTr("Continue in OpenAI’s own sign-in page using your ChatGPT account. No API key is requested.")
        }
    }
}
