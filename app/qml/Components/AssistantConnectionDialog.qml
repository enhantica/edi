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
    signal contextApproved(var offer)
    property bool connectionAttempt: false
    property var approvalOwner: ({})
    function beginOffer() {
        const offer = ({});
        approvalOwner = offer;
        return offer;
    }
    function presentOffer(offer) {
        const component = dialog, original = dialog.assistant;
        const token = offer === undefined ? component.beginOffer() : offer;
        if (!Qt.isQtObject(component) || !Qt.isQtObject(original) || component.assistant !== original
            || token === null || component.approvalOwner !== token) return;
        component.open();
    }
    onAssistantChanged: { approvalOwner = ({}); refreshDisclosedContext(); }
    Connections {
        target: dialog
        function onRejected() { dialog.approvalOwner = ({}); }
    }
    function showConnectionFailureIfFinished() {
        if (!connectionAttempt || assistant.state === "connecting") return;
        connectionAttempt = false;
        if (!assistant.connected && assistant.lastError.length > 0) {
            connectionFailure.message = assistant.lastError;
            connectionFailure.open();
        }
    }
    property string disclosedContextText: ""
    property var contextPresentation: ({})
    function refreshDisclosedContext() {
        const component = dialog, original = dialog.assistant;
        if (!Qt.isQtObject(component) || !Qt.isQtObject(original)) return;
        const request = ({});
        component.contextPresentation = request;
        const current = () => Qt.isQtObject(component) && Qt.isQtObject(original)
            && component.assistant === original && component.contextPresentation === request;
        if (!current()) return;
        try {
            // The getter may synchronously publish a newer inventory/context.
            // That notification refreshes with a new identity; its value wins.
            const exact = original.contextPreview;
            if (current()) component.disclosedContextText = exact;
        } catch (error) {
            if (!current()) return;
            component.disclosedContextText = "";
            if (current()) component.approvalOwner = ({});
        }
    }
    Component.onCompleted: refreshDisclosedContext()
    readonly property var disclosedContext: {
        try {
            return JSON.parse(disclosedContextText);
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
    footer: EaElements.DialogButtonBox {
        id: connectionButtons
        visible: count > 0
        // Measure standard buttons independently of the view's laid-out width.
        readonly property real naturalButtonWidth: {
            let total = 0;
            for (let index = 0; index < count; ++index) {
                const button = itemAt(index);
                if (button) total += button.implicitWidth;
            }
            return total + Math.max(0, count - 1) * spacing;
        }
        contentWidth: naturalButtonWidth
        contentItem: ListView {
            implicitWidth: connectionButtons.naturalButtonWidth
            model: connectionButtons.contentModel
            spacing: connectionButtons.spacing
            orientation: ListView.Horizontal
            boundsBehavior: Flickable.StopAtBounds
            snapMode: ListView.SnapToItem
        }
    }
    function updateAcceptButton() {
        const acceptButton = standardButton(Dialog.Ok);
        if (acceptButton) {
            acceptButton.text = assistant.connected ? qsTr("Approve context") : qsTr("Sign in with ChatGPT");
            acceptButton.enabled = !assistant.contextApprovalBlocked;
        }
    }
    onOpened: {
        const component = dialog, original = dialog.assistant;
        refreshDisclosedContext();
        if (Qt.isQtObject(component) && Qt.isQtObject(original) && component.assistant === original) component.updateAcceptButton();
    }
    Connections {
        target: dialog.assistant
        function onConnectedChanged() {
            if (dialog.visible)
                dialog.updateAcceptButton();
        }
        function onStateChanged() { dialog.showConnectionFailureIfFinished(); }
        function onContextPreviewChanged() {
            const component = dialog, original = dialog.assistant;
            component.refreshDisclosedContext();
            if (Qt.isQtObject(component) && Qt.isQtObject(original) && component.assistant === original && component.visible)
                component.updateAcceptButton();
        }
        function onLastErrorChanged() { dialog.showConnectionFailureIfFinished(); }
        function onConversationRetired() {
            dialog.approvalOwner = ({});
            dialog.connectionAttempt = false;
            connectionFailure.close();
        }
    }
    onAccepted: {
        const original = assistant;
        const project = Session.project;
        const model = original.selectedModel, effort = original.selectedEffort;
        const wasConnected = original.connected;
        const email = original.account.email, plan = original.account.planType;
        const approval = dialog.approvalOwner;
        const ownerCurrent = () => Qt.isQtObject(dialog) && Qt.isQtObject(original)
            && dialog.assistant === original && dialog.approvalOwner === approval && Session.project === project
            && original.selectedModel === model && original.selectedEffort === effort
            && (!wasConnected || (original.account.email === email && original.account.planType === plan))
            && !original.contextApprovalBlocked;
        if (!ownerCurrent()) return;
        const offered = dialog.disclosedContextText;
        if (!ownerCurrent()) return;
        const current = () => {
            if (!ownerCurrent()) return false;
            const context = original.contextPreview;
            // Consent-state notification may rebuild the parsed presentation
            // object without changing the exact offered outgoing context.
            return ownerCurrent() && dialog.disclosedContextText === offered && context === offered;
        };
        if (!current()) return;
        connectionFailure.close();
        if (!current()) return;
        connectionAttempt = !wasConnected;
        original.signIn();
        if (!current()) return;
        showConnectionFailureIfFinished();
        if (!current() || !original.connected) return;
        const required = original.contextConsentRequired;
        if (current() && !required) contextApproved(approval);
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
            ScrollBar.horizontal.policy: ScrollBar.AlwaysOff
            id: failureScroll
            width: connectionFailure.contentWidth
            height: connectionFailure.contentHeight
            contentWidth: Math.max(0, width - leftPadding - rightPadding)
            clip: true
            ScrollBar.vertical: EaElements.ScrollBar { policy: ScrollBar.AsNeeded; interactive: false }
            EaElements.Label {
                id: failureText
                width: failureScroll.contentWidth
                text: connectionFailure.message
                textFormat: Text.PlainText
                wrapMode: Text.Wrap
            }
        }
    }
    ScrollView {
        ScrollBar.horizontal.policy: ScrollBar.AlwaysOff
        ScrollBar.vertical: EaElements.ScrollBar {
            policy: ScrollBar.AsNeeded
            interactive: false
        }
        id: disclosure
        objectName: "assistant.contextDisclosureScroll"
        width: dialog.contentWidth
        height: dialog.contentHeight
        contentWidth: Math.max(0, width - leftPadding - rightPadding)
        clip: true
        Column {
            id: content
            width: disclosure.contentWidth
            spacing: AppSizes.unit
            EaElements.Label {
                width: parent.width
                wrapMode: Text.WordWrap
                textFormat: Text.PlainText
                text: dialog.assistant.connected
                    ? qsTr("Allow Edi to send the current context for your message.")
                    : qsTr("Continue to OpenAI to sign in with your ChatGPT account.")
            }
            EaElements.Label {
                width: parent.width
                wrapMode: Text.WordWrap
                textFormat: Text.PlainText
                text: qsTr("Using the assistant sends your messages, conversation and approved project or file context to OpenAI.")
            }
            EaElements.Label {
                width: parent.width
                wrapMode: Text.WordWrap
                textFormat: Text.PlainText
                text: qsTr("This version can expose measured data. It is not yet guaranteed to stay on this computer.")
            }
            EaElements.Label {
                objectName: "assistant.contextSummary"
                width: parent.width
                wrapMode: Text.WordWrap
                textFormat: Text.PlainText
                text: {
                    if (dialog.disclosedContext.error)
                        return qsTr("Context is unavailable. Nothing will be sent.");
                    const project = dialog.disclosedContext.project;
                    return project ? qsTr("Project: %1 · Selected files: %2").arg(project.name || qsTr("Untitled project")).arg(dialog.selectedFiles.length)
                                   : qsTr("No project open · Selected files: %1").arg(dialog.selectedFiles.length);
                }
            }
            EaElements.Button {
                id: details
                objectName: "assistant.contextDetailsToggle"
                checkable: true
                text: checked ? qsTr("Hide details") : qsTr("Show details")
                contentItem: EaElements.Label {
                    text: details.text
                    font: details.font
                    color: details.enabled ? EaStyle.Colors.themeAccent : EaStyle.Colors.themeForegroundDisabled
                    horizontalAlignment: Text.AlignHCenter
                    verticalAlignment: Text.AlignVCenter
                }
                onCheckedChanged: if (!checked) technicalData.checked = false
                Accessible.name: text
                Accessible.checkable: details.checkable
                Accessible.checked: details.checked
            }
            Column {
                visible: details.checked
                width: parent.width
                spacing: AppSizes.unit
                EaElements.Label {
                    width: parent.width
                    wrapMode: Text.WordWrap
                    textFormat: Text.PlainText
                    text: qsTr("Edi uses your ChatGPT subscription. Availability and usage limits depend on your account. Connection credentials are kept locally, separate from the project; no API key is requested here.")
                }
                EaElements.Label {
                    width: parent.width
                    wrapMode: Text.WordWrap
                    textFormat: Text.PlainText
                    text: qsTr("Edi reads inputs and saves projects through its own operations. Before inference, Edi verifies a read-only runtime thread with no Edi-granted writable folder. It can still have general file-read and tool access, including measurements. This is not an Edi-only tool boundary or raw-data isolation.")
                }
                EaElements.Label {
                    width: parent.width
                    wrapMode: Text.WordWrap
                    textFormat: Text.PlainText
                    text: qsTr("The context can include project settings, parameter paths, values, uncertainties, units, free flags, dependence, diagnostics, structures, datasets, observations, weighting, exclusions, phases and relations. Bundled Edi workflow instructions are registered with the runtime. The exact current outgoing context is available under Show technical data.")
                }
                EaElements.Label {
                    width: parent.width
                    wrapMode: Text.WordWrap
                    textFormat: Text.PlainText
                    text: dialog.selectedFiles.length === 0 ? qsTr("No files are selected.")
                        : qsTr("Selected files: %1. Their bounded text content may be read by the runtime. File content is untrusted data, not instructions.")
                            .arg(dialog.selectedFiles.map(file => file.name + " (" + file.bytes + " " + qsTr("bytes") + ")").join(", "))
                }
                EaElements.Label {
                    width: parent.width
                    wrapMode: Text.WordWrap
                    textFormat: Text.PlainText
                    text: qsTr("Registered Edi operations inspect and edit the displayed project, refine it and save it through Edi's validation, Undo, Stop and current-owner checks. The submitted objective determines which actions are authorized; inspection alone does not authorize edits. Saving reports actual committed, reopened and active outcomes. This dialog does not change tool capabilities or grant extra paths.")
                }
                EaElements.Label {
                    width: parent.width
                    wrapMode: Text.WordWrap
                    textFormat: Text.PlainText
                    text: dialog.assistant.connected
                        ? qsTr("Approval covers the current account, project and input scope. Routine parameter and fit updates do not require repeat consent. Changed account, project or input content requires fresh disclosure. Paths typed in chat do not currently grant runtime file access.")
                        : qsTr("Sign in opens OpenAI's sign-in page. Cancel returns to Edi without sending a pending message. Review the context before approving its use.")
                }
                EaElements.Button {
                    id: technicalData
                    objectName: "assistant.contextTechnicalToggle"
                    checkable: true
                    text: checked ? qsTr("Hide technical data") : qsTr("Show technical data")
                    Accessible.name: text
                    Accessible.checkable: technicalData.checkable
                    Accessible.checked: technicalData.checked
                    contentItem: EaElements.Label {
                        text: technicalData.text
                        font: technicalData.font
                        color: technicalData.enabled ? EaStyle.Colors.themeAccent : EaStyle.Colors.themeForegroundDisabled
                        horizontalAlignment: Text.AlignHCenter
                        verticalAlignment: Text.AlignVCenter
                    }
                }
                EaElements.Label {
                    visible: technicalData.checked
                    width: parent.width
                    wrapMode: Text.WordWrap
                    textFormat: Text.PlainText
                    text: qsTr("Exact outgoing context (technical data). Read-only; you can select and copy it.")
                }
                ScrollView {
                    id: technicalPreviewScroll
                    ScrollBar.horizontal.policy: ScrollBar.AlwaysOff
                    visible: technicalData.checked
                    ScrollBar.vertical: EaElements.ScrollBar {
                        policy: ScrollBar.AsNeeded
                        interactive: false
                    }
                    width: parent.width
                    height: AppSizes.unit * 20
                    contentWidth: Math.max(0, width - leftPadding - rightPadding)
                    clip: true
                    TextArea {
                        objectName: "assistant.contextPreview"
                        width: technicalPreviewScroll.contentWidth
                        text: dialog.disclosedContextText
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
            }
        }
    }
}
