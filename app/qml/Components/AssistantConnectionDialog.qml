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
    // Before signing in the user picks the provider and account here, so a user without the active one can still reach
    // the others (edi ADR-0108 §9). Each choice goes through the view model, which the texts below then follow.
    readonly property var installedProviders: assistant.providers.filter(entry => entry.installed)
    readonly property var providerAccounts: assistant.accounts.filter(entry => entry.provider === assistant.activeProvider.provider)
    // An added account is active but not recorded until its sign-in succeeds.
    readonly property bool addingAccount: !providerAccounts.some(entry => entry.active)
    readonly property bool choiceShown: !assistant.connected && (installedProviders.length > 1 || providerAccounts.length > 0)
    readonly property bool hostShown: !assistant.connected && assistant.activeProvider.provider === "copilot" && addingAccount
    // The host the added Copilot account was started with: empty for github.com, else <name>.ghe.com.
    property string appliedHost: ""
    readonly property var typedHost: copilotHost(hostField.text)
    readonly property bool hostBlocked: hostShown && typedHost !== appliedHost
    function copilotHost(text) {
        const host = text.trim().toLowerCase();
        if (host === "" || host === "github.com")
            return "";
        return /^[a-z0-9]([a-z0-9-]*[a-z0-9])?\.ghe\.com$/.test(host) ? host : null;
    }
    function chooseProvider(index) {
        const provider = installedProviders[index]?.provider;
        if (!provider || provider === assistant.activeProvider.provider)
            return;
        const saved = assistant.accounts.filter(entry => entry.provider === provider);
        if (saved.length > 0)
            assistant.switchAccount(provider, saved[0].id);
        else
            addAccount(provider);
        refreshOffer();
    }
    function chooseAccount(index) {
        if (index < providerAccounts.length)
            assistant.switchAccount(assistant.activeProvider.provider, providerAccounts[index].id);
        else if (!addingAccount)
            addAccount(assistant.activeProvider.provider);
        refreshOffer();
    }
    // The provider of the account last added here, so opening the dialog again does not add another one.
    property string addedProvider: ""
    function addAccount(provider) {
        const host = provider === "copilot" ? (typedHost ?? "") : "";
        appliedHost = host;
        addedProvider = provider;
        assistant.addAccount(provider, host);
    }
    // Opening the dialog makes the active provider one that is installed and has an account to sign in with: with a
    // single installed provider that is the one, and a provider other than ChatGPT gets its account added here.
    function prepareProvider() {
        if (assistant.connected || assistant.state === "connecting")
            return;
        if (installedProviders.length === 1 && assistant.activeProvider.provider !== installedProviders[0].provider)
            chooseProvider(0);
        else if (assistant.activeProvider.provider !== "chatgpt" && providerAccounts.length === 0 && addedProvider !== assistant.activeProvider.provider)
            addAccount(assistant.activeProvider.provider);
    }
    function applyHost() {
        if (!hostShown || typedHost === null || typedHost === appliedHost)
            return;
        addAccount("copilot");
        refreshOffer();
    }
    // A new account starts a new connection, so the offer shown must be made again.
    function refreshOffer() {
        refreshDisclosedContext();
        updateAcceptButton();
    }
    // A host typed for one added account must not carry over to the next one.
    onHostShownChanged: {
        if (!hostShown) {
            hostField.clear();
            appliedHost = "";
        }
    }
    onHostBlockedChanged: {
        if (visible)
            updateAcceptButton();
    }
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
    title: assistant.connected ? qsTr("Approve project information") : qsTr("Connect assistant")
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
            highlighted: true
            padding: EaStyle.Sizes.fontPixelSize * 0.5
            fontIcon: connectionButtons.roleIcon(DialogButtonBox.buttonRole)
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
        const accept = standardButton(Dialog.Ok);
        if (accept && hostBlocked)
            accept.enabled = false;
    }
    // The disclosure is refreshed before the dialog shows, not only once it has opened: an OK pressed while it
    // opens must approve what the project holds now, or it would be refused for a stale offer.
    onAboutToShow: {
        prepareProvider();
        refreshDisclosedContext();
        updateAcceptButton();
    }
    onOpened: ApplicationInfo.connectionPresentationChanged(0)
    // The disclosed context is made again only while the dialog is shown (opening it makes it afresh): a hidden dialog
    // does not listen, so a running fit's changes do not serialise the context.
    Connections {
        target: dialog.opened ? dialog.assistant : null
        function onContextPreviewChanged() {
            ApplicationInfo.connectionPresentationChanged(2);
        }
    }
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
        function onLastErrorChanged() {
            dialog.showConnectionFailureIfFinished();
        }
        function onConversationRetired() {
            ApplicationInfo.connectionResetOffer(false, true);
        }
    }
    // A failed connection shows only in the panel's notice, like every other assistant error.
    onAccepted: ApplicationInfo.connectionAccepted()
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
            // Each choice stands alone, full width, with no label of its own: the provider, then the account and, for
            // Copilot, the host. With one installed provider it still names it, disabled.
            EaElements.ComboBox {
                id: providerBox
                objectName: "assistant.connection.provider"
                width: parent.width
                visible: !dialog.assistant.connected && dialog.installedProviders.length > 0
                enabled: dialog.assistant.state !== "connecting" && dialog.installedProviders.length > 1
                model: dialog.installedProviders.map(entry => entry.name)
                currentIndex: dialog.installedProviders.findIndex(entry => entry.provider === dialog.assistant.activeProvider.provider)
                onActivated: index => dialog.chooseProvider(index)
                Accessible.name: qsTr("Provider")
            }
            EaElements.ComboBox {
                id: accountBox
                objectName: "assistant.connection.account"
                width: parent.width
                visible: (dialog.choiceShown || dialog.hostShown) && dialog.providerAccounts.length > 0
                enabled: dialog.assistant.state !== "connecting"
                model: dialog.providerAccounts.map(entry => entry.email || entry.host || qsTr("Account email unavailable")).concat([qsTr("New account")])
                currentIndex: dialog.addingAccount ? dialog.providerAccounts.length : dialog.providerAccounts.findIndex(entry => entry.active)
                onActivated: index => dialog.chooseAccount(index)
                Accessible.name: qsTr("Account")
            }
            EaElements.TextField {
                id: hostField
                objectName: "assistant.connection.host"
                width: parent.width
                visible: dialog.hostShown
                enabled: dialog.assistant.state !== "connecting"
                horizontalAlignment: TextInput.AlignLeft
                placeholderText: "github.com"
                onTextEdited: dialog.applyHost()
                Accessible.name: qsTr("Host")
            }
            EaElements.Label {
                objectName: "assistant.connection.hostMessage"
                width: parent.width
                wrapMode: Text.WordWrap
                textFormat: Text.PlainText
                visible: dialog.hostShown && dialog.typedHost === null
                color: EaStyle.Colors.themeForegroundMinor
                text: qsTr("Enter github.com or a GitHub Enterprise host such as name.ghe.com.")
            }
            EaElements.Label {
                width: parent.width
                wrapMode: Text.WordWrap
                textFormat: Text.PlainText
                // Before sign-in: how the chosen provider signs in, and where the data goes. Copilot
                // signs in with a one-time code on GitHub's page.
                text: dialog.assistant.connected ? qsTr("Allow the assistant to use current project information and attached files for your message.") : dialog.assistant.activeProvider.provider === "copilot" ? qsTr("Signs in with your GitHub account and a one-time code in the browser. Messages and project data go to %1.").arg(dialog.assistant.activeProvider.company) : qsTr("Signs in with your %1 account in the browser. Messages and project data go to %2.").arg(dialog.assistant.activeProvider.name).arg(dialog.assistant.activeProvider.company)
            }
            EaElements.Label {
                width: parent.width
                wrapMode: Text.WordWrap
                textFormat: Text.PlainText
                visible: dialog.assistant.connected
                text: qsTr("Your messages, attachments and relevant project data, including measurements, are sent to %1. Your account's availability and usage limits apply.").arg(dialog.assistant.activeProvider.company)
            }
            EaElements.Label {
                objectName: "assistant.managedClaudeNotice"
                width: parent.width
                wrapMode: Text.WordWrap
                textFormat: Text.PlainText
                // Only when managed Claude settings are actually found on this computer.
                visible: dialog.assistant.activeProvider.provider === "claude" && !dialog.assistant.connected && dialog.assistant.claudeManagedSettingsFound
                text: qsTr("Your organisation's Claude settings apply to this account.")
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
