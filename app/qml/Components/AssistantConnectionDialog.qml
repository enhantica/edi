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
        return ApplicationInfo.connectionBeginOffer();
    }
    function presentOffer(offer) {
        ApplicationInfo.connectionPresentOffer(offer);
    }
    onAssistantChanged: ApplicationInfo.connectionResetOffer(true, false)
    Connections {
        target: dialog
        function onRejected() {
            ApplicationInfo.connectionResetOffer(false, false);
        }
    }
    function resumeAcceptedOffer() {
        ApplicationInfo.connectionResumeAcceptedOffer();
    }
    function scheduleAcceptedOffer() {
        ApplicationInfo.connectionScheduleAcceptedOffer();
    }
    function showConnectionFailureIfFinished() {
        ApplicationInfo.connectionShowFailure();
    }
    property string disclosedContextText: ""
    property string disclosedContextIdentity: ""
    property var contextPresentation: ({})
    function refreshDisclosedContext() {
        ApplicationInfo.connectionRefreshContext();
    }
    Component.onCompleted: refreshDisclosedContext()
    readonly property var disclosedContext: ApplicationInfo.connectionDisclosedContext()
    title: assistant.connected ? qsTr("Approve project information") : qsTr("Connect ChatGPT")
    readonly property real viewportHeight: Math.max(0, parent.height - AppSizes.unit * 2)
    width: Math.min(AppSizes.unit * 40 + leftPadding + rightPadding, Math.max(0, parent.width - AppSizes.unit * 2))
    height: Math.min(implicitHeight, viewportHeight)
    contentWidth: Math.max(0, width - leftPadding - rightPadding)
    contentHeight: Math.min(content.implicitHeight, Math.max(0, viewportHeight - topPadding - bottomPadding - (implicitHeaderHeight > 0 ? implicitHeaderHeight + spacing : 0) - (implicitFooterHeight > 0 ? implicitFooterHeight + spacing : 0)))
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
        readonly property real naturalButtonWidth: ApplicationInfo.connectionNaturalButtonsWidth()
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
        ApplicationInfo.connectionUpdateAcceptButton();
    }
    onAboutToShow: updateAcceptButton()
    onOpened: ApplicationInfo.connectionPresentationChanged(0)
    Connections {
        target: dialog.assistant
        function onConnectedChanged() {
            ApplicationInfo.connectionPresentationChanged(1);
        }
        function onStateChanged() {
            ApplicationInfo.connectionPresentationChanged(3);
        }
        function onDraftAdmissionReadyChanged() {
            dialog.scheduleAcceptedOffer();
        }
        function onContextPreviewChanged() {
            ApplicationInfo.connectionPresentationChanged(2);
        }
        function onLastErrorChanged() {
            dialog.showConnectionFailureIfFinished();
        }
        function onConversationRetired() {
            ApplicationInfo.connectionResetOffer(false, true);
        }
    }
    onAccepted: ApplicationInfo.connectionAccepted()
    AppDialog {
        id: connectionFailure
        objectName: "assistant.connectionFailure"
        property string message: ""
        title: qsTr("ChatGPT connection was not completed")
        width: dialog.width
        height: Math.min(implicitHeight, dialog.viewportHeight)
        contentWidth: Math.max(0, width - leftPadding - rightPadding)
        contentHeight: Math.min(failureText.implicitHeight, Math.max(0, dialog.viewportHeight - topPadding - bottomPadding - (implicitHeaderHeight > 0 ? implicitHeaderHeight + spacing : 0) - (implicitFooterHeight > 0 ? implicitFooterHeight + spacing : 0)))
        standardButtons: Dialog.Ok
        footer: EaElements.DialogButtonBox {
            visible: count > 0
            delegate: EaElements.Button {
                highlighted: true
                padding: EaStyle.Sizes.fontPixelSize * 0.5
            }
        }
        ScrollView {
            id: failureScroll
            ScrollBar.horizontal.policy: ScrollBar.AlwaysOff
            width: connectionFailure.contentWidth
            height: connectionFailure.contentHeight
            contentWidth: Math.max(0, width - leftPadding - rightPadding)
            clip: true
            ScrollBar.vertical: EaElements.ScrollBar {
                policy: ScrollBar.AsNeeded
                interactive: false
            }
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
        id: disclosure
        ScrollBar.horizontal.policy: ScrollBar.AlwaysOff
        ScrollBar.vertical: EaElements.ScrollBar {
            policy: ScrollBar.AsNeeded
            interactive: false
        }
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
                text: dialog.assistant.connected ? qsTr("Allow the assistant to use current project information and attached files for your message.") : qsTr("Sign in with your ChatGPT account. Your existing sign-in is reused when available; otherwise OpenAI opens to sign in.")
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
