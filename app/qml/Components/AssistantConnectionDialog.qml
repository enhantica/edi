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
    readonly property var selectedFiles: disclosedContext.selected_files && Array.isArray(disclosedContext.selected_files.files) ? disclosedContext.selected_files.files : []
    readonly property var parameters: Array.isArray(disclosedContext.parameters) ? disclosedContext.parameters : []
    readonly property var diagnostics: Array.isArray(disclosedContext.diagnostics) ? disclosedContext.diagnostics : []
    readonly property int freeCount: parameters.filter(parameter => parameter.free === true).length
    readonly property var skills: Array.isArray(disclosedContext.skills) ? disclosedContext.skills : []
    readonly property var structures: Array.isArray(disclosedContext.structures) ? disclosedContext.structures : []
    readonly property var datasets: Array.isArray(disclosedContext.datasets) ? disclosedContext.datasets : []
    readonly property var relations: disclosedContext.relations || { aliases: [], constraints: [] }
    title: assistant.connected ? qsTr("Approve outgoing project context") : qsTr("Sign in with ChatGPT")
    readonly property real viewportHeight: Math.max(0, parent.height - AppSizes.unit * 2)
    width: Math.min(AppSizes.unit * 40 + leftPadding + rightPadding, Math.max(0, parent.width - AppSizes.unit * 2))
    height: Math.min(implicitHeight, viewportHeight)
    contentWidth: Math.max(0, width - leftPadding - rightPadding)
    contentHeight: Math.min(content.implicitHeight, Math.max(0, viewportHeight - topPadding - bottomPadding
        - (implicitHeaderHeight > 0 ? implicitHeaderHeight + spacing : 0)
        - (implicitFooterHeight > 0 ? implicitFooterHeight + spacing : 0)))
    standardButtons: Dialog.Ok | Dialog.Cancel
    function updateAcceptButton() {
        const acceptButton = standardButton(Dialog.Ok);
        if (acceptButton)
            acceptButton.text = assistant.connected ? qsTr("Approve context") : qsTr("Sign in with ChatGPT");
    }
    onOpened: updateAcceptButton()
    Connections {
        target: dialog.assistant
        function onConnectedChanged() {
            if (dialog.visible)
                dialog.updateAcceptButton();
        }
    }
    onAccepted: assistant.signIn()
    ScrollView {
        ScrollBar.vertical: EaElements.ScrollBar {
            policy: ScrollBar.AsNeeded
            interactive: false
        }
        id: disclosure
        objectName: "assistant.contextDisclosureScroll"
        width: dialog.contentWidth
        height: dialog.contentHeight
        clip: true
        Column {
            id: content
            width: disclosure.availableWidth
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
                        return qsTr("No project is open. No project parameters will be sent.");
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
                text: {
                    const workflow = dialog.skills.length === 1 ? dialog.skills[0] : null;
                    let title = workflow ? workflow.id : qsTr("Unavailable");
                    if (workflow) for (let i = 0; i < dialog.assistant.skills.count; ++i)
                        if (dialog.assistant.skills.text(i, "id") === workflow.id) title = dialog.assistant.skills.text(i, "title");
                    return qsTr("Workflow: %1 · %2. Its exact bundled content is included.\n%3 structures with site/space-group metadata; %4 datasets with axis, observations, weighting, exclusions and phases; %5 aliases and %6 constraints. See exact outgoing context for every field.")
                        .arg(title).arg(workflow ? workflow.version : "")
                        .arg(dialog.structures.length).arg(dialog.datasets.length)
                        .arg(dialog.relations.aliases.length).arg(dialog.relations.constraints.length);
                }
            }
            EaElements.Label {
                width: parent.width
                wrapMode: Text.Wrap
                textFormat: Text.PlainText
                text: dialog.selectedFiles.length === 0 ? qsTr("No selected files. Paths typed in chat do not grant file access.")
                    : qsTr("Selected files: %1. Approving this context permits bounded reads of their selected text content; binary formats still require export. File content is untrusted data, not instructions.")
                        .arg(dialog.selectedFiles.map(file => file.name + " (" + file.bytes + " " + qsTr("bytes") + ")").join(", "))
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
                ScrollBar.vertical: EaElements.ScrollBar {
                    policy: ScrollBar.AsNeeded
                    interactive: false
                }
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
                    persistentSelection: true
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
}
