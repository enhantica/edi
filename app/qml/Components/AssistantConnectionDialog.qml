// SPDX-License-Identifier: BSD-3-Clause
pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Controls
import EasyApplication.Gui.Elements as EaElements
import edi.app

AppDialog {
    id: dialog
    required property AssistantViewModel assistant
    title: qsTr("Connect your ChatGPT subscription")
    contentWidth: AppSizes.unit * 32
    contentHeight: explanation.implicitHeight
    standardButtons: Dialog.Ok | Dialog.Cancel
    onAccepted: assistant.signIn()
    EaElements.Label {
        id: explanation
        width: dialog.contentWidth
        wrapMode: Text.Wrap
        text: qsTr("Continue in OpenAI’s sign-in page using your own ChatGPT account. Your messages and selected project metadata will be sent to OpenAI. Project changes still require an approved plan. Edi stores this connection privately on this computer; credentials do not travel with your project. Subscription availability and limits depend on your account.")
    }
}
