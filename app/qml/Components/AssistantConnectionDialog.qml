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
    property var acceptedOffer: null
    function beginOffer() {
        const offer = ({});
        acceptedOffer = null;
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
    onAssistantChanged: { acceptedOffer = null; approvalOwner = ({}); refreshDisclosedContext(); }
    Connections {
        target: dialog
        function onRejected() { dialog.acceptedOffer = null; dialog.approvalOwner = ({}); }
    }
    function resumeAcceptedOffer() {
        const component=dialog, accepted=component.acceptedOffer;
        if(!accepted || accepted.submitting)return;
        const original=accepted.owner;
        if(!accepted.current() || !Qt.isQtObject(component) || !Qt.isQtObject(original)
            || component.acceptedOffer!==accepted || !original.connected) {
            if(Qt.isQtObject(component) && component.acceptedOffer===accepted)component.acceptedOffer=null;
            return;
        }
        const ready=original.draftAdmissionReady;
        if(!Qt.isQtObject(component) || !Qt.isQtObject(original) || component.acceptedOffer!==accepted || !accepted.current())return;
        if(!ready)return;
        accepted.submitting=true;
        const result=original.acceptConnectionOffer(accepted.context);
        if(!Qt.isQtObject(component) || !Qt.isQtObject(original) || component.acceptedOffer!==accepted)return;
        accepted.submitting=false;
        if(result==="waiting" && accepted.current())return;
        component.acceptedOffer=null;
        if(result==="approved" && accepted.current())component.contextApproved(accepted.approval);
    }
    function scheduleAcceptedOffer() { Qt.callLater(resumeAcceptedOffer); }
    function showConnectionFailureIfFinished() {
        if (!connectionAttempt || assistant.state === "connecting") return;
        connectionAttempt = false;
        if (!assistant.connected && assistant.lastError.length > 0) {
            connectionFailure.message = assistant.lastError;
            connectionFailure.open();
        }
    }
    property string disclosedContextText: ""
    property string disclosedContextIdentity: ""
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
            const identity = original.contextConsentIdentity;
            if (!current()) return;
            const exact = original.contextPreview;
            if (!current()) return;
            const actualIdentity = original.contextConsentIdentity;
            if (current() && identity.length && identity === actualIdentity) {
                component.disclosedContextText = exact;
                if (current()) component.disclosedContextIdentity = identity;
            }
        } catch (error) {
            if (!current()) return;
            component.disclosedContextText = "";
            if (current()) component.disclosedContextIdentity = "";
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
    title: assistant.connected ? qsTr("Approve project information") : qsTr("Connect ChatGPT")
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
        delegate: EaElements.Button {
            id: connectionChoice
            property string fontIcon: ""
            highlighted: true
            padding: EaStyle.Sizes.fontPixelSize * 0.5
            contentItem: Row {
                spacing: EaStyle.Sizes.fontPixelSize * 0.5
                EaElements.Label {
                    anchors.verticalCenter: parent.verticalCenter
                    text: connectionChoice.fontIcon
                    font.family: EaStyle.Fonts.iconsFamily
                    color: connectionChoice.foregroundColor()
                    Accessible.ignored: true
                }
                EaElements.Label {
                    anchors.verticalCenter: parent.verticalCenter
                    text: connectionChoice.text
                    font: connectionChoice.font
                    color: connectionChoice.foregroundColor()
                }
            }
        }
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
            acceptButton.text = assistant.connected ? qsTr("Share project information") : qsTr("Connect ChatGPT");
            acceptButton.fontIcon = assistant.connected ? "check" : "comment-dots";
            acceptButton.enabled = !assistant.contextApprovalBlocked;
        }
        const cancelButton = standardButton(Dialog.Cancel);
        if (cancelButton) cancelButton.fontIcon = "times";
    }
    onAboutToShow: updateAcceptButton()
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
        function onStateChanged() { dialog.showConnectionFailureIfFinished(); dialog.scheduleAcceptedOffer(); }
        function onDraftAdmissionReadyChanged() { dialog.scheduleAcceptedOffer(); }
        function onContextPreviewChanged() {
            const component = dialog, original = dialog.assistant;
            component.refreshDisclosedContext();
            if (Qt.isQtObject(component) && Qt.isQtObject(original) && component.assistant === original && component.visible)
                component.updateAcceptButton();
        }
        function onLastErrorChanged() { dialog.showConnectionFailureIfFinished(); }
        function onConversationRetired() {
            dialog.acceptedOffer = null;
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
            && !original.contextApprovalBlocked
            && (typeof approval.currentDraft !== "function" || approval.currentDraft());
        if (!ownerCurrent()) return;
        const offered = dialog.disclosedContextIdentity;
        if (!ownerCurrent()) return;
        const current = () => {
            if (!ownerCurrent()) return false;
            const context = original.contextConsentIdentity;
            // Approval/readiness may refresh presentation without replacing
            // the original backend disclosure authority.
            return ownerCurrent() && offered.length > 0 && dialog.disclosedContextIdentity === offered && context === offered;
        };
        if (!current()) return;
        connectionFailure.close();
        if (!current()) return;
        connectionAttempt = !wasConnected;
        const result=original.acceptConnectionOffer(offered);
        if (!current()) return;
        if(result==="waiting") {
            dialog.acceptedOffer={owner:original,approval:approval,context:offered,current:current,submitting:false};
            dialog.scheduleAcceptedOffer();return;
        }
        showConnectionFailureIfFinished();
        if(result==="approved" && current())contextApproved(approval);
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
        footer: EaElements.DialogButtonBox {
            visible: count > 0
            delegate: EaElements.Button {
                highlighted: true
                padding: EaStyle.Sizes.fontPixelSize * 0.5
            }
        }
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
                    ? qsTr("Allow the assistant to use current project information and attached files for your message.")
                    : qsTr("Sign in with your ChatGPT account. Your existing sign-in is reused when available; otherwise OpenAI opens to sign in.")
            }
            EaElements.Label {
                width: parent.width
                wrapMode: Text.WordWrap
                textFormat: Text.PlainText
                text: qsTr("Your messages, attachments and relevant project data, including measurements, are sent to OpenAI. Your account's availability and usage limits apply.")
            }
            EaElements.Label {
                width: parent.width
                wrapMode: Text.WordWrap
                textFormat: Text.PlainText
                visible: dialog.disclosedContext.error === true
                text: qsTr("Project information is unavailable. Nothing will be sent.")
            }
        }
    }
}
