// SPDX-License-Identifier: BSD-3-Clause
pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Controls
import EasyApplication.Gui.Elements as EaElements
import edi.app

AppDialog {
    id: dialog
    required property AssistantViewModel assistant
    readonly property var disclosedContext: {
        try {
            return JSON.parse(assistant.contextPreview);
        } catch (error) {
            return { error: true };
        }
    }
    readonly property var parameters: Array.isArray(disclosedContext.parameters) ? disclosedContext.parameters : []
    readonly property var diagnostics: Array.isArray(disclosedContext.diagnostics) ? disclosedContext.diagnostics : []
    readonly property int freeCount: parameters.filter(parameter => parameter.free === true).length
    title: assistant.connected ? qsTr("Approve outgoing project context") : qsTr("Sign in with ChatGPT")
    contentWidth: AppSizes.unit * 40
    contentHeight: content.implicitHeight
    standardButtons: Dialog.Ok | Dialog.Cancel
    onOpened: {
        const acceptButton = standardButton(Dialog.Ok);
        if (acceptButton)
            acceptButton.text = assistant.connected ? qsTr("Approve context") : qsTr("Sign in with ChatGPT");
    }
    onAccepted: assistant.signIn()
    Column {
        id: content
        width: dialog.contentWidth
        spacing: AppSizes.unit
        EaElements.Label {
            width: parent.width
            wrapMode: Text.Wrap
            textFormat: Text.PlainText
            text: qsTr("OpenAI will receive your message, conversation context and the project information described below. Edi uses your ChatGPT subscription; availability and usage limits depend on your account.")
        }
        EaElements.Label {
            objectName: "assistant.contextSummary"
            width: parent.width
            wrapMode: Text.Wrap
            textFormat: Text.PlainText
            text: {
                if (dialog.disclosedContext.error)
                    return qsTr("Project context is unavailable or exceeds its limit. Nothing will be sent.");
                const project = dialog.disclosedContext.project;
                if (!project)
                    return qsTr("No project is open. No project parameters or files will be sent.");
                return qsTr("Project: %1\nFitting mode: %2\n%3 parameter values, including %4 marked free; %5 diagnostic entries.")
                    .arg(project.name || qsTr("Untitled project"))
                    .arg(project.fitting_mode || qsTr("Unspecified"))
                    .arg(dialog.parameters.length).arg(dialog.freeCount).arg(dialog.diagnostics.length);
            }
        }
        EaElements.Label {
            width: parent.width
            wrapMode: Text.Wrap
            textFormat: Text.PlainText
            text: qsTr("Project context includes parameter paths, values, uncertainties, units, free flags and dependence, plus available diagnostics. Project changes require your approved plan. Files are not attached or read from paths typed into chat.")
        }
        EaElements.Button {
            id: details
            objectName: "assistant.contextDetailsToggle"
            checkable: true
            text: checked ? qsTr("Hide technical details") : qsTr("Show exact outgoing context")
            Accessible.name: text
        }
        ScrollView {
            visible: details.checked
            width: parent.width
            height: visible ? AppSizes.unit * 20 : 0
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
            text: dialog.assistant.connected
                ? qsTr("Approve this scope to continue. Changed project information requires your consent again.")
                : qsTr("Continue on OpenAI’s sign-in page. Edi keeps the connection credentials privately on this computer, separate from your project. No API key is requested.")
        }
    }
}
