// SPDX-License-Identifier: BSD-3-Clause
pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Controls
import EasyApplication.Gui.Style as EaStyle
import EasyApplication.Gui.Elements as EaElements
import edi.app

AppDialog {
    id: dialog
    required property AssistantViewModel assistant
    signal contextApproved()
    property bool connectionAttempt: false
    function showConnectionFailureIfFinished() {
        if (!connectionAttempt || assistant.state === "connecting") return;
        connectionAttempt = false;
        if (!assistant.connected && assistant.lastError.length > 0) {
            connectionFailure.message = assistant.lastError;
            connectionFailure.open();
        }
    }
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
        function onStateChanged() { dialog.showConnectionFailureIfFinished(); }
        function onLastErrorChanged() { dialog.showConnectionFailureIfFinished(); }
        function onConversationRetired() {
            dialog.connectionAttempt = false;
            connectionFailure.close();
        }
    }
    onAccepted: {
        connectionFailure.close();
        connectionAttempt = !assistant.connected;
        assistant.signIn();
        showConnectionFailureIfFinished();
        if (assistant.connected && !assistant.contextConsentRequired)
            contextApproved();
    }
    AppDialog {
        id: connectionFailure
        objectName: "assistant.connectionFailure"
        property string message: ""
        title: qsTr("ChatGPT connection was not completed")
        width: dialog.width
        height: Math.min(implicitHeight, dialog.viewportHeight)
        contentWidth: Math.max(0, width - leftPadding - rightPadding)
        contentHeight: Math.min(failureText.implicitHeight, Math.max(0, dialog.viewportHeight - topPadding - bottomPadding
            - (implicitHeaderHeight > 0 ? implicitHeaderHeight + spacing : 0)
            - (implicitFooterHeight > 0 ? implicitFooterHeight + spacing : 0)))
        standardButtons: Dialog.Ok
        ScrollView {
            id: failureScroll
            width: connectionFailure.contentWidth
            height: connectionFailure.contentHeight
            clip: true
            ScrollBar.vertical: EaElements.ScrollBar { policy: ScrollBar.AsNeeded; interactive: false }
            EaElements.Label {
                id: failureText
                width: failureScroll.availableWidth
                text: connectionFailure.message
                textFormat: Text.PlainText
                wrapMode: Text.Wrap
            }
        }
    }
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
                width: parent.width
                wrapMode: Text.Wrap
                textFormat: Text.PlainText
                text: dialog.assistant.workingFolder.length
                    ? qsTr("The native folder picker grants read/write scope to %1, alongside Edi's temporary staging workspace. Network remains disabled; broader authority is declined. Selecting the folder does not authorize overwriting an open or externally changed project.").arg(dialog.assistant.workingFolder)
                    : qsTr("Writes are limited to Edi's temporary staging workspace. Choose working folder in the assistant to grant a specific folder; chat paths alone do not grant access.")
            }
            EaElements.Label {
                objectName: "assistant.contextSummary"
                width: parent.width
                wrapMode: Text.Wrap
                textFormat: Text.PlainText
                text: {
                    if (dialog.disclosedContext.error) {
                        const code = dialog.disclosedContext.error.code;
                        if (code === "edi.assistant.resource_exhausted")
                            return qsTr("Project context exceeds its limit. Nothing will be sent.");
                        if (code === "edi.assistant.invalid_argument")
                            return qsTr("Project context contains invalid or unsupported metadata. Nothing will be sent.");
                        return qsTr("Project context is unavailable. Nothing will be sent.");
                    }
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
                    if (dialog.assistant.selectedSkill.length === 0)
                        return qsTr("The official agent uses a staged working copy of this project and the selected files. All bundled Edi skills are registered; relevant content is loaded on demand. Its ordinary shell/file tools may read files permitted by the runtime. Edi admits workspace writes with network disabled and declines broader authority requests; this is not a private read jail or a guarantee that inherited runtime extensions are confined. Native inspect_project/list_parameters/diagnostics read the displayed project. For the actual submitted objective, set_parameters/set_free may edit it and run_fit may run its real single/joint fit through normal Undo, Stop and physical/currentness validation. These tools cannot expand paths or capabilities. create_cwl_project may create a new displayed single-phase powder CW neutron project from the selected CIF/data IDs and an explicit recipe, only while this Session is empty. It cannot replace an open project. Native save/report and other conversions are not registered. Inspect the exact context below.");
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
                text: dialog.assistant.selectedSkill.length === 0 ? qsTr("Project context includes parameter paths, values, uncertainties, units, free flags, dependence and available diagnostics. The genuine submitted objective authorizes only the disclosed native actions within current project/revision bounds; mere inspection does not authorize mutation. No second scientific-plan approval is required for already delegated work. Paths typed into chat do not grant host file access.") : qsTr("Project context includes parameter paths, values, uncertainties, units, free flags and dependence, plus available diagnostics. Project changes require your approved plan. Files are not attached or read from paths typed into chat.")
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
                    selectionColor: EaStyle.Colors.themeAccent
                    selectedTextColor: EaStyle.Colors.themeBackground
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
